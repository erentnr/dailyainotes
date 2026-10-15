import { defineMiddleware } from "astro:middleware";

import { SESSION_COOKIE } from "./lib/account";
import { serverApi } from "./lib/api/server";

/** Who is signed in, for every page rendered on the server. Only a request with the session
 * cookie asks the API; anonymous visits cost nothing. The API may renew the session, and its
 * renewed cookie goes back to the browser with the page. */
export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.reader = null;
  const cookie = context.request.headers.get("cookie") ?? "";
  let renewed: string | null = null;
  if (cookie.includes(`${SESSION_COOKIE}=`)) {
    const { data, response } = await serverApi().GET("/api/v1/me", { headers: { cookie } });
    context.locals.reader = data ?? null;
    renewed = response.headers.get("set-cookie");
  }
  const page = await next();
  if (renewed) page.headers.append("set-cookie", renewed);
  return page;
});
