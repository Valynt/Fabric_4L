# Scalar Interactive API Documentation — Fabric 4L v1.2.0

> **Target:** Staff+ API Engineer review ready  
> **Scope:** Interactive API docs for 6-layer FastAPI backend (L1–L6)  
> **Theme:** Fabric 4L brand — purple accent `#7c3aed`, dark mode default  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Per-Service Integration (L1–L6)](#3-per-service-integration-l1l6)
4. [Custom Theming](#4-custom-theming)
5. [Docker Compose Configuration](#5-docker-compose-configuration)
6. [Validation & Testing](#6-validation--testing)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Overview

This guide provides complete integration steps for deploying [Scalar](https://scalar.com/) interactive API documentation across all six FastAPI layers of the Fabric_4L platform. Scalar replaces the default Swagger UI with a modern, brand-aligned documentation experience that supports OpenAPI 3.1.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │  L1     │ │  L2     │ │  L3     │ │  L4     │ │  L5     ││
│  │ Ingress │ │AuthN/   │ │Core     │ │Compute  │ │Data     ││
│  │Gateway  │ │AuthZ    │ │Services │ │Engine   │ │Access   ││
│  │ :8001   │ │ :8002   │ │ :8003   │ │ :8004   │ │ :8005   ││
│  │ /docs   │ │ /docs   │ │ /docs   │ │ /docs   │ │ /docs   ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘│
│  ┌─────────┐                                                │
│  │  L6     │                                                │
│  │Observ-  │                                                │
│  │ability  │                                                │
│  │ :8006   │                                                │
│  │ /docs   │                                                │
│  └─────────┘                                                │
└─────────────────────────────────────────────────────────────┘
```

### Service Map

| Layer | Service | Port | OpenAPI Path | Scalar Path | Description |
|-------|---------|------|--------------|-------------|-------------|
| L1 | Ingress Gateway | `8001` | `/openapi.json` | `/docs` | Request routing, rate limiting, TLS termination |
| L2 | AuthN/AuthZ | `8002` | `/openapi.json` | `/docs` | Authentication, authorization, JWT/OAuth2 |
| L3 | Core Services | `8003` | `/openapi.json` | `/docs` | Business logic, workflows, entity management |
| L4 | Compute Engine | `8004` | `/openapi.json` | `/docs` | Async jobs, ML inference, batch processing |
| L5 | Data Access | `8005` | `/openapi.json` | `/docs` | Database queries, caching, search |
| L6 | Observability | `8006` | `/openapi.json` | `/docs` | Metrics, logs, traces, health checks |

---

## 2. Installation

### 2.1 Add Dependency

Add `scalar-fastapi` to each service's dependency manifest:

**`pyproject.toml` (recommended — all services)**

```toml
[project]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "scalar-fastapi>=1.0.0",  # <-- add this
]
```

**`requirements.txt` (legacy services)**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
scalar-fastapi>=1.0.0
```

### 2.2 Install

```bash
# Install across all services (run from repo root)
for dir in services/*/; do
    echo "Installing scalar-fastapi in $dir..."
    cd "$dir" && pip install scalar-fastapi && cd ../..
done

# Or via Docker (multi-stage build)
docker compose build --no-cache
```

### 2.3 Dependency Pinning

For reproducible builds, pin the exact version:

```toml
# pyproject.toml
[project]
dependencies = [
    "scalar-fastapi==1.0.3",  # pinned
]
```

---

## 3. Per-Service Integration (L1–L6)

### 3.1 L1 — Ingress Gateway (`services/l1-gateway/`)

**File:** `services/l1-gateway/src/main.py`

```python
"""
Fabric 4L — Layer 1: Ingress Gateway
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 1: Ingress Gateway",
    description=(
        "Request routing, rate limiting, TLS termination, and load balancing "
        "for the Fabric 4L platform. All external traffic enters through this layer."
    ),
    version="1.2.0",
    docs_url=None,      # Disable default Swagger UI
    redoc_url=None,     # Disable default ReDoc
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Routing", "description": "Dynamic and static route management"},
        {"name": "Rate Limiting", "description": "Throttle and quota controls"},
        {"name": "TLS", "description": "Certificate and termination management"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 1: Ingress Gateway",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        """,
    )
```

### 3.2 L2 — AuthN/AuthZ (`services/l2-auth/`)

**File:** `services/l2-auth/src/main.py`

```python
"""
Fabric 4L — Layer 2: Authentication & Authorization
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 2: AuthN/AuthZ",
    description=(
        "Identity verification, JWT token management, OAuth2 flows, RBAC, "
        "and API key authentication for the Fabric 4L platform."
    ),
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Authentication", "description": "Login, logout, token refresh"},
        {"name": "Authorization", "description": "Permissions, roles, policies"},
        {"name": "OAuth2", "description": "OAuth2 and OIDC flow endpoints"},
        {"name": "API Keys", "description": "Key generation and revocation"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 2: AuthN/AuthZ",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        .scalar-auth-container {
            border: 1px solid #7c3aed40;
            border-radius: 8px;
            background: #7c3aed0d;
        }
        """,
    )
```

### 3.3 L3 — Core Services (`services/l3-core/`)

**File:** `services/l3-core/src/main.py`

```python
"""
Fabric 4L — Layer 3: Core Services
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 3: Core Services",
    description=(
        "Business logic engine, workflow orchestration, entity lifecycle management, "
        "and domain-specific operations for the Fabric 4L platform."
    ),
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Workflows", "description": "Create, execute, and manage workflows"},
        {"name": "Entities", "description": "CRUD operations for domain entities"},
        {"name": "Events", "description": "Event publishing and subscription"},
        {"name": "Policies", "description": "Business rule and policy engine"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 3: Core Services",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        """,
    )
```

### 3.4 L4 — Compute Engine (`services/l4-compute/`)

**File:** `services/l4-compute/src/main.py`

```python
"""
Fabric 4L — Layer 4: Compute Engine
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 4: Compute Engine",
    description=(
        "Asynchronous job processing, ML model inference, batch computations, "
        "and distributed task execution for the Fabric 4L platform."
    ),
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Jobs", "description": "Submit, monitor, and manage compute jobs"},
        {"name": "Inference", "description": "ML model inference endpoints"},
        {"name": "Batch", "description": "Batch processing operations"},
        {"name": "Workers", "description": "Worker pool and queue management"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 4: Compute Engine",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        .scalar-badge { font-variant-numeric: tabular-nums; }
        """,
    )
```

### 3.5 L5 — Data Access (`services/l5-data/`)

**File:** `services/l5-data/src/main.py`

```python
"""
Fabric 4L — Layer 5: Data Access
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 5: Data Access",
    description=(
        "Database abstraction, query optimization, caching layer, full-text search, "
        "and data persistence services for the Fabric 4L platform."
    ),
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Queries", "description": "Execute and optimize database queries"},
        {"name": "Cache", "description": "Cache management and invalidation"},
        {"name": "Search", "description": "Full-text and vector search operations"},
        {"name": "Migrations", "description": "Schema migration tools"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 5: Data Access",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        .scalar-code-block {
            font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        }
        """,
    )
```

### 3.6 L6 — Observability (`services/l6-observability/`)

**File:** `services/l6-observability/src/main.py`

```python
"""
Fabric 4L — Layer 6: Observability
Scalar Interactive API Documentation Integration
"""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Fabric 4L API — Layer 6: Observability",
    description=(
        "Metrics collection, log aggregation, distributed tracing, health checks, "
        "and alerting for the Fabric 4L platform."
    ),
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Metrics", "description": "Prometheus-compatible metrics endpoints"},
        {"name": "Logs", "description": "Log query and aggregation"},
        {"name": "Traces", "description": "Distributed trace retrieval and analysis"},
        {"name": "Health", "description": "Service health and readiness probes"},
        {"name": "Alerts", "description": "Alert rule and notification management"},
    ],
)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """Serve Scalar interactive API documentation."""
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer 6: Observability",
        theme="moon",
        hide_models=True,
        custom_css="""
        :root {
            --scalar-color-accent: #7c3aed;
            --scalar-color-1: #f8fafc;
            --scalar-color-2: #94a3b8;
            --scalar-color-3: #64748b;
            --scalar-color-green: #22c55e;
            --scalar-color-red: #ef4444;
            --scalar-color-yellow: #eab308;
            --scalar-background-1: #0f172a;
            --scalar-background-2: #1e293b;
            --scalar-background-3: #334155;
            --scalar-background-accent: #7c3aed1a;
            --scalar-border-color: #334155;
            --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .scalar-api-reference { font-family: var(--scalar-font); }
        .scalar-sidebar { background: var(--scalar-background-2) !important; }
        .scalar-sidebar-heading {
            color: #7c3aed !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em;
        }
        .scalar-endpoint-health {
            border-left: 3px solid #22c55e;
        }
        """,
    )
```

### 3.7 Shared Scalar Configuration (DRY Alternative)

For services that share a codebase, extract the common configuration:

**File:** `services/_shared/scalar_config.py`

```python
"""Shared Scalar configuration for all Fabric 4L services."""

from typing import Final

# Fabric 4L Brand Colors
FABRIC_PURPLE: Final[str] = "#7c3aed"
FABRIC_SLATE_900: Final[str] = "#0f172a"
FABRIC_SLATE_800: Final[str] = "#1e293b"
FABRIC_SLATE_700: Final[str] = "#334155"
FABRIC_SLATE_400: Final[str] = "#94a3b8"
FABRIC_SLATE_500: Final[str] = "#64748b"

SCALAR_BASE_CSS: Final[str] = f"""
:root {{
    --scalar-color-accent: {{FABRIC_PURPLE}};
    --scalar-color-1: #f8fafc;
    --scalar-color-2: {{FABRIC_SLATE_400}};
    --scalar-color-3: {{FABRIC_SLATE_500}};
    --scalar-color-green: #22c55e;
    --scalar-color-red: #ef4444;
    --scalar-color-yellow: #eab308;
    --scalar-background-1: {{FABRIC_SLATE_900}};
    --scalar-background-2: {{FABRIC_SLATE_800}};
    --scalar-background-3: {{FABRIC_SLATE_700}};
    --scalar-background-accent: {{FABRIC_PURPLE}}1a;
    --scalar-border-color: {{FABRIC_SLATE_700}};
    --scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}
.scalar-api-reference {{ font-family: var(--scalar-font); }}
.scalar-sidebar {{ background: var(--scalar-background-2) !important; }}
.scalar-sidebar-heading {{
    color: {{FABRIC_PURPLE}} !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em;
}}
"""


def build_scalar_css(extra_css: str = "") -> str:
    """Build the custom CSS string for Scalar theming.

    Args:
        extra_css: Additional CSS rules to append (service-specific).

    Returns:
        Complete CSS string for Scalar custom_css parameter.
    """
    css = SCALAR_BASE_CSS.replace("{{FABRIC_PURPLE}}", FABRIC_PURPLE)
    css = css.replace("{{FABRIC_SLATE_900}}", FABRIC_SLATE_900)
    css = css.replace("{{FABRIC_SLATE_800}}", FABRIC_SLATE_800)
    css = css.replace("{{FABRIC_SLATE_700}}", FABRIC_SLATE_700)
    css = css.replace("{{FABRIC_SLATE_400}}", FABRIC_SLATE_400)
    css = css.replace("{{FABRIC_SLATE_500}}", FABRIC_SLATE_500)
    if extra_css:
        css += f"\n{extra_css}"
    return css
```

**Usage in each service:**

```python
from scalar_fastapi import get_scalar_api_reference
from _shared.scalar_config import build_scalar_css

@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API — Layer N",
        theme="moon",
        hide_models=True,
        custom_css=build_scalar_css(extra_css=".my-class { color: red; }"),
    )
```

---

## 4. Custom Theming

### 4.1 Theme Options

| Theme | Description | Best For |
|-------|-------------|----------|
| `moon` | Dark slate background (default) | Primary — matches Fabric 4L brand |
| `deep-space` | Deep navy with subtle gradients | Alternative dark mode |
| `purple` | Purple-tinted dark theme | Brand-aligned variant |
| `none` | System/browser preference | Accessibility mode |

### 4.2 Brand Color Tokens

```css
/* Fabric 4L Brand Tokens — Scalar CSS Variables */
:root {
    /* Primary Accent */
    --scalar-color-accent: #7c3aed;        /* Fabric Purple 600 */
    --scalar-color-accent-light: #a78bfa;   /* Fabric Purple 400 */
    --scalar-color-accent-dark: #5b21b6;    /* Fabric Purple 800 */

    /* Text Colors */
    --scalar-color-1: #f8fafc;             /* Slate 50 — primary text */
    --scalar-color-2: #94a3b8;             /* Slate 400 — secondary text */
    --scalar-color-3: #64748b;             /* Slate 500 — tertiary text */

    /* Semantic Colors */
    --scalar-color-green: #22c55e;          /* Success */
    --scalar-color-red: #ef4444;            /* Error / Breaking */
    --scalar-color-yellow: #eab308;         /* Warning / Deprecated */
    --scalar-color-blue: #3b82f6;           /* Info */

    /* Background Colors */
    --scalar-background-1: #0f172a;         /* Slate 900 — page bg */
    --scalar-background-2: #1e293b;         /* Slate 800 — card/sidebar bg */
    --scalar-background-3: #334155;         /* Slate 700 — elevated bg */
    --scalar-background-accent: #7c3aed1a;  /* Purple 600 at 10% */

    /* Border */
    --scalar-border-color: #334155;         /* Slate 700 */
}
```

### 4.3 Typography

```css
/* Font Stack */
--scalar-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--scalar-font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;

/* Load Inter from Google Fonts (add to custom_css) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

### 4.4 Dark Mode as Default

The `theme="moon"` parameter sets dark mode by default. To allow users to toggle:

```python
@app.get("/docs", include_in_schema=False)
async def scalar_html(theme: str = "moon"):
    """Serve Scalar with optional theme override.

    Query param `theme` can be: moon, purple, deep-space
    """
    valid_themes = {"moon", "purple", "deep-space", "none"}
    selected_theme = theme if theme in valid_themes else "moon"

    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Fabric 4L API",
        theme=selected_theme,
        hide_models=True,
        custom_css=build_scalar_css(),
    )
```

---

## 5. Docker Compose Configuration

### 5.1 Complete `docker-compose.docs.yml`

```yaml
# =============================================================================
# Fabric 4L — Scalar Interactive Documentation
# Docker Compose Overlay for Documentation Services
# =============================================================================
version: "3.9"

services:
  # ── L1: Ingress Gateway ──────────────────────────────────────────────────
  l1-gateway:
    build:
      context: ./services/l1-gateway
      dockerfile: Dockerfile
    container_name: fabric-l1-gateway
    ports:
      - "8001:8000"
    environment:
      - SERVICE_NAME=l1-gateway
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L1"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── L2: AuthN/AuthZ ──────────────────────────────────────────────────────
  l2-auth:
    build:
      context: ./services/l2-auth
      dockerfile: Dockerfile
    container_name: fabric-l2-auth
    ports:
      - "8002:8000"
    environment:
      - SERVICE_NAME=l2-auth
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L2"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── L3: Core Services ────────────────────────────────────────────────────
  l3-core:
    build:
      context: ./services/l3-core
      dockerfile: Dockerfile
    container_name: fabric-l3-core
    ports:
      - "8003:8000"
    environment:
      - SERVICE_NAME=l3-core
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L3"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── L4: Compute Engine ───────────────────────────────────────────────────
  l4-compute:
    build:
      context: ./services/l4-compute
      dockerfile: Dockerfile
    container_name: fabric-l4-compute
    ports:
      - "8004:8000"
    environment:
      - SERVICE_NAME=l4-compute
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L4"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── L5: Data Access ──────────────────────────────────────────────────────
  l5-data:
    build:
      context: ./services/l5-data
      dockerfile: Dockerfile
    container_name: fabric-l5-data
    ports:
      - "8005:8000"
    environment:
      - SERVICE_NAME=l5-data
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L5"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── L6: Observability ────────────────────────────────────────────────────
  l6-observability:
    build:
      context: ./services/l6-observability
      dockerfile: Dockerfile
    container_name: fabric-l6-observability
    ports:
      - "8006:8000"
    environment:
      - SERVICE_NAME=l6-observability
      - DOCS_PATH=/docs
      - OPENAPI_URL=/openapi.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "fabric.layer=L6"
      - "fabric.docs.enabled=true"
      - "fabric.docs.path=/docs"

  # ── Documentation Aggregator (Optional) ──────────────────────────────────
  # Serves a unified docs portal linking to all 6 layer docs
  docs-aggregator:
    image: nginx:alpine
    container_name: fabric-docs-aggregator
    ports:
      - "8080:80"
    volumes:
      - ./docs/aggregator/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./docs/aggregator/index.html:/usr/share/nginx/html/index.html:ro
    depends_on:
      - l1-gateway
      - l2-auth
      - l3-core
      - l4-compute
      - l5-data
      - l6-observability
    labels:
      - "fabric.service=docs-aggregator"

networks:
  default:
    name: fabric-4l-network
    driver: bridge
```

### 5.2 Quick Start Commands

```bash
# Start all services with docs
docker compose -f docker-compose.yml -f docker-compose.docs.yml up -d

# Verify docs are accessible
curl -s http://localhost:8001/docs | head -20
curl -s http://localhost:8002/docs | head -20
curl -s http://localhost:8003/docs | head -20
curl -s http://localhost:8004/docs | head -20
curl -s http://localhost:8005/docs | head -20
curl -s http://localhost:8006/docs | head -20

# View in browser
open http://localhost:8001/docs  # L1 Gateway
open http://localhost:8002/docs  # L2 Auth
open http://localhost:8003/docs  # L3 Core
open http://localhost:8004/docs  # L4 Compute
open http://localhost:8005/docs  # L5 Data
open http://localhost:8006/docs  # L6 Observability

# Unified docs portal
open http://localhost:8080
```

### 5.3 Makefile Targets

```makefile
# Makefile — Documentation targets

.PHONY: docs-up docs-down docs-health docs-open

## Start all services with Scalar documentation
docs-up:
	docker compose -f docker-compose.yml -f docker-compose.docs.yml up -d --build

## Stop documentation services
docs-down:
	docker compose -f docker-compose.yml -f docker-compose.docs.yml down

## Check health of all documentation endpoints
docs-health:
	@echo "Checking Scalar docs health..."
	@for port in 8001 8002 8003 8004 8005 8006; do \
		status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$$port/docs 2>/dev/null || echo "000"); \
		if [ "$$status" = "200" ]; then \
			echo "  ✓ L$$((port-8000)) (port $$port): OK ($$status)"; \
		else \
			echo "  ✗ L$$((port-8000)) (port $$port): FAIL ($$status)"; \
		fi; \
	done

## Open all documentation pages in browser (macOS)
docs-open:
	@for port in 8001 8002 8003 8004 8005 8006; do \
		open http://localhost:$$port/docs; \
	done
```

---

## 6. Validation & Testing

### 6.1 Automated Health Checks

**File:** `tests/integration/test_scalar_docs.py`

```python
"""Integration tests for Scalar documentation endpoints across all 6 layers."""

import pytest
import requests

# Service endpoints
SERVICES = {
    "L1-IngressGateway": "http://localhost:8001",
    "L2-AuthNAuthZ": "http://localhost:8002",
    "L3-CoreServices": "http://localhost:8003",
    "L4-ComputeEngine": "http://localhost:8004",
    "L5-DataAccess": "http://localhost:8005",
    "L6-Observability": "http://localhost:8006",
}


@pytest.mark.parametrize("name,base_url", SERVICES.items())
def test_scalar_docs_endpoint(name: str, base_url: str):
    """Verify Scalar /docs endpoint returns HTML with 200 status."""
    response = requests.get(f"{base_url}/docs", timeout=10)
    assert response.status_code == 200, f"{name}: Expected 200, got {response.status_code}"
    assert "text/html" in response.headers["content-type"]
    assert "scalar" in response.text.lower(), f"{name}: Scalar not found in response"


@pytest.mark.parametrize("name,base_url", SERVICES.items())
def test_openapi_json_endpoint(name: str, base_url: str):
    """Verify /openapi.json returns valid OpenAPI spec."""
    response = requests.get(f"{base_url}/openapi.json", timeout=10)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    spec = response.json()
    assert spec.get("openapi", "").startswith("3."), f"{name}: Not OpenAPI 3.x"
    assert "info" in spec
    assert "paths" in spec
    assert "title" in spec["info"]


@pytest.mark.parametrize("name,base_url", SERVICES.items())
def test_scalar_theme_loaded(name: str, base_url: str):
    """Verify Scalar dark theme (moon) CSS is present."""
    response = requests.get(f"{base_url}/docs", timeout=10)
    assert response.status_code == 200

    html = response.text
    # Check for theme indicator
    assert "moon" in html or "data-theme" in html, f"{name}: Theme not detected"
    # Check for custom brand color
    assert "7c3aed" in html, f"{name}: Brand color not found"


@pytest.mark.parametrize("name,base_url", SERVICES.items())
def test_default_swagger_disabled(name: str, base_url: str):
    """Ensure default /docs (Swagger) and /redoc are disabled."""
    swagger_response = requests.get(f"{base_url}/docs", timeout=10)
    # Should return Scalar HTML, not Swagger UI
    assert "swagger-ui" not in swagger_response.text.lower(), f"{name}: Swagger UI still active"

    redoc_response = requests.get(f"{base_url}/redoc", timeout=10)
    assert redoc_response.status_code in (404, 307, 308), f"{name}: ReDoc still accessible"


def test_all_services_respond():
    """Smoke test: all 6 services respond on their docs endpoints."""
    failures = []
    for name, base_url in SERVICES.items():
        try:
            resp = requests.get(f"{base_url}/docs", timeout=5)
            if resp.status_code != 200:
                failures.append(f"{name}: HTTP {resp.status_code}")
        except requests.RequestException as e:
            failures.append(f"{name}: {e}")

    assert not failures, f"Services failing: {', '.join(failures)}"
```

### 6.2 Run Tests

```bash
# Install test dependencies
pip install pytest requests

# Run integration tests
pytest tests/integration/test_scalar_docs.py -v

# Expected output:
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L1-IngressGateway] PASSED
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L2-AuthNAuthZ] PASSED
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L3-CoreServices] PASSED
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L4-ComputeEngine] PASSED
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L5-DataAccess] PASSED
# tests/integration/test_scalar_docs.py::test_scalar_docs_endpoint[L6-Observability] PASSED
# tests/integration/test_scalar_docs.py::test_openapi_json_endpoint[L1-IngressGateway] PASSED
# ... (18 tests total)
```

---

## 7. Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: scalar_fastapi` | Package not installed | `pip install scalar-fastapi` |
| `/docs` returns 404 | Route not registered | Verify `@app.get("/docs")` decorator is present |
| Default Swagger still shows | `docs_url` not disabled | Set `docs_url=None, redoc_url=None` in `FastAPI()` |
| Theme not applied | CSS syntax error | Validate CSS with a linter; check for unclosed braces |
| Brand color not visible | CSS specificity | Use `!important` on color overrides |
| CORS errors on `openapi.json` | Missing CORS middleware | Add `CORSMiddleware` with `allow_origins=["*"]` for docs |

### Debug Mode

Enable verbose logging to diagnose issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

@app.get("/docs", include_in_schema=False)
async def scalar_html():
    logging.debug("Serving Scalar docs")
    ref = get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Debug",
        theme="moon",
        hide_models=True,
        custom_css=build_scalar_css(),
    )
    logging.debug(f"Scalar response type: {type(ref)}")
    return ref
```

---

## Appendix A: Complete File Checklist

- [ ] `services/l1-gateway/src/main.py` — Scalar route added
- [ ] `services/l2-auth/src/main.py` — Scalar route added
- [ ] `services/l3-core/src/main.py` — Scalar route added
- [ ] `services/l4-compute/src/main.py` — Scalar route added
- [ ] `services/l5-data/src/main.py` — Scalar route added
- [ ] `services/l6-observability/src/main.py` — Scalar route added
- [ ] `services/_shared/scalar_config.py` — Shared config (optional)
- [ ] `docker-compose.docs.yml` — Documentation overlay
- [ ] `tests/integration/test_scalar_docs.py` — Integration tests
- [ ] `Makefile` — Documentation targets

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2025-01-15 | Initial Scalar integration for all 6 layers |
| 1.2.1 | — | Planned: unified docs aggregator portal |
