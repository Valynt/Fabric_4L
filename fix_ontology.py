import re

with open('apps/web/src/pages/OntologyEditor.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

if 'import { Textarea }' not in content:
    content = content.replace(
        'import { PageShell } from "@/components";',
        'import { PageShell } from "@/components";\nimport { Textarea } from "@/components/ui/textarea";'
    )

old = '''<textarea
                value={importJson}
                onChange={(e) => setImportJson(e.target.value)}
                placeholder={`{
  "types": [...],
  "relationships": [...]
}`}
                rows={10}
                className="w-full px-3 py-2 vf-text-body-s bg-muted/50 border border-border rounded-md font-mono resize-none"
              />'''

new = '''<Textarea
                value={importJson}
                onChange={(e) => setImportJson(e.target.value)}
                placeholder={`{
  "types": [...],
  "relationships": [...]
}`}
                rows={10}
                className="w-full vf-text-body-s font-mono"
              />'''

content = content.replace(old, new)

with open('apps/web/src/pages/OntologyEditor.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed OntologyEditor')
