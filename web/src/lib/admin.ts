/** The /admin pages, behind Cloudflare Access (ADR 0003). */

// Ends the editor's Access session.
export const SIGN_OUT = "/cdn-cgi/access/logout";

/** Why a list could not load, from the API's status; a request that failed outright most often
 * means Access sent it to its sign-in page because the session ended. */
export function problem(status: number | undefined): string {
  if (status === 503) return "Admin is off: Cloudflare Access is not set up. Withdraw with dan review on the server.";
  if (status === 401) return "Sign in through Cloudflare Access: reload this page.";
  if (status === undefined) return "Your sign-in has ended. Reload this page to sign in again.";
  return "Admin is unavailable.";
}
