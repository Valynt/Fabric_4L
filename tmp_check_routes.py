import sys
sys.path.insert(0, 'C:/Users/BBB/Fabric_4L/packages/shared/src')
sys.path.insert(0, 'C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src')
from layer1_ingestion.api.main import app
paths = [getattr(r, 'path', str(r)) for r in app.routes]
print('batch routes:', [p for p in paths if 'batch' in p])
print('stats routes:', [p for p in paths if 'stats' in p])
print('total routes:', len(paths))
