import re

with open("apps/web/scripts/a11y/axe-critical-scan.mjs", "r") as f:
    content = f.read()

content = content.replace('const page = await browser.newPage();', 'const context = await browser.newContext();\nconst page = await context.newPage();')

with open("apps/web/scripts/a11y/axe-critical-scan.mjs", "w") as f:
    f.write(content)
