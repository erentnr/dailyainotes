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

/** The preview database's reader (MEMORY.md, Procedural Memory: a preview database). Signed in,
 * the account's topics, the same as FOLLOWED, replace the browser's. */
const PREVIEW_SESSION = "preview-reader-session";

async function signIn(page: Page) {
  await page.context().addCookies([{ name: "dan_session", value: PREVIEW_SESSION, url: "http://localhost:4321" }]);
}

async function follow(page: Page, topics: typeof FOLLOWED) {
  await page.addInitScript((value) => localStorage.setItem("dan.topics", value), JSON.stringify(topics));
}

/** Islands render on the server first; wait until each can answer a click. */
async function hydrated(page: Page) {
  await page.waitForFunction(() => !document.querySelector("astro-island[ssr]"));
}

/** Moves the page's clock on until `selector` shows, then past the parts' fade-in. */
async function playUntil(page: Page, selector: string) {
  for (let step = 0; step < 100 && !(await page.locator(selector).count()); step++) {
    await page.clock.runFor(200);
  }
  await page.clock.runFor(500);
  // CSS fades run on the browser's own time, not the test's clock.
  await page.waitForTimeout(450);
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

test("ask, signed out: the example as it plays", async ({ page }, info) => {
  // The page's clock is the test's, so each frame is the same on every run.
  await page.clock.install();
  await page.goto("/ask?q=What+happened+in+Formula+1+this+week%3F");
  await hydrated(page);
  for (const [name, mark] of [
    ["typing", ".demo-typed"],
    ["writing", ".demo-live .citation"],
    ["note-open", ".citation.is-active"],
  ] as const) {
    await playUntil(page, mark);
    await shoot(page, `ask-example-${name}`, info.project.name);
  }
});

test("ask, signed out, with less motion", async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/ask");
  await shoot(page, "ask-example-still", info.project.name);
});

test("ask, signed in", async ({ page }, info) => {
  await signIn(page);
  await page.goto("/ask");
  await shoot(page, "ask", info.project.name);
});

/** A canned answer stream, so screenshots never spend a model's free quota. */
function answer(events: [string, unknown][]) {
  return { status: 200, contentType: "text/event-stream", body: events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("") };
}

test("ask with an answer open at its citation", async ({ page }, info) => {
  await signIn(page);
  const slug = await firstNote(page, "formula-1");
  const note = (await (await page.request.get(`/api/v1/notes/${slug}`)).json()) as { title: string; edition_date: string };
  await page.route("**/api/v1/ask", (route) =>
    route.fulfill(
      answer([
        ["sources", [{ marker: 1, slug, topic: "formula-1", title: note.title, edition_date: note.edition_date }]],
        ["text", "The notes cover one Formula 1 story that day [1]."],
        ["done", { cited: [1], insufficient: false }],
      ]),
    ),
  );
  await page.goto("/ask");
  await hydrated(page);
  await page.getByLabel("Your question").fill("What happened in Formula 1 this week?");
  await page.getByLabel("Your question").press("Enter");
  await page.getByRole("button", { name: "Source 1" }).click();
  await page.getByRole("link", { name: "Open note →" }).waitFor();
  await shoot(page, "ask-answer", info.project.name);
});

test("ask when the notes fall short", async ({ page }, info) => {
  await signIn(page);
  await page.route("**/api/v1/ask", (route) =>
    route.fulfill(
      answer([
        ["sources", []],
        ["text", "Not enough in the notes to answer that."],
        ["done", { cited: [], insufficient: true }],
      ]),
    ),
  );
  await page.goto("/ask?topic=formula-1&q=Who+won+the+Istanbul+derby%3F");
  await page.getByText("Not enough in the notes to answer that.").waitFor();
  await shoot(page, "ask-not-enough", info.project.name);
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
