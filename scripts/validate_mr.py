#!/usr/bin/env python3
"""Validate an index MR for auto-merge (GitLab flavor of validate_pr.py).

Runs with scripts/ re-checked-out from the trusted target branch (see
.gitlab-ci.yml). MR content is consumed as data only — never executed.

Env inputs (predefined by GitLab CI unless noted):
  CI_API_V4_URL                 API base, e.g. https://gitlab.example.com/api/v4
  CI_SERVER_HOST                instance host — pins the index/<host>/ segment
  CI_MERGE_REQUEST_PROJECT_ID   target project id
  CI_MERGE_REQUEST_IID          MR iid
  CHANGED_FILES                 newline-separated changed paths (from git diff)
  GRIM_INDEX_BOT_TOKEN          access token (`api` scope) for lookups + merge
  GRIM_INDEX_MIN_ACCESS_LEVEL   membership threshold (default 30 = Developer)

Gate (all must hold, any failure -> non-zero exit -> manual review):
  1. every changed path is index/<host>/<namespace>/<pkg>/metadata.json
     (nested group namespaces allowed)
  2. the MR author owns each namespace: username == user namespace, or
     member of the group (inherited membership counts) with sufficient
     access level, or a trusted bot
  3. every file passes the schema checks, owner.login matches the
     namespace, owner.id matches the GitLab namespace id
  4. every ref lists at least one tag on its registry
On success the MR is merged via merge_when_pipeline_succeeds (a direct
merge from inside the still-running pipeline would be rejected when
"pipelines must succeed" is enabled).

Exit 0 = merge requested. Non-zero = manual review required.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import validate  # noqa: E402  (trusted, same checkout)
from validate_pr import ref_reachable  # noqa: E402  (registry checks, portable)

# Bots trusted to announce for namespaces (e.g. a central publish bot).
# Keyed by bot username, value = (numeric user id, allowed namespaces).
# "*" allows every namespace. Forks edit this in-source.
TRUSTED_BOTS: dict[str, tuple[int, frozenset[str]]] = {}


def fail(msg: str) -> None:
    sys.exit(f"error: {msg}")


def api_request(
    method: str, path: str, body: dict | None = None
) -> tuple[int, dict | list | None]:
    """One GitLab API call. Module-level so tests can monkeypatch."""
    url = f"{os.environ['CI_API_V4_URL']}{path}"
    headers = {
        "User-Agent": "grimoire-index-bot",
        "PRIVATE-TOKEN": os.environ.get("GRIM_INDEX_BOT_TOKEN", ""),
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read()
            return resp.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        return e.code, None
    except urllib.error.URLError:
        return 0, None


def api_get(path: str) -> tuple[int, dict | list | None]:
    return api_request("GET", path)


def api_put(path: str, body: dict) -> tuple[int, dict | list | None]:
    return api_request("PUT", path, body)


def path_rule(host: str) -> re.Pattern:
    """Changed-path gate. Greedy first group = namespace (nested groups)."""
    return re.compile(rf"^index/{re.escape(host)}/(.+)/([^/]+)/metadata\.json$")


def namespace_info(ns: str) -> dict | None:
    """The GitLab namespace object (kind, id, full_path) or None."""
    status, data = api_get(f"/namespaces/{urllib.parse.quote(ns, safe='')}")
    return data if status == 200 and isinstance(data, dict) else None


def namespace_allowed(
    ns: str, ns_info: dict, author: str, author_id: int, min_access: int
) -> bool:
    """Author owns ns: trusted bot, own user namespace, or group member."""
    bot = TRUSTED_BOTS.get(author)
    if bot is not None:
        bot_id, namespaces = bot
        return bot_id == author_id and ("*" in namespaces or ns.lower() in namespaces)
    if ns_info.get("kind") == "user":
        return author.lower() == ns_info.get("full_path", "").lower()
    # Group namespace: /members/all/ includes inherited membership, so a
    # parent-group member owns subgroup namespaces too.
    status, member = api_get(
        f"/groups/{urllib.parse.quote(ns, safe='')}/members/all/{author_id}"
    )
    return (
        status == 200
        and isinstance(member, dict)
        and member.get("access_level", 0) >= min_access
    )


def request_merge(project_id: str, mr_iid: str) -> None:
    status, _ = api_put(
        f"/projects/{project_id}/merge_requests/{mr_iid}/merge",
        {
            "merge_when_pipeline_succeeds": True,
            "squash": True,
            "should_remove_source_branch": True,
        },
    )
    if status not in (200, 202):
        fail(f"merge request API returned {status} — merge manually")


def main() -> None:
    host = os.environ["CI_SERVER_HOST"]
    project_id = os.environ["CI_MERGE_REQUEST_PROJECT_ID"]
    mr_iid = os.environ["CI_MERGE_REQUEST_IID"]
    min_access = int(os.environ.get("GRIM_INDEX_MIN_ACCESS_LEVEL", "30"))
    changed = [f for f in os.environ["CHANGED_FILES"].splitlines() if f]

    if not changed:
        fail("empty change set")

    rule = path_rule(host)
    namespaces: set[str] = set()
    for f in changed:
        m = rule.match(f)
        if not m:
            fail(f"{f}: outside index/{host}/<ns>/<pkg>/metadata.json — manual review")
        namespaces.add(m.group(1))

    status, mr = api_get(f"/projects/{project_id}/merge_requests/{mr_iid}")
    if status != 200 or not isinstance(mr, dict):
        fail(f"cannot read MR {mr_iid} (API status {status})")
    author = mr["author"]["username"]
    author_id = mr["author"]["id"]

    ns_ids: dict[str, int] = {}
    for ns in sorted(namespaces):
        info = namespace_info(ns)
        if info is None:
            fail(f"namespace {ns!r} does not exist on {host}")
        if not namespace_allowed(ns, info, author, author_id, min_access):
            fail(
                f"namespace {ns!r} not owned by MR author {author!r} "
                "(must match username or group membership with access level "
                f">= {min_access})"
            )
        ns_ids[ns] = info["id"]

    for f in changed:
        path = Path(f)
        if not path.exists():
            print(f"{f}: deleted by owner — ok")
            continue
        ns = rule.match(f).group(1)
        try:
            meta = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            fail(f"{f}: invalid JSON: {e}")
        validate(path, meta)  # schema/kind/name checks from build.py
        owner = meta["owner"]
        if owner.get("login", "").lower() != ns.lower():
            fail(f"{f}: owner.login {owner.get('login')!r} != namespace {ns!r}")
        if owner["id"] != ns_ids[ns]:
            fail(f"{f}: owner.id {owner['id']!r} != namespace id {ns_ids[ns]!r}")
        if not ref_reachable(meta["ref"]):
            fail(f"{f}: ref {meta['ref']!r} has no reachable tags — publish first")
        print(f"{f}: ok ({meta['kind']} {meta['name']} -> {meta['ref']})")

    request_merge(project_id, mr_iid)
    print(
        f"validated {len(changed)} file(s) across namespaces {sorted(namespaces)} "
        "— merge requested (when pipeline succeeds)"
    )


if __name__ == "__main__":
    main()
