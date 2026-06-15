import re

with open("tests/ci/test_workflow_permissions.py", "r") as f:
    content = f.read()

# remove cleanup-branches.yml
content = re.sub(r'\s*"cleanup-branches\.yml": \{.*?\},\n', '\n', content, flags=re.DOTALL)

# add contents to repo-hygiene.yml
replacement = """    "repo-hygiene.yml": {
        "contents": "deletes stale branches selected by the cleanup policy",
        "issues": "comments repository hygiene failures on pull requests",
        "pull-requests": "comments repository hygiene failures on pull requests",
    },"""
content = re.sub(r'\s*"repo-hygiene\.yml": \{.*?\},\n', '\n' + replacement + '\n', content, flags=re.DOTALL)

with open("tests/ci/test_workflow_permissions.py", "w") as f:
    f.write(content)

