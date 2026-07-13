# syntax=docker/dockerfile:1
FROM node@sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625 AS builder
WORKDIR /app

# Canonical public API route prefixes for production builds. These match
# apps/web/.env.example and the gateway routing contract; they contain no
# secrets and are embedded in the browser bundle. They may be overridden at
# build time if the deployment uses non-standard gateway paths.
ARG VITE_API_BASE=/api/v1
ARG VITE_L1_PREFIX=/ingest
ARG VITE_L2_PREFIX=/extract
ARG VITE_L2_5_PREFIX=/signals
ARG VITE_L3_PREFIX=/graph
ARG VITE_L4_PREFIX=/agents
ARG VITE_L5_PREFIX=/truths
ARG VITE_L6_PREFIX=/benchmarks
ARG VITE_L7_PREFIX=/billing
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_L1_PREFIX=${VITE_L1_PREFIX}
ENV VITE_L2_PREFIX=${VITE_L2_PREFIX}
ENV VITE_L2_5_PREFIX=${VITE_L2_5_PREFIX}
ENV VITE_L3_PREFIX=${VITE_L3_PREFIX}
ENV VITE_L4_PREFIX=${VITE_L4_PREFIX}
ENV VITE_L5_PREFIX=${VITE_L5_PREFIX}
ENV VITE_L6_PREFIX=${VITE_L6_PREFIX}
ENV VITE_L7_PREFIX=${VITE_L7_PREFIX}

RUN corepack enable

# Copy workspace manifests for pnpm --filter support
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root
RUN pnpm install --frozen-lockfile

# Build only the web app using workspace filter
RUN pnpm --filter ./apps/web build

FROM node@sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625 AS runtime
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# corepack enable requires root to create symlinks in /usr/local/bin
RUN corepack enable

# Copy workspace manifests for pnpm --filter support
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root (production only)
RUN pnpm install --frozen-lockfile --prod

# Security: Run as non-root user (node is built-in to node:alpine images)
# Set USER after all root-requiring operations (corepack, pnpm install)
USER node

COPY --from=builder /app/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "dist/index.js"]
