from pathlib import Path
import difflib
root = Path('C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src/layer1_ingestion/api')
main = (root / 'main.py').read_text(encoding='utf-8').splitlines()
mono = (root / 'app_monolith.py').read_text(encoding='utf-8').splitlines()
print('main.py lines:', len(main))
print('app_monolith.py lines:', len(mono))
sm = difflib.SequenceMatcher(None, main, mono)
print('similarity ratio:', sm.ratio())
for i, (op, a1, a2, b1, b2) in enumerate(sm.get_opcodes()):
    if op != 'equal':
        print(op, a1, a2, b1, b2)
        print('main:', main[a1:a2])
        print('mono:', mono[b1:b2])
        if i >= 5:
            break
