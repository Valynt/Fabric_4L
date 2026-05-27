#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml

REQUIRED_CONTROLS = {"ingress_strategy", "cors", "auth_integration", "rate_limiting_annotations"}
REQUIRED_INGRESS = "nginx-path"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy-file", type=Path, required=True)
    ap.add_argument("--profile", required=True)
    args = ap.parse_args()
    data = yaml.safe_load(args.policy_file.read_text(encoding="utf-8")) or {}
    profiles = data.get("deployment_profiles") or {}
    profile = profiles.get(args.profile)
    if not profile:
      print(f"Missing deployment profile '{args.profile}' in {args.policy_file}", file=sys.stderr)
      return 1
    controls = set(profile.get("required_controls") or [])
    missing = sorted(REQUIRED_CONTROLS - controls)
    if missing:
      print(f"Profile '{args.profile}' is missing required controls: {missing}", file=sys.stderr)
      return 1
    ingress = profile.get("ingress_strategy")
    if ingress != REQUIRED_INGRESS:
      print(f"Profile '{args.profile}' ingress_strategy must be '{REQUIRED_INGRESS}', got '{ingress}'", file=sys.stderr)
      return 1
    print(f"OK: deployment profile '{args.profile}' includes mandatory controls and supported ingress strategy.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
