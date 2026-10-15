import { expect, type Page, test } from "@playwright/test";

/** A reader who follows five topics, two of them sharing a cover motif, with the slots the
 * slot rule gives them. */
const FOLLOWED = [
  { slug: "formula-1", slot: 1 },
  { slug: "climate-tech", slot: 2 },
  { slug: "open-weight-ai-models", slot: 4 },
  { slug: "cybersecurity", slot: 5 },
  { slug: "astronomy-and-spaceflight", slot: 6 },
];

async function follow(page: Page, topics: typeof FOLLOWED) {
  await page.addInitScript((value) => localStorage.setItem("dan.topics", value), JSON.stringify(topics));
}

/** Islands render on the server first; wait until each can answer a click. */
async function hydrated(page: Page) {
  await page.waitForFunction(() => !document.querySelector("astro-island[ssr]"));
}

async function shoot(page: Page, name: string, project: string) {
  await page.waitForLoadState("networkidle");
  await hydrated(page);
  await page.evaluate(() => document.fonts.ready);
  // The dev server's own toolbar is not part of the site.
  await page.evaluate(() => document.querySelector("astro-dev-toolbar")?.remove());
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth, `${name} scrolls sideways`).toBeLessThanOrEqual(innerWidth);
  if (project !== "narrow") {
    await page.screenshot({ path: `screenshots/${name}-${project}.png`, fullPage: true });
  }
}

async function firstNote(page: Page, topic: string): Promise<string> {
  const response = await page.request.get(`/api/v1/notes?topic=${topic}`);
  const day = (await response.json()) as { notes: { slug: string }[] };
  const slug = day.notes[0]?.slug;
  if (!slug) throw new Error(`No note on ${topic} to look at`);
  return slug;
}

test("daily page", async ({ page }, info) => {
  await follow(page, FOLLOWED);
  await page.goto("/");
  await shoot(page, "daily", info.project.name);
});

test("daily page for a first visit", async ({ page }, info) => {
  await page.goto("/");
  await shoot(page, "daily-first-visit", info.project.name);
});

test("note", async ({ page }, info) => {
  await follow(page, FOLLOWED);
  await page.goto(`/notes/${await firstNote(page, "formula-1")}`);
  await shoot(page, "note", info.project.name);
});

test("note with a source open", async ({ page }, info) => {
  await follow(page, FOLLOWED);
  await page.goto(`/notes/${await firstNote(page, "formula-1")}`);
  await hydrated(page);
  await page.getByRole("button", { name: "Source 1" }).first().click();
  await shoot(page, "note-source", info.project.name);
});

test("topics", async ({ page }, info) => {
  await follow(page, FOLLOWED.slice(0, 2));
  await page.goto("/topics");
  await shoot(page, "topics", info.project.name);
});

test("topics with a search that finds nothing", async ({ page }, info) => {
  await page.goto("/topics");
  await hydrated(page);
  await page.getByLabel("Search topics").fill("electric ferries");
  await shoot(page, "topics-no-match", info.project.name);
});

test("ask", async ({ page }, info) => {
  await follow(page, FOLLOWED);
  await page.goto("/ask");
  await shoot(page, "ask", info.project.name);
});

for (const [name, path] of [
  ["timeline", "/topics/climate-tech"],
  ["how-it-works", "/how-it-works"],
  ["sign-in", "/sign-in"],
  ["privacy", "/privacy"],
  ["not-found", "/notes/no-such-note"],
] as const) {
  test(name, async ({ page }, info) => {
    await follow(page, FOLLOWED);
    await page.goto(path);
    await shoot(page, name, info.project.name);
  });
}
