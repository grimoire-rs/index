#!/usr/bin/env python3
"""Offline self-checks for validate_mr.py (and the shared build.validate).

Run: python3 scripts/test_validate_mr.py — stdlib only, no network: every
API call is monkeypatched.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import validate_mr  # noqa: E402


def expect_exit(fn, *args, **kwargs) -> str:
    try:
        fn(*args, **kwargs)
    except SystemExit as e:
        return str(e.code)
    raise AssertionError(f"{fn.__name__} did not exit")


def test_path_rule() -> None:
    rule = validate_mr.path_rule("gitlab.example.com")
    m = rule.match("index/gitlab.example.com/acme/tool/metadata.json")
    assert m and m.group(1) == "acme" and m.group(2) == "tool"
    # Nested groups: greedy namespace, package dir is always the last segment.
    m = rule.match("index/gitlab.example.com/platform/ai/tool/metadata.json")
    assert m and m.group(1) == "platform/ai" and m.group(2) == "tool"
    assert not rule.match("scripts/validate_mr.py")
    assert not rule.match("index/github.com/acme/tool/metadata.json")
    assert not rule.match("index/gitlab.example.com/tool/metadata.json")
    assert not rule.match("index/gitlab.example.co/acme/tool/metadata.json")


def test_build_validate_owner_keys() -> None:
    def meta(owner: dict) -> dict:
        return {
            "schema": 1,
            "name": "tool",
            "kind": "skill",
            "ref": "reg.example.com/acme/tool",
            "description": "d",
            "owner": owner,
        }

    path = Path("index/gitlab.example.com/acme/tool/metadata.json")
    build.validate(path, meta({"login": "acme", "id": 7}))
    build.validate(path, meta({"github": "acme", "id": 7}))
    assert "owner" in expect_exit(build.validate, path, meta({"id": 7}))
    assert "owner" in expect_exit(build.validate, path, meta({"login": "acme"}))


def test_build_validate_kinds() -> None:
    def meta(kind: str) -> dict:
        return {
            "schema": 1,
            "name": "tool",
            "kind": kind,
            "ref": "reg.example.com/acme/tool",
            "description": "d",
            "owner": {"github": "acme", "id": 7},
        }

    path = Path("index/github.com/acme/tool/metadata.json")
    for kind in ("skill", "rule", "agent", "mcp", "bundle"):
        build.validate(path, meta(kind))
    assert "kind" in expect_exit(build.validate, path, meta("plugin"))


def test_namespace_info_user_fallback(monkey) -> None:
    # /namespaces is membership-scoped: a project access token's bot user
    # cannot see foreign namespaces, so user namespaces 404 — fall back to
    # the public /users lookup and carry the USER id (owner.id contract).
    def get(path):
        if path.startswith("/namespaces/"):
            return 404, None
        if path.startswith("/users?username="):
            return 200, [{"id": 5, "username": "Acme"}]
        raise AssertionError(f"unexpected GET {path}")

    monkey["get"] = get
    assert validate_mr.namespace_info("acme") == {
        "kind": "user",
        "id": 5,
        "full_path": "Acme",
    }

    # A visible user namespace still resolves to the user id, never the
    # namespace id — grim stamps the user id into owner.id.
    def get_visible(path):
        if path.startswith("/namespaces/"):
            return 200, {"kind": "user", "id": 999, "full_path": "acme"}
        if path.startswith("/users?username="):
            return 200, [{"id": 5, "username": "acme"}]
        raise AssertionError(f"unexpected GET {path}")

    monkey["get"] = get_visible
    assert validate_mr.namespace_info("acme")["id"] == 5

    # Unknown everywhere -> None (manual review).
    def get_missing(path):
        if path.startswith("/namespaces/"):
            return 404, None
        if path.startswith("/users?username="):
            return 200, []
        raise AssertionError(f"unexpected GET {path}")

    monkey["get"] = get_missing
    assert validate_mr.namespace_info("acme") is None

    # Only an exact (case-insensitive) username hit counts.
    def get_substring(path):
        if path.startswith("/namespaces/"):
            return 404, None
        if path.startswith("/users?username="):
            return 200, [{"id": 6, "username": "acme2"}]
        raise AssertionError(f"unexpected GET {path}")

    monkey["get"] = get_substring
    assert validate_mr.namespace_info("acme") is None

    # Groups pass through unchanged (group id == namespace id).
    monkey["get"] = lambda path: (200, {"kind": "group", "id": 44, "full_path": "platform/ai"})
    assert validate_mr.namespace_info("platform/ai")["id"] == 44


def test_namespace_allowed(monkey) -> None:
    user_ns = {"kind": "user", "id": 9, "full_path": "Acme"}
    assert validate_mr.namespace_allowed("acme", user_ns, "ACME", 9, 30)
    # Username match alone is not enough — the author id must match too.
    assert not validate_mr.namespace_allowed("acme", user_ns, "ACME", 1, 30)
    assert not validate_mr.namespace_allowed("acme", user_ns, "mallory", 2, 30)

    group_ns = {"kind": "group", "id": 44, "full_path": "platform/ai"}
    monkey["get"] = lambda path: (200, {"access_level": 30})
    assert validate_mr.namespace_allowed("platform/ai", group_ns, "dev", 5, 30)
    monkey["get"] = lambda path: (200, {"access_level": 20})
    assert not validate_mr.namespace_allowed("platform/ai", group_ns, "dev", 5, 30)
    monkey["get"] = lambda path: (404, None)
    assert not validate_mr.namespace_allowed("platform/ai", group_ns, "dev", 5, 30)

    validate_mr.TRUSTED_BOTS["announce-bot"] = (77, frozenset({"*"}))
    try:
        assert validate_mr.namespace_allowed("anything", group_ns, "announce-bot", 77, 30)
        assert not validate_mr.namespace_allowed("anything", group_ns, "announce-bot", 78, 30)
        validate_mr.TRUSTED_BOTS["scoped-bot"] = (88, frozenset({"platform/ai"}))
        assert validate_mr.namespace_allowed("platform/ai", group_ns, "scoped-bot", 88, 30)
        assert not validate_mr.namespace_allowed("other", group_ns, "scoped-bot", 88, 30)
    finally:
        validate_mr.TRUSTED_BOTS.clear()


def test_request_merge(monkey) -> None:
    calls = []

    def put(path, body):
        calls.append((path, body))
        return 200, {}

    monkey["put"] = put
    validate_mr.request_merge("123", "7")
    assert calls[0][0] == "/projects/123/merge_requests/7/merge"
    assert calls[0][1]["merge_when_pipeline_succeeds"] is True

    monkey["put"] = lambda path, body: (405, None)
    assert "405" in expect_exit(validate_mr.request_merge, "123", "7")


def test_main_happy_path(monkey, tmp: Path) -> None:
    ns = "platform/ai"
    pkg = tmp / "index/gitlab.example.com/platform/ai/tool"
    pkg.mkdir(parents=True)
    (pkg / "metadata.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "name": "tool",
                "kind": "skill",
                "ref": "reg.example.com/platform/ai/tool",
                "description": "d",
                "owner": {"login": ns, "id": 44},
            }
        )
    )

    def get(path):
        if path.endswith("/merge_requests/7"):
            return 200, {"author": {"username": "dev", "id": 5}}
        if path.startswith("/namespaces/"):
            return 200, {"kind": "group", "id": 44, "full_path": ns}
        if "/members/all/" in path:
            return 200, {"access_level": 40}
        raise AssertionError(f"unexpected GET {path}")

    merged = []
    monkey["get"] = get
    monkey["put"] = lambda path, body: merged.append(path) or (200, {})
    validate_mr.ref_reachable = lambda ref: True

    os.environ.update(
        CI_SERVER_HOST="gitlab.example.com",
        CI_MERGE_REQUEST_PROJECT_ID="123",
        CI_MERGE_REQUEST_IID="7",
        CHANGED_FILES="index/gitlab.example.com/platform/ai/tool/metadata.json",
    )
    cwd = os.getcwd()
    os.chdir(tmp)
    try:
        validate_mr.main()
    finally:
        os.chdir(cwd)
    assert merged == ["/projects/123/merge_requests/7/merge"]


def main() -> None:
    # Route the module's API calls through a mutable dispatch table.
    monkey: dict = {}
    validate_mr.api_get = lambda path: monkey["get"](path)
    validate_mr.api_put = lambda path, body: monkey["put"](path, body)

    test_path_rule()
    test_build_validate_owner_keys()
    test_build_validate_kinds()
    test_namespace_info_user_fallback(monkey)
    test_namespace_allowed(monkey)
    test_request_merge(monkey)
    with tempfile.TemporaryDirectory() as tmp:
        test_main_happy_path(monkey, Path(tmp))
    print("all validate_mr self-checks passed")


if __name__ == "__main__":
    main()
