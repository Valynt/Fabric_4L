import re
from pathlib import Path

fixes = [
    # test_l3_route_contract_regression.py
    {
        "path": "tests/contract/test_l3_route_contract_regression.py",
        "replacements": [
            ('from src.api.app_monolith import app', 'from src.api.main import app'),
            (
                'pytestmark = pytest.mark.skip(\n    reason="value_fabric import path broken: package missing or SQLAlchemy duplicate table issue. Pre-existing; tracked in signoff report blocker #1/#9.")\n\nREPO_ROOT',
                'REPO_ROOT'
            ),
        ]
    },
    # test_l3_provenance_audit_contract.py
    {
        "path": "tests/contract/test_l3_provenance_audit_contract.py",
        "replacements": [
            (
                'pytestmark = pytest.mark.skip(\n    reason="value_fabric import path broken: package missing or SQLAlchemy duplicate table issue. Pre-existing; tracked in signoff report blocker #1/#9.")\n\nclass _Neo4jStub:',
                'class _Neo4jStub:'
            ),
        ]
    },
    # test_l3_route_alias_parity.py
    {
        "path": "tests/contract/test_l3_route_alias_parity.py",
        "replacements": [
            ('from src.api.app_monolith import app', 'from src.api.main import app'),
        ]
    },
]

for fix in fixes:
    p = Path(fix["path"])
    text = p.read_text(encoding='utf-8')
    for old, new in fix["replacements"]:
        if old in text:
            text = text.replace(old, new, 1)
            print(f'Fixed {p.name}: replaced')
        else:
            print(f'Fix {p.name}: pattern not found: {old[:50]}...')
    p.write_text(text, encoding='utf-8')

print('Done')
