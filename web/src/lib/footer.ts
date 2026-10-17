export interface FooterLink {
  href: string;
  label: string;
  /** The source link's icon: GitHub's mark only when the code is on github.com. */
  icon?: "github" | "code";
}

/** The footer's links, from the site's settings: each one appears only when its address is set,
 * so a fork shows its own links, or none, without a code change. */
export function footerLinks(settings: {
  sourceUrl?: string;
  authorName?: string;
  authorUrl?: string;
}): FooterLink[] {
  const links: FooterLink[] = [];
  const source = webAddress(settings.sourceUrl);
  if (source) {
    const github = source.hostname === "github.com" || source.hostname === "www.github.com";
    links.push({ href: source.href, label: "Source code", icon: github ? "github" : "code" });
  }
  const author = webAddress(settings.authorUrl);
  if (author) links.push({ href: author.href, label: `Made by ${settings.authorName?.trim() || author.host}` });
  return links;
}

/** The address as a link, when it is a web page; null otherwise, or when it is empty. */
export function webPage(value: string | undefined): string | null {
  return webAddress(value)?.href ?? null;
}

function webAddress(value: string | undefined): URL | null {
  try {
    const url = new URL(value ?? "");
    return url.protocol === "https:" || url.protocol === "http:" ? url : null;
  } catch {
    return null;
  }
}
