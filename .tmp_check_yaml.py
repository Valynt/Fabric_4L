with open(r'c:\Users\BBB\Fabric_4L\.github\workflows\prod-readiness.yml', 'r') as f:
    lines = f.readlines()
for i in range(400, 432):
    line = lines[i]
    prefix = line[:len(line) - len(line.lstrip())]
    print(f'{i+1}: {len(prefix)} spaces, repr={repr(prefix)}, first={repr(line[:50])}')
