import sys
import importlib.abc
import importlib.util

class RedirectFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        prefixes = ['api', 'db', 'agents', 'graph', 'analytics', 'metrics', 'models', 'retrieval', 'schema', 'services', 'utils', 'cache', 'config']
        for prefix in prefixes:
            if fullname == prefix or fullname.startswith(prefix + '.'):
                src_name = 'src.' + fullname
                try:
                    spec = importlib.util.find_spec(src_name)
                    if spec is not None:
                        return spec
                except Exception:
                    pass
        return None

sys.meta_path.insert(0, RedirectFinder())

# Setup path
if 'services/layer3-knowledge/src' in sys.path:
    sys.path.remove('services/layer3-knowledge/src')
if 'services/layer3-knowledge' not in sys.path:
    sys.path.insert(0, 'services/layer3-knowledge')

# Test
from api.dependencies_tenant_secured import require_request_tenant_id
print('Success!')
