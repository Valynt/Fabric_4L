import subprocess, sys

with open('tests/conftest.py', 'r') as f:
    content = f.read()

marker = 'for p in _PATHS_TO_ADD:\n    if p not in sys.path:\n        sys.path.insert(0, p)\n'
new_marker = marker + '\nimport sys as _sys\nprint("=== SYSPATH AFTER CONFTEST ===")\nfor _i, _p in enumerate(_sys.path):\n    if "layer" in _p.lower():\n        print(f"  {_i}: {_p}")\n'

content = content.replace(marker, new_marker)
with open('tests/conftest.py', 'w') as f:
    f.write(content)

result = subprocess.run([sys.executable, '-m', 'pytest', '-c', 'pytest.ini', '--co', 'tests/layer3/test_api_rate_limit_contract.py'], capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr[:2000])

with open('tests/conftest.py', 'r') as f:
    content = f.read()
content = content.replace(new_marker, marker)
with open('tests/conftest.py', 'w') as f:
    f.write(content)
