// @ts-check
import node from "@astrojs/node";
import react from "@astrojs/react";
import { defineConfig, envField, fontProviders } from "astro/config";

// The fonts DESIGN.md names, downloaded from Google Fonts at build time and served from our
// own origin, so a visit sends nothing to Google.
const google = fontProviders.google();

export default defineConfig({
  output: "server",
  adapter: node({ mode: "standalone" }),
  integrations: [react()],
  // Nothing uses sessions; without this the Node adapter stores them on the filesystem.
  session: false,
  env: {
    schema: {
      // The API for pages rendered on the server, read at run time; browsers call /api.
      API_URL: envField.string({
        context: "server",
        access: "secret",
        default: "http://localhost:8000",
      }),
    },
  },
  fonts: [
    {
      provider: google,
      name: "Newsreader",
      cssVariable: "--font-serif",
      weights: [400, 500, 600],
      styles: ["normal", "italic"],
      subsets: ["latin"],
      fallbacks: ["Georgia", "serif"],
    },
    {
      provider: google,
      name: "Hanken Grotesk",
      cssVariable: "--font-sans",
      weights: [400, 500, 600],
      subsets: ["latin"],
      fallbacks: ["system-ui", "sans-serif"],
    },
    {
      provider: google,
      name: "IBM Plex Mono",
      cssVariable: "--font-mono",
      weights: [400, 500],
      subsets: ["latin"],
      fallbacks: ["ui-monospace", "monospace"],
    },
  ],
  // `pnpm dev` sends the browser's /api calls to `make api`.
  vite: { server: { proxy: { "/api": "http://localhost:8000" } } },
});
