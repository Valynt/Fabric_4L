import re

with open("apps/web/src/pages/admin/AdminPages.test.tsx", "r") as f:
    content = f.read()

# Replace all <<<<<<< HEAD ... ======= ... >>>>>>> feat/billing-admin-page
# by concatenating both parts.
content = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> feat/billing-admin-page', r'\1\n\2', content, flags=re.DOTALL)

with open("apps/web/src/pages/admin/AdminPages.test.tsx", "w") as f:
    f.write(content)
