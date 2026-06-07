import re

def insert_after_tablename(path: str, tablename: str) -> bool:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    pattern = rf'(__tablename__\s*=\s*"{tablename}")'
    
    # Check if already has extend_existing
    if '__table_args__ = {"extend_existing": True}' in text:
        idx = text.find(f'__tablename__ = "{tablename}"')
        if idx != -1 and '__table_args__' in text[idx:idx+200]:
            print(f'Skipping {path} - {tablename} already fixed')
            return True
    
    def replacer(m):
        return m.group(1) + '\n    __table_args__ = {"extend_existing": True}'
    
    new_text, count = re.subn(pattern, replacer, text, count=1)
    if count == 0:
        print(f'Pattern not found for {tablename} in {path}')
        return False
    
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(new_text)
    print(f'Fixed {tablename} in {path}')
    return True

# Fix benchmark_governance.py
insert_after_tablename(
    'services/layer5-ground-truth/src/layer5_ground_truth/models/benchmark_governance.py',
    'benchmark_datasets'
)

# Fix policy_governance.py
insert_after_tablename(
    'services/layer5-ground-truth/src/layer5_ground_truth/models/policy_governance.py',
    'policy_rules'
)

# Fix approval_workflow.py
insert_after_tablename(
    'services/layer5-ground-truth/src/layer5_ground_truth/models/approval_workflow.py',
    'approval_requests'
)
insert_after_tablename(
    'services/layer5-ground-truth/src/layer5_ground_truth/models/approval_workflow.py',
    'approval_decisions'
)
