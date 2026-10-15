/** Reader accounts in the browser (ADR 0003). The session cookie is HttpOnly, so scripts never
 * see it; they only know whether someone is signed in from the page. */

export const SESSION_COOKIE = "dan_session";

/** Where to go after signing in: a path on this site only, never another origin. */
export function safeNext(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return "/";
  return value;
}
