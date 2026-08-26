import re

with open(".github/workflows/pr-checks.yml", "r") as f:
    content = f.read()
content = re.sub(r'JWT_SECRET: ""', 'JWT_SECRET: ""\n', content)
content = re.sub(r'JWT_SECRET:\n+', 'JWT_SECRET: ""\n', content)
with open(".github/workflows/pr-checks.yml", "w") as f:
    f.write(content)

with open(".depot/workflows/pr-checks.yml", "r") as f:
    content = f.read()
content = re.sub(r'JWT_SECRET: ""', 'JWT_SECRET: ""\n', content)
content = re.sub(r'JWT_SECRET:\n+', 'JWT_SECRET: ""\n', content)
with open(".depot/workflows/pr-checks.yml", "w") as f:
    f.write(content)

with open("services/layer2-extraction/pyproject.toml", "r") as f:
    content = f.read()
content = re.sub(r'"JWT_SECRET=\n', '"JWT_SECRET=",\n', content)
with open("services/layer2-extraction/pyproject.toml", "w") as f:
    f.write(content)
