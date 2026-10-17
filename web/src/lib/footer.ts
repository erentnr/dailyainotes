export interface FooterLink {
  href: string;
  label: string;
}

/** The footer's links, from the site's settings: each one appears only when its address is set,
 * so a fork shows its own links, or none, without a code change. */
export function footerLinks(settings: {
  sourceUrl?: string;
  authorName?: string;
  authorUrl?: string;
}): FooterLink[] {
  const links: FooterLink[] = [];
  const source = webPage(settings.sourceUrl);
  if (source) links.push({ href: source, label: "Source code" });
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
