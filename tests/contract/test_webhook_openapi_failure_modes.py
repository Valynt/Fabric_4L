from __future__ import annotations
import json
from pathlib import Path
import pytest

pytestmark = pytest.mark.contract_static_no_service


def _spec():
    return json.loads((Path(__file__).resolve().parents[2] / 'contracts/openapi/layer4-agents.json').read_text())


def test_webhook_failure_response_codes_documented() -> None:
    spec = _spec()['paths']
    assert '401' in spec['/v1/tenants/{tenant_id}/provisioning/webhook']['post']['responses']
    assert '401' in spec['/v1/webhooks/crm/salesforce']['post']['responses']
    assert '401' in spec['/v1/webhooks/crm/hubspot']['post']['responses']
    assert '400' in spec['/v1/billing/webhook']['post']['responses']


def test_webhook_failure_descriptions_match_runtime_envelopes() -> None:
    responses = _spec()['paths']
    billing_400 = responses['/v1/billing/webhook']['post']['responses']['400']['description']
    prov_401 = responses['/v1/tenants/{tenant_id}/provisioning/webhook']['post']['responses']['401']['description']
    crm_401 = responses['/v1/webhooks/crm/salesforce']['post']['responses']['401']['description']

    assert 'payload' in billing_400.lower() and 'timestamp' in billing_400.lower()
    assert 'expired timestamp' in prov_401.lower() or 'expired' in prov_401.lower()
    assert 'credentials' in crm_401.lower() or 'signature' in crm_401.lower()
