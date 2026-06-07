import re

files_to_fix = [
    ('services/layer5-ground-truth/src/layer5_ground_truth/models/benchmark_governance.py',
     'class BenchmarkDataset(Base):\n    __tablename__ = "benchmark_datasets"',
     'class BenchmarkDataset(Base):\n    __tablename__ = "benchmark_datasets"\n    __table_args__ = {"extend_existing": True}'),
    ('services/layer5-ground-truth/src/layer5_ground_truth/models/policy_governance.py',
     'class PolicyRule(Base):\n    __tablename__ = "policy_rules"',
     'class PolicyRule(Base):\n    __tablename__ = "policy_rules"\n    __table_args__ = {"extend_existing": True}'),
    ('services/layer5-ground-truth/src/layer5_ground_truth/models/approval_workflow.py',
     'class ApprovalRequest(Base):\n    __tablename__ = "approval_requests"',
     'class ApprovalRequest(Base):\n    __tablename__ = "approval_requests"\n    __table_args__ = {"extend_existing": True}'),
    ('services/layer5-ground-truth/src/layer5_ground_truth/models/approval_workflow.py',
     'class ApprovalDecision(Base):\n    __tablename__ = "approval_decisions"',
     'class ApprovalDecision(Base):\n    __tablename__ = "approval_decisions"\n    __table_args__ = {"extend_existing": True}'),
]

for path, old, new in files_to_fix:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if old in text:
        text = text.replace(old, new, 1)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        print(f'Fixed {path}')
    else:
        print(f'Pattern not found in {path}')
