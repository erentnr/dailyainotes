import { defineConfig, devices } from "@playwright/test";

/** `pnpm screenshots`: every page at phone and desktop sizes in both themes, saved to
 * ./screenshots/ for a person to look at. It runs against a site that is already up (`pnpm dev`
 * with `make api`), so it is not part of `make check`. */
const phone = { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true };
const desktop = { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } };

export default defineConfig({
  testDir: "e2e",
  testMatch: "*.pw.ts",
  outputDir: "test-results",
  fullyParallel: true,
  reporter: "list",
  use: { baseURL: "http://localhost:4321" },
  projects: [
    { name: "phone-light", use: { ...phone, colorScheme: "light" } },
    { name: "phone-dark", use: { ...phone, colorScheme: "dark" } },
    { name: "desktop-light", use: { ...desktop, colorScheme: "light" } },
    { name: "desktop-dark", use: { ...desktop, colorScheme: "dark" } },
    // The narrowest phone we support: checked for sideways scrolling, no screenshots kept.
    {
      name: "narrow",
      use: { ...phone, viewport: { width: 360, height: 740 }, colorScheme: "light" },
    },
  ],
});
