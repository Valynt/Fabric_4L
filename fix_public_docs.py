import re

with open("tests/ci/test_workflow_permissions.py", "r") as f:
    content = f.read()

replacement = """    "public-docs.yml": {
        "pages": "deploys documentation to GitHub Pages",
        "id-token": "authenticates deploy job to GitHub Pages",
    },
    "refresh-testing-kpis.yml":"""
content = re.sub(r'\s*"refresh-testing-kpis\.yml":', '\n' + replacement, content, flags=re.DOTALL)

with open("tests/ci/test_workflow_permissions.py", "w") as f:
    f.write(content)

