// @ts-check
import { defineConfig } from "astro/config";
import preact from "@astrojs/preact";

export default defineConfig({
  site: "https://index.grimoire.rs",
  integrations: [preact()],
});
