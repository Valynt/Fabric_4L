# syntax=docker/dockerfile:1
FROM node:22-alpine AS builder
WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
# Remove workspace-only devDependency not resolvable in standalone Docker build
RUN node -e "const p=require('./package.json'); delete (p.devDependencies||{})['eslint-plugin-fabric-contracts']; delete (p.scripts||{})['preinstall']; require('fs').writeFileSync('package.json', JSON.stringify(p,null,2))"
RUN pnpm install --no-frozen-lockfile

COPY . .
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# corepack enable requires root to create symlinks in /usr/local/bin
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
# Remove workspace-only devDependency not resolvable in standalone Docker build
RUN node -e "const p=require('./package.json'); delete (p.devDependencies||{})['eslint-plugin-fabric-contracts']; delete (p.scripts||{})['preinstall']; require('fs').writeFileSync('package.json', JSON.stringify(p,null,2))"
RUN pnpm install --no-frozen-lockfile --prod

# Security: Run as non-root user (node is built-in to node:alpine images)
# Set USER after all root-requiring operations (corepack, pnpm install)
USER node

COPY --from=builder /app/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "dist/index.js"]
