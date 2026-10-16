/** Reader accounts in the browser (ADR 0003). The session cookie is HttpOnly, so scripts never
 * see it; they only know whether someone is signed in from the page. */

export const SESSION_COOKIE = "dan_session";

/** Where to go after signing in: a path on this site only, never another origin. Browsers drop
 * tabs and line breaks from URLs, so "/\t/evil.example" would become "//evil.example"; any
 * control character is refused. */
export function safeNext(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(value)) {
    return "/";
  }
  return value;
}
