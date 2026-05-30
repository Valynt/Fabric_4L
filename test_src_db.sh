#!/bin/bash
python -c "
import sys
from pathlib import Path

repo = Path('services/layer3-knowledge/src').resolve().parent.parent.parent
layer4 = repo / 'services' / 'layer4-agents' / 'src'
layer3 = repo / 'services' / 'layer3-knowledge' / 'src'

import types
src = types.ModuleType('src')
src.__package__ = 'src'
src.__path__ = [str(layer4), str(layer3)]
src.__file__ = str(repo / '<legacy-src-namespace>')
sys.modules['src'] = src

try:
    from src.db.query_execution import run_validated_query
    print('OK - src.db.query_execution imported')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1
