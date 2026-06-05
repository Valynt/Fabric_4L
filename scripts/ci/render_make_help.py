from __future__ import annotations

import re
import sys
from pathlib import Path


PUBLIC_TARGET = re.compile(r"^([A-Za-z0-9_.-]+):.*?##\s+(.*)$")


def iter_public_targets(paths: list[Path]) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    seen: set[str] = set()

    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue

        for line in source.splitlines():
            match = PUBLIC_TARGET.match(line)
            if match is None:
                continue
            target, description = match.groups()
            if target in seen:
                continue
            seen.add(target)
            targets.append((target, description.strip()))

    return targets


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    paths = [Path(arg) for arg in argv[1:]] or [Path("Makefile")]
    targets = iter_public_targets(paths)
    width = max((len(target) for target, _ in targets), default=0)

    for target, description in targets:
        print(f"{target:<{width}} {description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
