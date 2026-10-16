import { type Page, test } from "@playwright/test";

import type { Topic } from "../src/lib/api/client";
import { addTopic, homeSlot, type Picked } from "../src/lib/topics";

/** The README's pictures (`make readme-media`, playwright.readme.config.ts): the daily page as a
 * visitor who follows every active topic sees it, and one loop of How it works' "One story's
 * night" as frames named by the millisecond they were taken at, which readme-media.sh turns
 * into a GIF. */

const OUT = "screenshots/readme";
// nightAt's loop (src/lib/night.ts).
const NIGHT_MS = 16_000;

/** Follows every active topic, in the slots the topic picker would give them. */
async function followAll(page: Page) {
  const topics = (await (await page.request.get("/api/v1/topics")).json()) as Topic[];
  const picked = topics.reduce<Picked[]>((all, t) => addTopic(all, t.slug, homeSlot(t.category)), []);
  await page.addInitScript((value) => localStorage.setItem("dan.topics", value), JSON.stringify(picked));
}

async function ready(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => !document.querySelector("astro-island[ssr]"));
  await page.evaluate(() => document.fonts.ready);
}

test("daily page", async ({ page }, info) => {
  await followAll(page);
  await page.goto("/");
  await ready(page);
  await page.screenshot({ path: `${OUT}/daily-${info.project.name}.png` });
});

test("one story's night", async ({ page }, info) => {
  test.skip(!info.project.name.startsWith("desktop"), "The GIF is taken at desktop width.");
  test.setTimeout(90_000);
  await page.goto("/how-it-works");
  await ready(page);
  // Pause means nothing in a picture.
  await page.addStyleTag({ content: ".night-head button { visibility: hidden; }" });
  // Start where a loop starts: after the last step, the first again.
  await page.locator('.night-stage[data-step="6"]').waitFor({ timeout: NIGHT_MS + 2_000 });
  await page.locator('.night-stage[data-step="0"]').waitFor({ timeout: NIGHT_MS });
  const stage = page.locator(".night-stage");
  const theme = info.project.name.replace("desktop-", "");
  const start = Date.now();
  for (let ms = 0; ms < NIGHT_MS; ms = Date.now() - start) {
    await stage.screenshot({ path: `${OUT}/night-${theme}/${String(ms).padStart(5, "0")}.png` });
  }
});
