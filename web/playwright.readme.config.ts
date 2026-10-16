import { defineConfig, devices } from "@playwright/test";

/** `make readme-media`: the README's pictures, taken from the live site at twice the pixels, so
 * they stay sharp at GitHub's width on any screen. e2e/readme-media.sh puts them together. */
const phone = {
  ...devices["Desktop Chrome"],
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  deviceScaleFactor: 2,
};
const desktop = { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 };

export default defineConfig({
  testDir: "e2e",
  testMatch: "readme.media.ts",
  outputDir: "test-results",
  fullyParallel: true,
  reporter: "list",
  use: { baseURL: "https://dailyainotes.com" },
  projects: [
    { name: "phone-light", use: { ...phone, colorScheme: "light" } },
    { name: "phone-dark", use: { ...phone, colorScheme: "dark" } },
    { name: "desktop-light", use: { ...desktop, colorScheme: "light" } },
    { name: "desktop-dark", use: { ...desktop, colorScheme: "dark" } },
  ],
});
