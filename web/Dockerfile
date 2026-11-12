# syntax=docker/dockerfile:1.7
# Pillmark web app (SvelteKit, adapter-node). Needs API_URL pointing at the API.

FROM node:22-alpine AS build
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG BUILD=local
ARG COMMIT=dev
ENV PILLMARK_BUILD=${BUILD} PILLMARK_COMMIT=${COMMIT}
RUN npm run build

FROM node:22-alpine
ARG VERSION=0.0.0-dev
ARG COMMIT=dev
LABEL org.opencontainers.image.title="pillmark-web" \
      org.opencontainers.image.description="Pillmark open pill identifier: web app" \
      org.opencontainers.image.source="https://github.com/lobojoel2003/Pillmark" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT}"
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 API_URL=http://api:8000
WORKDIR /app
# adapter-node bundles every devDependency, so the build output is self-contained.
COPY --from=build --chown=node:node /app/build ./build
COPY --from=build --chown=node:node /app/package.json ./
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:3000/healthz"]
CMD ["node", "build"]
