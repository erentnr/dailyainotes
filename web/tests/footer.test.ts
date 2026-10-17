import { describe, expect, it } from "vitest";

import { footerLinks, webPage } from "../src/lib/footer";

describe("footerLinks", () => {
  it("shows a link for each address that is set", () => {
    expect(
      footerLinks({
        sourceUrl: "https://github.com/someone/dailyainotes",
        authorName: "Someone",
        authorUrl: "https://someone.example",
      }),
    ).toEqual([
      { href: "https://github.com/someone/dailyainotes", label: "Source code" },
      { href: "https://someone.example/", label: "Made by Someone" },
    ]);
  });

  it("shows nothing when no address is set, as in a fresh fork", () => {
    expect(footerLinks({})).toEqual([]);
    expect(footerLinks({ sourceUrl: "", authorName: "Someone", authorUrl: "" })).toEqual([]);
  });

  it("names the author by the site's host when no name is set", () => {
    expect(footerLinks({ authorUrl: "https://someone.example" })).toEqual([
      { href: "https://someone.example/", label: "Made by someone.example" },
    ]);
  });

  it("refuses an address that is not a web page", () => {
    expect(footerLinks({ sourceUrl: "javascript:alert(1)", authorUrl: "not a url" })).toEqual([]);
  });
});

describe("webPage", () => {
  it("keeps a web address and drops anything else", () => {
    expect(webPage("https://github.com/someone/dailyainotes")).toBe("https://github.com/someone/dailyainotes");
    expect(webPage("")).toBeNull();
    expect(webPage(undefined)).toBeNull();
    expect(webPage("javascript:alert(1)")).toBeNull();
  });
});
