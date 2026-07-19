#!/usr/bin/env python3
"""Refresh enrich/<namespace>/<name>/ sidecars from the live registry.

For each index/**/metadata.json package:
  * `grim describe <ref>` -> refresh data.json metadata every run (cheap, no
    content download).
  * If the package has a description companion, probe its digest
    (`grim fetch --description --digest-only`); only on first-seen/change do a
    full `grim fetch --description` to write readme.md / changelog.md / logo.

Committed to git; a scheduled workflow reruns it. Per-package failures keep the
existing (stale) sidecar; the process only fails on a majority outage.

Optional args filter packages by ref substring; `--selftest` runs pure checks.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index"
ENRICH = ROOT / "enrich"

TIMEOUT = 60  # per grim call, seconds


def grim_json(*args: str) -> dict:
    r = subprocess.run(
        ["grim", *args, "--format", "json"],
        capture_output=True, text=True, timeout=TIMEOUT, check=True,
    )
    return json.loads(r.stdout)


def _map_meta(desc: dict) -> dict:
    """grim's snake_case describe payload -> camelCase Package fields."""
    data = {}
    for k in ("title", "summary", "version", "license", "created"):
        if desc.get(k) is not None:
            data[k] = desc[k]
    data["keywords"] = desc.get("keywords") or []
    data["tags"] = desc.get("tags") or []
    data["deprecated"] = desc.get("deprecated")  # string | null, always present
    if desc.get("replaced_by"):
        data["replacedBy"] = desc["replaced_by"]
    return data


def _decode(member: dict) -> bytes:
    c = member["content"]
    return base64.b64decode(c) if member.get("encoding") == "base64" else c.encode()


def _clean_companions(out: Path) -> None:
    """Drop stale companion files; the caller rewrites whatever still exists
    upstream. Without this, content removed from the registry would keep
    rendering forever (the detail page globs files, not data.json flags)."""
    for old in (*out.glob("logo.*"), out / "readme.md", out / "changelog.md"):
        old.unlink(missing_ok=True)


def enrich(ref: str, namespace: str, name: str) -> None:
    out = ENRICH / namespace / name
    existing = {}
    if (out / "data.json").exists():
        existing = json.loads((out / "data.json").read_text())

    desc = grim_json("describe", ref)
    data = _map_meta(desc)

    if desc.get("has_description"):
        digest = grim_json("fetch", ref, "--description", "--digest-only")["digest"]
        if digest != existing.get("descDigest"):  # first-seen or changed
            out.mkdir(parents=True, exist_ok=True)
            files = grim_json("fetch", ref, "--description")["files"]
            _clean_companions(out)
            has_readme = has_changelog = False
            logo = None
            for m in files:
                low = m["path"].lower()
                if low == "readme.md":
                    (out / "readme.md").write_bytes(_decode(m))
                    has_readme = True
                elif low == "changelog.md":
                    (out / "changelog.md").write_bytes(_decode(m))
                    has_changelog = True
                elif low.startswith("logo."):
                    ext = m["path"].rsplit(".", 1)[-1]
                    (out / f"logo.{ext}").write_bytes(_decode(m))
                    logo = f"/logos/{namespace}/{name}.{ext}"
            data["descDigest"] = digest
            data["hasReadme"] = has_readme
            data["hasChangelog"] = has_changelog
            if logo:  # keep key order identical to the cached branch below
                data["logo"] = logo
        else:  # unchanged -> carry the cached companion state forward
            data["descDigest"] = digest
            data["hasReadme"] = existing.get("hasReadme", False)
            data["hasChangelog"] = existing.get("hasChangelog", False)
            if existing.get("logo"):
                data["logo"] = existing["logo"]
    else:  # description companion gone entirely: clear its leftovers too
        if out.exists():
            _clean_companions(out)
        data["hasReadme"] = False
        data["hasChangelog"] = False

    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(data, indent=1) + "\n")


def main() -> None:
    filters = [a for a in sys.argv[1:] if a != "--selftest"]
    packages = []
    for path in sorted(INDEX.rglob("metadata.json")):
        meta = json.loads(path.read_text())
        ref = meta["ref"]
        if filters and not any(f in ref for f in filters):
            continue
        namespace = str(path.parent.parent.relative_to(INDEX))
        packages.append((ref, namespace, meta["name"]))

    # ponytail: sequential is fine at N~5; parallelize with a ThreadPoolExecutor
    # (grim calls are I/O-bound) if the index grows into the hundreds.
    failures = 0
    for ref, namespace, name in packages:
        try:
            enrich(ref, namespace, name)
        except Exception as exc:  # keep the stale sidecar; stale beats empty
            failures += 1
            print(f"warn: {ref}: {exc}", file=sys.stderr)

    print(f"enriched {len(packages) - failures}/{len(packages)} packages")
    if failures * 2 > len(packages):  # >50% failed: treat as an outage
        sys.exit(f"error: {failures}/{len(packages)} packages failed")


def _selftest() -> None:
    assert _decode({"content": "hi"}) == b"hi"
    png = base64.b64encode(b"\x89PNG").decode()
    assert _decode({"content": png, "encoding": "base64"}) == b"\x89PNG"
    m = _map_meta({"title": "t", "replaced_by": "x", "deprecated": None,
                   "keywords": ["a"], "tags": ["1"], "license": None})
    assert m == {"title": "t", "keywords": ["a"], "tags": ["1"],
                 "deprecated": None, "replacedBy": "x"}, m
    print("selftest ok")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
