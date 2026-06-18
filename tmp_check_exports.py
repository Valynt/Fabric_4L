import re
for fn in ['main.py', 'app_monolith.py']:
    p = f'C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src/layer1_ingestion/api/{fn}'
    txt = open(p, encoding='utf-8').read()
    print(f'=== {fn} ===')
    for pattern in ['BatchOperationRequest', 'BatchOperationResponse', 'BatchOperationType', 'class BatchOperationRequest', 'class BatchOperationResponse']:
        print(pattern, txt.count(pattern))
