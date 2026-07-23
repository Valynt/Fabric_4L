# syntax=docker/dockerfile:1
FROM node@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3 AS builder
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

# Install pnpm directly instead of corepack to avoid signature-key rotation
# issues that periodically break `corepack enable` in pinned base images.
RUN npm install -g pnpm@10.18.1

# Copy workspace manifests for pnpm --filter support
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY scripts/enforce-package-manager.cjs ./scripts/enforce-package-manager.cjs
COPY apps/web/package.json ./apps/web/
COPY apps/web/scripts/enforce-package-manager.cjs ./apps/web/scripts/enforce-package-manager.cjs
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/
COPY packages/feature-flags/package.json ./packages/feature-flags/
COPY packages/platform-contract/package.json ./packages/platform-contract/
COPY packages/shared/package.json ./packages/shared/

# Install from workspace root
RUN pnpm install --frozen-lockfile --ignore-scripts

# Copy workspace source needed for the web build
COPY apps/web ./apps/web
COPY packages/config ./packages/config
COPY packages/feature-flags ./packages/feature-flags
COPY packages/platform-contract ./packages/platform-contract
COPY packages/shared ./packages/shared
RUN pnpm --filter ./apps/web build

FROM node@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3 AS runtime
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Install pnpm directly instead of corepack to avoid signature-key rotation issues.
RUN npm install -g pnpm@10.18.1

# Copy workspace manifests for pnpm --filter support
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY scripts/enforce-package-manager.cjs ./scripts/enforce-package-manager.cjs
COPY apps/web/package.json ./apps/web/
COPY apps/web/scripts/enforce-package-manager.cjs ./apps/web/scripts/enforce-package-manager.cjs
COPY packages/eslint-plugin-fabric-contracts/package.json ./packages/eslint-plugin-fabric-contracts/
COPY packages/config/package.json ./packages/config/

# Install from workspace root (production only)
# Ignore lifecycle scripts in the runtime stage: the app is already built in the
# builder stage, and dev-only workspace packages (e.g. eslint-plugin) do not need
# to compile inside the production image.
RUN pnpm install --frozen-lockfile --prod --ignore-scripts

# Security: Run as non-root user (node is built-in to node:alpine images)
# Set USER after all root-requiring operations (pnpm install)
USER node

COPY --from=builder /app/apps/web/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "dist/index.js"]
