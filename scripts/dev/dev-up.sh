#!/usr/bin/env bash
# =============================================================================
# Value Fabric — Local Dev Environment Launcher
# =============================================================================
# Usage:
#   ./scripts/dev-up.sh          # Start everything
#   ./scripts/dev-up.sh --build  # Rebuild containers first
#   ./scripts/dev-up.sh down     # Tear down
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/infra/compose/docker-compose.dev.yml"
ENV_FILE="$PROJECT_ROOT/.env.dev"

# Health check configuration
MAX_WAIT_SECONDS=120
CHECK_INTERVAL=5

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║           Value Fabric — Local Dev Environment          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Detect docker compose variant early (needed for 'down' command)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif docker-compose version &>/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    echo "Install Docker Desktop or Docker Compose."
    exit 1
fi

# Handle 'down' command
if [[ "${1:-}" == "down" ]]; then
    echo -e "${YELLOW}Tearing down dev environment...${NC}"
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
    echo -e "${GREEN}Done.${NC}"
    exit 0
fi

banner

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &>/dev/null; then
    echo -e "${RED}Error: docker is not installed.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Compose available ($COMPOSE)${NC}"

# Check for .env.dev
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: .env.dev not found. Copy from template:${NC}"
    echo "  cp .env.dev.example .env.dev"
    exit 1
fi

echo -e "${GREEN}✓ .env.dev found${NC}"

JWT_SECRET_VALUE="$(awk -F= '/^JWT_SECRET=/{print $2}' "$ENV_FILE" | tail -n 1 | tr -d '[:space:]')"
if [[ -z "${JWT_SECRET_VALUE:-}" || "$JWT_SECRET_VALUE" == "CHANGE_ME_32_CHARS_MIN" ]]; then
    echo -e "${RED}Error: JWT_SECRET must be set explicitly in .env.dev.${NC}"
    echo "  Update JWT_SECRET in $ENV_FILE (copy from .env.example if needed)."
    exit 1
fi

# Optional: check for LLM keys
if grep -q "^OPENAI_API_KEY=$" "$ENV_FILE" 2>/dev/null; then
    echo -e "${YELLOW}⚠ OPENAI_API_KEY not set — ValuePilot will use heuristic mode${NC}"
    echo -e "  Set it in .env.dev for full LLM responses."
fi

# Build and start
echo ""
echo -e "${YELLOW}Starting services...${NC}"

BUILD_FLAG=""
if [[ "${1:-}" == "--build" ]]; then
    BUILD_FLAG="--build"
fi

$COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_FLAG

# Wait for health
echo ""
echo -e "${YELLOW}Waiting for services to be healthy (max ${MAX_WAIT_SECONDS}s)...${NC}"

ELAPSED=0
ALL_HEALTHY=false

while [[ $ELAPSED -lt $MAX_WAIT_SECONDS ]]; do
    # Count healthy services using docker inspect instead of parsing json
    SERVICES=$($COMPOSE -f "$COMPOSE_FILE" ps -q 2>/dev/null || true)
    TOTAL=0
    HEALTHY=0

    for container in $SERVICES; do
        TOTAL=$((TOTAL + 1))
        # Check if container is running and healthy (if healthcheck defined)
        STATE=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
        HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>/dev/null || echo "none")

        if [[ "$STATE" == "running" ]]; then
            if [[ "$HEALTH" == "none" || "$HEALTH" == "healthy" ]]; then
                HEALTHY=$((HEALTHY + 1))
            fi
        fi
    done

    echo -ne "\r  Services healthy: ${HEALTHY}/${TOTAL}  (${ELAPSED}s elapsed)"

    if [[ $HEALTHY -gt 0 && $HEALTHY -eq $TOTAL && $TOTAL -gt 0 ]]; then
        ALL_HEALTHY=true
        echo ""
        break
    fi

    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

if [[ "$ALL_HEALTHY" != "true" ]]; then
    echo ""
    echo -e "${RED}Error: Services failed to become healthy within ${MAX_WAIT_SECONDS}s${NC}"
    echo -e "  Check logs: ${CYAN}$COMPOSE -f $COMPOSE_FILE logs${NC}"
    exit 1
fi

echo -e "${GREEN}  All services healthy!${NC}"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Dev environment is ready!${NC}"
echo ""
echo -e "  ${CYAN}Frontend:${NC}  http://localhost:3001"
echo -e "  ${CYAN}Layer 4 API:${NC}  http://localhost:8004"
echo -e "  ${CYAN}Neo4j Browser:${NC}  http://localhost:7474"
echo -e "  ${CYAN}PostgreSQL:${NC}  localhost:5432 (postgres/postgres)"
echo -e "  ${CYAN}Redis:${NC}  localhost:6379"
echo ""
echo -e "  ${YELLOW}Auth:${NC} Bypassed — all requests auto-authenticated"
echo -e "  ${YELLOW}Tenant:${NC} 00000000-0000-4000-a000-000000000001"
echo ""
echo -e "  To stop:  ${CYAN}./scripts/dev-up.sh down${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
