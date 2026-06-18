txt = open('C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src/api/app_monolith.py', encoding='utf-8').read().splitlines()
for i, line in enumerate(txt, 1):
    if any(k in line for k in ['BatchOperation', 'get_target_stats', 'batch_operation', 'TargetStatsResponse', 'compatibility_routes', 'app =', 'def create_app', 'app.include_router']):
        print(f'{i}: {line[:120]}')
