import re

with open("tests/ci/test_bunnyshell_environment_contract.py", "r") as f:
    content = f.read()

content = content.replace('BUNNYSHELL_PATH = REPO_ROOT / "bunnyshell.yaml"', '''
BUNNYSHELL_PATHS = [REPO_ROOT / "bunnyshell.yaml", REPO_ROOT / "bunnyshell-pr.yaml"]
def _load_bunnyshell(path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
''')

# We need to replace all calls to _load_bunnyshell() and text = BUNNYSHELL_PATH.read_text
content = re.sub(r'def test_([a-zA-Z0-9_]+)\(\):', r'import pytest\n@pytest.mark.parametrize("bunnyshell_path", BUNNYSHELL_PATHS)\ndef test_\1(bunnyshell_path):', content)
content = content.replace('config = _load_bunnyshell()', 'config = _load_bunnyshell(bunnyshell_path)')
content = content.replace('text = BUNNYSHELL_PATH.read_text(encoding="utf-8")', 'text = bunnyshell_path.read_text(encoding="utf-8")')

# remove the original _load_bunnyshell definition
content = re.sub(r'def _load_bunnyshell\(\) -> dict:\n(?:    .*\n)+', '', content)

with open("tests/ci/test_bunnyshell_environment_contract.py", "w") as f:
    f.write(content)
