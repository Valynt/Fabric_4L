#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DOMAIN_COVERAGE_MATRIX: dict[str, dict[str, list[str]]] = {
    'auth': {
        'frontend': [
            'apps/web/src/api/__tests__/contract/accounts-create.contract.test.ts',
            'apps/web/src/api/__tests__/contract/domain-coverage.contract.test.ts',
        ],
        'backend': [
            'tests/contract/test_state_inspector_auth_contract.py',
            'tests/contract/test_unauthenticated_route_inventory.py',
        ],
    },
    'billing': {
        'frontend': [
            'apps/web/src/api/__tests__/contract/accounts-create.contract.test.ts',
            'apps/web/src/api/__tests__/contract/domain-coverage.contract.test.ts',
        ],
        'backend': ['tests/contract/test_system_route_contract.py'],
    },
    'workflows': {
        'frontend': ['apps/web/src/api/__tests__/contract/workflows.contract.test.ts'],
        'backend': [
            'tests/contract/test_l4_workflows_contract.py',
            'tests/contract/test_journey_contracts.py',
        ],
    },
    'admin': {
        'frontend': [
            'apps/web/src/api/__tests__/contract/governance.contract.test.ts',
            'apps/web/src/api/__tests__/contract/domain-coverage.contract.test.ts',
        ],
        'backend': [
            'tests/contract/test_system_route_contract.py',
            'tests/contract/test_api_main_architecture.py',
        ],
    },
    'data': {
        'frontend': [
            'apps/web/src/api/__tests__/contract/graph.contract.test.ts',
            'apps/web/src/api/__tests__/contract/extraction.contract.test.ts',
            'apps/web/src/api/__tests__/contract/domain-coverage.contract.test.ts',
        ],
        'backend': [
            'tests/contract/test_layer3_contract.py',
            'tests/contract/test_layer5_contract.py',
        ],
    },
}


def main() -> int:
    missing: list[str] = []
    for domain, scopes in DOMAIN_COVERAGE_MATRIX.items():
        for scope, files in scopes.items():
            if not files:
                missing.append(f'{domain}:{scope}:<empty>')
                continue
            for rel in files:
                if not (REPO_ROOT / rel).exists():
                    missing.append(f'{domain}:{scope}:{rel}')

    print('Contract endpoint family coverage gate')
    print('Required domains:', ', '.join(sorted(DOMAIN_COVERAGE_MATRIX.keys())))
    if missing:
        print('Missing coverage entries:')
        for item in missing:
            print('-', item)
        return 1

    print('All required endpoint families are represented in contract tests.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
