#!/usr/bin/env python3
"""Validate an index PR for auto-merge.

Runs from the TRUSTED base checkout (pull_request_target). PR content is
consumed as data only — never executed.

Env inputs:
  PR_AUTHOR       PR author login
  PR_AUTHOR_ID    PR author numeric account id
  CHANGED_FILES   newline-separated changed paths (from the GitHub API)
  PR_TREE         directory holding the PR head's files (data checkout)
  GH_TOKEN        token for GitHub API lookups

Exit 0 = eligible for auto-merge. Non-zero = manual review required.
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
from build import KINDS, validate  # noqa: E402  (trusted, same checkout)

PATH_RE = re.compile(r"^index/github\.com/([^/]+)/([^/]+)/metadata\.json$")
API = "https://api.github.com"

# App bots trusted to announce for a namespace (first-party publish CI).
# Keyed by bot login, value = (numeric account id, allowed namespaces).
# "[bot]" logins are app-reserved (humans cannot register brackets) and
# app slugs are globally unique; the id is pinned anyway as belt-and-braces.
TRUSTED_BOTS: dict[str, tuple[int, frozenset[str]]] = {
    "grimoire-index-announce[bot]": (298988186, frozenset({"grimoire-rs"})),
}


def fail(msg: str) -> None:
    sys.exit(f"::error::{msg}")


def gh_api(path: str) -> tuple[int, dict | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "grimoire-index-bot",
    }
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, None


def namespace_allowed(ns: str, author: str, author_id: str) -> bool:
    """ns == author, an org the author publicly belongs to, or a trusted bot."""
    bot = TRUSTED_BOTS.get(author)
    if bot is not None:
        bot_id, namespaces = bot
        return str(bot_id) == author_id and ns.lower() in namespaces
    if ns.lower() == author.lower():
        status, data = gh_api(f"/users/{urllib.parse.quote(ns)}")
        return status == 200 and str(data["id"]) == author_id
    status, data = gh_api(f"/users/{urllib.parse.quote(ns)}")
    if status != 200 or data.get("type") != "Organization":
        return False
    status, _ = gh_api(
        f"/orgs/{urllib.parse.quote(ns)}/public_members/{urllib.parse.quote(author)}"
    )
    return status == 204


def namespace_id(ns: str) -> int | None:
    status, data = gh_api(f"/users/{urllib.parse.quote(ns)}")
    return data["id"] if status == 200 else None


def registry_token(host: str, repo: str, challenge: str) -> str | None:
    """Anonymous bearer-token dance for registries that 401 with a realm."""
    m = re.search(r'realm="([^"]+)"', challenge)
    if not m:
        return None
    params = {"scope": f"repository:{repo}:pull"}
    svc = re.search(r'service="([^"]+)"', challenge)
    if svc:
        params["service"] = svc.group(1)
    url = f"{m.group(1)}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "grimoire-index-bot"})
        ) as resp:
            return json.loads(resp.read()).get("token")
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def ref_reachable(ref: str) -> bool:
    """True when <host>/v2/<repo>/tags/list lists at least one tag."""
    host, _, repo = ref.partition("/")
    if not repo:
        return False
    url = f"https://{host}/v2/{repo}/tags/list"

    def fetch(token: str | None) -> tuple[int, bytes, str]:
        headers = {"User-Agent": "grimoire-index-bot"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30
            ) as resp:
                return resp.status, resp.read(), ""
        except urllib.error.HTTPError as e:
            return e.code, b"", e.headers.get("WWW-Authenticate", "")
        except urllib.error.URLError:
            return 0, b"", ""

    status, body, challenge = fetch(None)
    if status == 401 and challenge:
        token = registry_token(host, repo, challenge)
        if token:
            status, body, _ = fetch(token)
    if status != 200:
        return False
    try:
        return bool(json.loads(body).get("tags"))
    except json.JSONDecodeError:
        return False


def main() -> None:
    author = os.environ["PR_AUTHOR"]
    author_id = os.environ["PR_AUTHOR_ID"]
    pr_tree = Path(os.environ["PR_TREE"])
    changed = [f for f in os.environ["CHANGED_FILES"].splitlines() if f]

    if not changed:
        fail("empty change set")

    namespaces: set[str] = set()
    for f in changed:
        m = PATH_RE.match(f)
        if not m:
            fail(f"{f}: outside index/github.com/<ns>/<pkg>/metadata.json — manual review")
        namespaces.add(m.group(1))

    for ns in sorted(namespaces):
        if not namespace_allowed(ns, author, author_id):
            fail(
                f"namespace {ns!r} not owned by PR author {author!r} "
                "(must match login or be an org with public membership)"
            )

    for f in changed:
        path = pr_tree / f
        if not path.exists():
            print(f"{f}: deleted by owner — ok")
            continue
        ns = PATH_RE.match(f).group(1)
        try:
            meta = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            fail(f"{f}: invalid JSON: {e}")
        validate(path, meta)  # schema/kind/name checks from build.py
        owner = meta["owner"]
        if owner["github"].lower() != ns.lower():
            fail(f"{f}: owner.github {owner['github']!r} != namespace {ns!r}")
        expected = namespace_id(ns)
        if expected is None or owner["id"] != expected:
            fail(f"{f}: owner.id {owner['id']!r} != GitHub account id {expected!r}")
        if "grim.ocx.sh" in meta["ref"]:
            fail(f"{f}: grim.ocx.sh refs are not accepted")
        if not ref_reachable(meta["ref"]):
            fail(f"{f}: ref {meta['ref']!r} has no reachable tags — publish first")
        print(f"{f}: ok ({meta['kind']} {meta['name']} -> {meta['ref']})")

    print(f"validated {len(changed)} file(s) across namespaces: {sorted(namespaces)}")


if __name__ == "__main__":
    main()
