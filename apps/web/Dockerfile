# syntax=docker/dockerfile:1
FROM node@sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625 AS builder
WORKDIR /app

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
