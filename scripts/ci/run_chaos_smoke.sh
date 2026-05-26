#!/usr/bin/env bash
set -euo pipefail

pytest tests/backend_integrated/test_chaos_smoke_validation.py -m backend_integrated -q
