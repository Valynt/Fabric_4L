#!/usr/bin/env python3
"""Patch backend-integrated compose URLs for host-gateway compatibility.

The local validation sandbox blocks direct container-to-container traffic on the
user-defined bridge while host-published ports remain reachable from containers
through Docker's host gateway. This script keeps the compose file deterministic
by rewriting app service dependency URLs to host.docker.internal and adding the
required host-gateway alias to non-infrastructure service containers.
"""
from pathlib import Path

path = Path("infra/compose/docker-compose.backend-integrated.yml")
text = path.read_text()

replacements = {
    "http://minio:9000": "http://host.docker.internal:9000",
    "postgresql://postgres:postgres@postgres:5432/ingestion": "postgresql://postgres:postgres@host.docker.internal:5432/ingestion",
    "postgresql://postgres:postgres@postgres:5432/layer2_extraction": "postgresql://postgres:postgres@host.docker.internal:5432/layer2_extraction",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/layer4_agents": "postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/layer4_agents",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/ground_truth": "postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/ground_truth",
    "postgresql+psycopg2://postgres:postgres@postgres:5432/ground_truth": "postgresql+psycopg2://postgres:postgres@host.docker.internal:5432/ground_truth",
    "redis://redis:6379/0": "redis://host.docker.internal:6379/0",
    "bolt://neo4j:7687": "bolt://host.docker.internal:7687",
    "POSTGRES_HOST: postgres": "POSTGRES_HOST: host.docker.internal",
    "http://layer1:8000": "http://host.docker.internal:8001",
    "http://layer2:8000": "http://host.docker.internal:8002",
    "http://layer3:8001": "http://host.docker.internal:8003",
    "http://layer5:8005": "http://host.docker.internal:8005",
    "http://layer6:8006": "http://host.docker.internal:8006",
}
for old, new in replacements.items():
    text = text.replace(old, new)

services_requiring_host_gateway = {
    "minio-init",
    "layer1",
    "layer1-worker",
    "layer2",
    "layer3",
    "layer4",
    "layer5",
    "layer5-migrate",
    "layer6",
}
lines = text.splitlines()
out: list[str] = []
current_service: str | None = None
service_indent: int | None = None
service_has_extra_hosts = False
inserted_for_service: set[str] = set()

for i, line in enumerate(lines):
    stripped = line.strip()
    if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
        if current_service in services_requiring_host_gateway and not service_has_extra_hosts and current_service not in inserted_for_service:
            out.extend([
                "    extra_hosts:",
                '      - "host.docker.internal:host-gateway"',
            ])
            inserted_for_service.add(current_service)
        current_service = stripped[:-1]
        service_indent = 2
        service_has_extra_hosts = False
    if current_service in services_requiring_host_gateway and stripped == "extra_hosts:":
        service_has_extra_hosts = True
    if (
        current_service in services_requiring_host_gateway
        and not service_has_extra_hosts
        and stripped == "networks:"
        and line.startswith("    ")
        and current_service not in inserted_for_service
    ):
        out.extend([
            "    extra_hosts:",
            '      - "host.docker.internal:host-gateway"',
        ])
        inserted_for_service.add(current_service)
        service_has_extra_hosts = True
    out.append(line)

if current_service in services_requiring_host_gateway and not service_has_extra_hosts and current_service not in inserted_for_service:
    out.extend([
        "    extra_hosts:",
        '      - "host.docker.internal:host-gateway"',
    ])

path.write_text("\n".join(out) + "\n")
