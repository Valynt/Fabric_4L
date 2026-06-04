import os
files=[
    'apps/web/src/pages/hypothesis/HypothesisTab.tsx',
    'apps/web/src/pages/studio/StudioCompetitiveTab.tsx',
    'apps/web/src/pages/studio/StudioEnrichmentTab.tsx',
    'apps/web/src/pages/studio/StudioEvidenceTab.tsx',
    'apps/web/src/pages/studio/StudioROITab.tsx',
    'apps/web/src/components/workspace/ValueStudioShell.tsx',
]
for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as fh:
            count = sum(1 for _ in fh)
        print(f'{f}: {count} lines')
    else:
        print(f'{f}: NOT FOUND')
