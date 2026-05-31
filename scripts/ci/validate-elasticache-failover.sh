#!/usr/bin/env bash
# P0-002: Validate ElastiCache automatic failover by rebooting the primary node.
# Usage: ./scripts/ci/validate-elasticache-failover.sh <replication-group-id> [timeout-seconds]

set -euo pipefail

REPLICATION_GROUP_ID="${1:-}"
TIMEOUT_SECONDS="${2:-300}"

if [[ -z "$REPLICATION_GROUP_ID" ]]; then
  echo "Usage: $0 <replication-group-id> [timeout-seconds]"
  exit 1
fi

echo "=== ElastiCache Failover Validation for ${REPLICATION_GROUP_ID} ==="

# Get current primary endpoint
PRIMARY_ENDPOINT=$(aws elasticache describe-replication-groups \
  --replication-group-id "$REPLICATION_GROUP_ID" \
  --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' \
  --output text 2>/dev/null || echo "")

if [[ -z "$PRIMARY_ENDPOINT" ]]; then
  echo "FAIL: Could not retrieve primary endpoint for ${REPLICATION_GROUP_ID}"
  exit 1
fi

echo "Current primary endpoint: ${PRIMARY_ENDPOINT}"

# Get primary node ID
PRIMARY_NODE_ID=$(aws elasticache describe-replication-groups \
  --replication-group-id "$REPLICATION_GROUP_ID" \
  --query 'ReplicationGroups[0].NodeGroups[0].NodeGroupMembers[?IsMaster==`true`].CacheClusterId' \
  --output text 2>/dev/null || echo "")

if [[ -z "$PRIMARY_NODE_ID" ]]; then
  echo "FAIL: Could not identify primary node for ${REPLICATION_GROUP_ID}"
  exit 1
fi

echo "Current primary node: ${PRIMARY_NODE_ID}"

# Trigger failover by rebooting the primary node with failover
aws elasticache reboot-cache-cluster \
  --cache-cluster-id "$PRIMARY_NODE_ID" \
  --cache-node-ids-to-reboot 1 \
  >/dev/null 2>&1 || true

echo "Triggered primary node reboot with failover..."

# Wait for failover to complete
START_TIME=$(date +%s)
NEW_PRIMARY=""

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  if [[ $ELAPSED -ge $TIMEOUT_SECONDS ]]; then
    echo "FAIL: Failover did not complete within ${TIMEOUT_SECONDS} seconds"
    exit 1
  fi

  NEW_PRIMARY=$(aws elasticache describe-replication-groups \
    --replication-group-id "$REPLICATION_GROUP_ID" \
    --query 'ReplicationGroups[0].NodeGroups[0].NodeGroupMembers[?IsMaster==`true`].CacheClusterId' \
    --output text 2>/dev/null || echo "")

  if [[ -n "$NEW_PRIMARY" && "$NEW_PRIMARY" != "$PRIMARY_NODE_ID" ]]; then
    echo "PASS: Failover completed in ${ELAPSED} seconds"
    echo "New primary node: ${NEW_PRIMARY}"
    break
  fi

  sleep 5
done

echo "=== ElastiCache Failover Validation Complete ==="
