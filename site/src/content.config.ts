// Loads enrich/<namespace>/<name>/{readme,changelog}.md from the repo-root
// enrich/ tree (populated by a separate pipeline; may be absent entirely —
// glob() degrades to an empty collection when its base dir doesn't exist).
import { pathToFileURL } from "node:url";
import path from "node:path";
import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { repoRoot } from "./lib/catalog";

const enrichDir = pathToFileURL(path.join(repoRoot(), "enrich") + path.sep);

// id = "<namespace>/<name>", matching the page slug, by stripping the
// trailing "/<file>.md" off the glob-relative entry path.
function idFromFile(file: string) {
  const re = new RegExp(`/${file}\\.md$`);
  return ({ entry }: { entry: string }) => entry.replace(re, "");
}

const readmes = defineCollection({
  loader: glob({ pattern: "**/readme.md", base: enrichDir, generateId: idFromFile("readme") }),
});

const changelogs = defineCollection({
  loader: glob({ pattern: "**/changelog.md", base: enrichDir, generateId: idFromFile("changelog") }),
});

export const collections = { readmes, changelogs };
