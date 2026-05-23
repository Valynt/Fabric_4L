
import sys
print('=== SYS.PATH ===')
for i, p in enumerate(sys.path):
    if 'layer' in p.lower() or 'Fabric_4L' in p:
        print(f'{i}: {p}')
