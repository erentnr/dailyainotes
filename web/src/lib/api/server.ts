import { API_URL } from "astro:env/server";

import { api } from "./client";

/** For pages rendered on the server. */
export const serverApi = () => api(API_URL);
