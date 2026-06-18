lines = open('C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src/layer1_ingestion/api/main.py', encoding='utf-8').read().splitlines()
for i, line in enumerate(lines, 1):
    if 'include_router' in line:
        print(f'{i}: {line[:120]}')
