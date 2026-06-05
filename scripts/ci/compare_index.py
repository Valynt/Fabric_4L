import re

a = open('.devin/workflows/INDEX.md', encoding='utf-8').read()
b = open('.devin/workflows/INDEX.md.generated', encoding='utf-8').read()

a_ids = set(re.findall(r'^### ([\w-]+)', a, re.M))
b_ids = set(re.findall(r'^### ([\w-]+)', b, re.M))

print('In original but not generated:', sorted(a_ids - b_ids))
print('In generated but not original:', sorted(b_ids - a_ids))
print('Total in original:', len(a_ids))
print('Total in generated:', len(b_ids))
print('Original lines:', len(a.splitlines()))
print('Generated lines:', len(b.splitlines()))
