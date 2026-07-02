#!/usr/bin/env python3
"""Compile index/**/metadata.json into dist/ for static serving.

dist/ layout:
  all.json                                   -- every package, one array
  index/<namespace...>/<pkg>/metadata.json   -- path-addressable copies
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index"
DIST = ROOT / "dist"

REQUIRED = {"schema", "name", "kind", "ref", "description", "owner"}
KINDS = {"skill", "rule", "agent", "bundle"}


def fail(path: Path, msg: str) -> None:
    try:
        shown = path.relative_to(ROOT)
    except ValueError:  # path from a PR data checkout, not this tree
        shown = path
    sys.exit(f"error: {shown}: {msg}")


def validate(path: Path, meta: dict) -> None:
    missing = REQUIRED - meta.keys()
    if missing:
        fail(path, f"missing keys: {sorted(missing)}")
    if meta["schema"] != 1:
        fail(path, f"unsupported schema version {meta['schema']!r}")
    if meta["kind"] not in KINDS:
        fail(path, f"kind must be one of {sorted(KINDS)}")
    if meta["name"] != path.parent.name:
        fail(path, f"name {meta['name']!r} != directory {path.parent.name!r}")
    owner = meta["owner"]
    if not isinstance(owner, dict) or {"github", "id"} - owner.keys():
        fail(path, "owner must be an object with 'github' and 'id'")


def main() -> None:
    packages = []
    for path in sorted(INDEX.rglob("metadata.json")):
        meta = json.loads(path.read_text())
        validate(path, meta)
        meta["namespace"] = str(path.parent.parent.relative_to(INDEX))
        packages.append(meta)

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(INDEX, DIST / "index")
    (DIST / "all.json").write_text(json.dumps(packages, indent=1) + "\n")
    (DIST / "index.html").write_text(
        "<meta http-equiv=refresh content='0;url=https://grimoire.rs'>\n"
    )
    print(f"built {len(packages)} packages -> dist/")


if __name__ == "__main__":
    main()
