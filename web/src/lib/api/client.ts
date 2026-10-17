import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type NoteCard = components["schemas"]["NoteCard"];
export type NoteDetail = components["schemas"]["NoteDetail"];
export type Topic = components["schemas"]["Topic"];
export type Stats = components["schemas"]["Stats"];
export type Review = components["schemas"]["Review"];
export type Me = components["schemas"]["Me"];
export type Plan = components["schemas"]["Plan"];
export type Suggestion = components["schemas"]["Suggestion"];
export type AskedQuestion = components["schemas"]["AskedQuestion"];

/** The typed API client. On the server, `baseUrl` is the API's own address; in the browser it
 * is empty, so requests go to /api on the same origin (Caddy, or the dev server's proxy). */
export function api(baseUrl = "") {
  return createClient<paths>({ baseUrl });
}
