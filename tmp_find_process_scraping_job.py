for fn in ['services/layer1-ingestion/src/api/app_monolith.py', 'services/layer1-ingestion/src/layer1_ingestion/api/main.py']:
    p = 'C:/Users/BBB/Fabric_4L/' + fn
    lines = open(p, encoding='utf-8').read().splitlines()
    print(f'=== {fn} ===')
    for i, line in enumerate(lines, 1):
        if 'process_scraping_job' in line or 'from ..shared.tasks' in line or 'from .shared.tasks' in line:
            print(f'{i}: {line[:120]}')
