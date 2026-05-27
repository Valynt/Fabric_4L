#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
checks = {
    "services/layer3-knowledge/src/tracing/middleware.py": ["build_trace_attributes", "span_name("],
    "services/layer2-extraction/src/layer2_extraction/api/main.py": ["FastAPI", "health"],
    "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py": ["/health", "APIRouter"],
    "services/layer6-benchmarks/src/api/main.py": ["/health", "register_health_endpoint"],
    "services/layer2-extraction/src/layer2_extraction/services/signal_lifecycle_service.py": ["signal"],
}
missing=[]
for file, needles in checks.items():
    p=ROOT/file
    text=p.read_text(encoding='utf-8',errors='ignore') if p.exists() else ''
    for n in needles:
        if n not in text:
            missing.append(f"{file} missing '{n}'")
if missing:
    print('Tracing smoke check failed:')
    print('\n'.join(missing))
    sys.exit(1)
print('Tracing smoke check passed.')
