import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";

// Site vitrine statique (SSG) — SEO natif, build ultra-léger.
export default defineConfig({
  site: "https://myhanout.ai",
  integrations: [tailwind()],
});
