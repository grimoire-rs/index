// node --test site/src/lib/  (Node's built-in runner + type stripping)
import assert from "node:assert/strict";
import { test } from "node:test";
import { versionCascade } from "./catalog.ts";

const real = ["latest", "0.10.0", "0.10", "0.9.1", "0.9.0", "0.9", "0.8.4", "0.8", "0"];

test("versionCascade", () => {
  assert.deepEqual(versionCascade("0.10.0", real), ["latest", "0", "0.10", "0.10.0"]);
  // A "v" prefix must ride along into the rolling tags, not be stripped off.
  assert.deepEqual(versionCascade("v1.2.3", ["latest", "v1.2.3", "v1.2", "v1"]), [
    "latest",
    "v1",
    "v1.2",
    "v1.2.3",
  ]);
  // Rolling tags that were never published are skipped, not invented.
  assert.deepEqual(versionCascade("1.2.3", ["1.2.3", "1"]), ["1", "1.2.3"]);
  // No version field: derive from the newest numeric-looking tag.
  assert.deepEqual(versionCascade(undefined, real), ["latest", "0", "0.10", "0.10.0"]);
  // Nothing parses as a version — must not return an empty (empty = bare
  // bordered strip with no segments on the page).
  assert.deepEqual(versionCascade(undefined, ["stable", "beta"]), ["stable", "beta"]);
  assert.deepEqual(versionCascade(undefined, []), []);
});
