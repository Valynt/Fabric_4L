# Pinned to a digest fetched from the upstream registry. The `latest` tag is
# forbidden by the hermetic-build-inputs gate, and base images must be pinned
# by digest so rebuilds are reproducible. When bumping, update the digest to
# match the new tag and update docker-compose.dev.yml to match.
FROM pgbouncer/pgbouncer@sha256:aa8a38b7b33e5fe70c679053f97a8e55c74d52b00c195f0880845e52b50ce516

USER root

RUN apk add --no-cache postgresql-client

USER postgres

