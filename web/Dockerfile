# The site: Astro rendered on the server by Node 24 LTS.
FROM node:24.21.0-trixie-slim AS build
WORKDIR /web
# pnpm at the version package.json names.
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# The build downloads the fonts, so the server never fetches them.
RUN pnpm build && pnpm prune --prod

FROM node:24.21.0-trixie-slim
WORKDIR /web
COPY --from=build /web/package.json ./
COPY --from=build /web/node_modules ./node_modules
COPY --from=build /web/dist ./dist
ENV HOST=0.0.0.0 PORT=4321 NODE_ENV=production
USER node
EXPOSE 4321
CMD ["node", "dist/server/entry.mjs"]
