import re

with open('services/layer4-agents/src/layer4_agents/tools/crm_tools.py', 'r') as f:
    content = f.read()

# Apply the CRM fix exactly
content = content.replace(
    'prospect_id = self._soql_safe_id(input_data.prospect_id)',
    'prospect_id = self._validate_sfdc_id(input_data.prospect_id)\n        safe_id = self._soql_safe_id(prospect_id)'
)

content = content.replace(
    'WHERE WhatId = \'{prospect_id}\'{since_clause}{type_filter}',
    'WHERE WhatId = \'{safe_id}\'{since_clause}{type_filter}'
)

with open('services/layer4-agents/src/layer4_agents/tools/crm_tools.py', 'w') as f:
    f.write(content)
