#!/usr/bin/env python3
"""Run canonical golden-path gate order for J1/J11.

Policy enforced by this runner:
- J1 backend-integrated is the canonical P0 production-readiness gate.
- J1 deep is required secondary coverage.
- J11 backend-integrated is required parallel regression coverage.
- If J1 deep fails, a non-blocking waiver is accepted only when explicitly
  allowed and documented in docs/launch/launch-blocker-register.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCKER_REGISTER = ROOT / "docs" / "launch" / "launch-blocker-register.md"

REQUIRED_WAIVER_TOKENS = (
    "j1-golden-path-deep.spec.ts",
    "pnpm --dir apps/web run test:e2e:golden:j1:deep",
    "failure summary",
    "root cause category",
    "why non-blocking for production readiness",
    "risk level",
    "owner",
    "target remediation date",
    "link to issue/pr",
    "evidence j1 backend-integrated canonical p0 still passes",
    "evidence j11 parallel regression still passes",
    "code-owner approval acknowledgment",
)

@dataclass(frozen=True)
class CommandStep:
    name: str
    command: tuple[str, ...]
    required: bool = True


def run_step(step: CommandStep) -> bool:
    print(f"\n==> {step.name}")
    print("$ " + " ".join(step.command))
    proc = subprocess.run(step.command, cwd=ROOT, text=True, shell=sys.platform.startswith("win"))
    return proc.returncode == 0


def load_blocker_register(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"missing blocker register: {path}")
    return path.read_text(encoding="utf-8").lower()


def validate_deep_waiver(path: Path) -> None:
    content = load_blocker_register(path)

    missing = [token for token in REQUIRED_WAIVER_TOKENS if token.lower() not in content]
    if missing:
        raise RuntimeError(
            "J1 deep waiver is incomplete in docs/launch/launch-blocker-register.md. "
            f"Missing required fields: {', '.join(missing)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run J1/J11 canonical golden-path gate order")
    parser.add_argument(
        "--allow-j1-deep-waiver",
        action="store_true",
        help="Allow J1 deep failure only when launch-blocker-register waiver requirements are present",
    )
    parser.add_argument(
        "--blocker-register",
        default=str(BLOCKER_REGISTER),
        help="Path to launch blocker register markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blocker_register = Path(args.blocker_register)

    steps = (
        CommandStep(
            name="Shared guard checks",
            command=("pnpm", "--dir", "apps/web", "run", "test:e2e:guard"),
        ),
        CommandStep(
            name="J1 canonical backend-integrated gate (P0)",
            command=("pnpm", "--dir", "apps/web", "run", "test:e2e:golden:j1:canonical"),
        ),
        CommandStep(
            name="J1 deep secondary journey coverage",
            command=("pnpm", "--dir", "apps/web", "run", "test:e2e:golden:j1:deep"),
            required=False,
        ),
        CommandStep(
            name="J11 parallel regression coverage",
            command=("pnpm", "--dir", "apps/web", "run", "test:e2e:golden:j11"),
        ),
        CommandStep(
            name="J1+J11 backend-integrated pair",
            command=("pnpm", "--dir", "apps/web", "run", "test:e2e:golden:pair"),
        ),
    )

    deep_failed = False
    for step in steps:
        passed = run_step(step)
        if passed:
            continue

        if step.name == "J1 deep secondary journey coverage":
            deep_failed = True
            if not args.allow_j1_deep_waiver:
                print("\nFAIL: J1 deep secondary coverage failed and no waiver flag was provided.")
                return 1

            try:
                validate_deep_waiver(blocker_register)
            except RuntimeError as exc:
                print(f"\nFAIL: {exc}")
                return 1

            print(
                "\nWARN: J1 deep failed, but waiver requirements were detected in "
                "docs/launch/launch-blocker-register.md. Continuing by policy."
            )
            continue

        print(f"\nFAIL: required step failed: {step.name}")
        return 1

    if deep_failed:
        print(
            "\nPASS WITH WAIVER: J1 canonical P0 and J11 passed; "
            "J1 deep is treated as non-blocking per documented exception policy."
        )
    else:
        print("\nPASS: J1 canonical P0 gate passed; J11 parallel regression suite also passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
