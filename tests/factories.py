"""
Test data factories for Fabric_4L test suite.
Uses factory_boy and faker for deterministic, realistic test data generation.
"""

from datetime import UTC, datetime, timezone
from typing import Any, Dict, List

import factory
from faker import Faker

fake = Faker()


class EntityFactory(factory.Factory):
    """Factory for generating test entities (capabilities, use cases, personas, value drivers)."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"entity-{n:08d}")
    name = factory.LazyAttribute(lambda _: fake.company())
    type = factory.Iterator(['capability', 'usecase', 'persona', 'valuedriver'])
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    confidence = factory.Faker('pyfloat', min_value=0.0, max_value=1.0)
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    properties = factory.LazyAttribute(lambda _: {})
    
    @factory.post_generation
    def set_type_specific_properties(obj, create, extracted, **kwargs):
        """Add type-specific properties based on entity type."""
        entity_type = obj.get('type', 'capability')
        
        if entity_type == 'capability':
            obj['properties'] = {
                'maturity': fake.random_element(['low', 'medium', 'high']),
                'scope': fake.random_element(['tactical', 'strategic', 'transformative']),
            }
        elif entity_type == 'usecase':
            obj['properties'] = {
                'priority': fake.random_element(['p0', 'p1', 'p2']),
                'status': fake.random_element(['draft', 'active', 'archived']),
            }
        elif entity_type == 'persona':
            obj['properties'] = {
                'role': fake.job(),
                'seniority': fake.random_element(['ic', 'manager', 'director', 'executive']),
            }
        elif entity_type == 'valuedriver':
            obj['properties'] = {
                'impact': fake.random_element(['cost', 'revenue', 'risk', 'time']),
                'quantifiable': fake.boolean(),
            }


class ValuePackFactory(factory.Factory):
    """Factory for generating test value packs."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"pack-{n:08d}")
    name = factory.LazyAttribute(lambda _: fake.catch_phrase())
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    status = factory.Iterator(['draft', 'published', 'archived'])
    created_by = factory.Faker('email')
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    formulas = factory.List([factory.SubFactory(EntityFactory) for _ in range(3)])
    
    @factory.post_generation
    def add_metadata(obj, create, extracted, **kwargs):
        """Add pack metadata."""
        obj['metadata'] = {
            'version': fake.numerify('1.%.#'),
            'category': fake.random_element(['industry', 'function', 'technology']),
            'tags': fake.words(nb=3),
        }


class UserFactory(factory.Factory):
    """Factory for generating test users."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"user-{n:08d}")
    email = factory.Faker('email')
    name = factory.Faker('name')
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    role = factory.Iterator(['admin', 'editor', 'viewer'])
    tier = factory.Iterator(['standard', 'advanced', 'admin'])
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    last_login = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    preferences = factory.LazyAttribute(lambda _: {
        'theme': 'system',
        'notifications': True,
        'advanced_mode': False,
    })


class FormulaFactory(factory.Factory):
    """Factory for generating test formulas."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"formula-{n:08d}")
    name = factory.LazyAttribute(lambda _: f"{fake.word().title()} Formula")
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=300))
    expression = factory.LazyAttribute(
        lambda _: f"{fake.random_element(['revenue', 'cost', 'users'])} * {fake.random_int(1, 100)}"
    )
    variables = factory.LazyAttribute(lambda _: [
        {'name': fake.word(), 'type': 'number', 'required': True}
        for _ in range(fake.random_int(1, 5))
    ])
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    status = factory.Iterator(['draft', 'submitted', 'approved', 'rejected'])
    created_by = factory.Faker('email')
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    version = factory.Sequence(lambda n: n)


class BusinessCaseFactory(factory.Factory):
    """Factory for generating test business cases."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"case-{n:08d}")
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=6))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=1000))
    status = factory.Iterator(['draft', 'review', 'approved', 'rejected'])
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    created_by = factory.Faker('email')
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    
    @factory.post_generation
    def add_financials(obj, create, extracted, **kwargs):
        """Add financial projections."""
        obj['financials'] = {
            'capex': fake.random_int(10000, 1000000),
            'opex_annual': fake.random_int(5000, 500000),
            'benefits_annual': fake.random_int(100000, 5000000),
            'roi_percent': fake.random_int(-50, 500),
            'payback_months': fake.random_int(6, 60),
        }


class ExtractionJobFactory(factory.Factory):
    """Factory for generating test extraction jobs."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"job-{n:08d}")
    source_type = factory.Iterator(['document', 'url', 'text', 'api'])
    source_url = factory.LazyAttribute(lambda _: fake.url() if fake.boolean() else None)
    status = factory.Iterator(['pending', 'processing', 'completed', 'failed'])
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    created_by = factory.Faker('email')
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    
    @factory.post_generation
    def add_results(obj, create, extracted, **kwargs):
        """Add extraction results for completed jobs."""
        if obj.get('status') == 'completed':
            obj['results'] = {
                'entities_extracted': fake.random_int(1, 50),
                'relationships_extracted': fake.random_int(0, 100),
                'processing_time_ms': fake.random_int(100, 30000),
            }


class KnowledgeGraphEdgeFactory(factory.Factory):
    """Factory for generating knowledge graph relationships."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"edge-{n:08d}")
    source_id = factory.SubFactory(EntityFactory)
    target_id = factory.SubFactory(EntityFactory)
    relationship_type = factory.Iterator([
        'enables', 'requires', 'implements', 'measures', 'owns', 'influences'
    ])
    confidence = factory.Faker('pyfloat', min_value=0.5, max_value=1.0)
    properties = factory.LazyAttribute(lambda _: {
        'strength': fake.random_element(['weak', 'medium', 'strong']),
        'direction': fake.random_element(['unidirectional', 'bidirectional']),
    })


class AuditLogEntryFactory(factory.Factory):
    """Factory for generating audit log entries."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"audit-{n:08d}")
    timestamp = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    action = factory.Iterator(['create', 'update', 'delete', 'read', 'export', 'login'])
    actor_id = factory.SubFactory(UserFactory)
    resource_type = factory.Iterator(['entity', 'value_pack', 'formula', 'user', 'business_case'])
    resource_id = factory.Faker('uuid4')
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    details = factory.LazyAttribute(lambda _: {
        'ip_address': fake.ipv4(),
        'user_agent': fake.user_agent(),
        'changes': fake.words(nb=3),
    })


class AgentWorkflowStateFactory(factory.Factory):
    """Factory for generating agent workflow states."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"workflow-{n:08d}")
    agent_type = factory.Iterator(['extractor', 'validator', 'composer', 'analyzer'])
    state = factory.Iterator(['initiated', 'drafting', 'validating', 'refining', 'composing', 'completed', 'failed'])
    prompt = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    created_by = factory.Faker('email')
    created_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    
    @factory.post_generation
    def add_checkpoint(obj, create, extracted, **kwargs):
        """Add checkpoint data for resumable workflows."""
        obj['checkpoint'] = {
            'state': obj.get('state'),
            'output_draft': fake.text(max_nb_chars=1000) if obj.get('state') in ['drafting', 'validating', 'refining'] else None,
            'validation_results': {
                'valid': fake.boolean(),
                'confidence': fake.pyfloat(min_value=0.0, max_value=1.0),
            } if obj.get('state') in ['validating', 'refining', 'composing'] else None,
        }


class SubscriptionFactory(factory.Factory):
    """Factory for generating billing subscriptions."""
    
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: f"sub-{n:08d}")
    customer_id = factory.Sequence(lambda n: f"cus-{n:08d}")
    plan_id = factory.Iterator(['starter', 'pro', 'enterprise'])
    status = factory.Iterator(['active', 'canceled', 'past_due', 'trialing'])
    tenant_id = factory.Sequence(lambda n: f"tenant-{n:04d}")
    current_period_start = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())
    current_period_end = factory.LazyFunction(
        lambda: datetime.now(UTC).replace(month=datetime.now(UTC).month + 1).isoformat()
    )
    
    @factory.post_generation
    def add_entitlements(obj, create, extracted, **kwargs):
        """Add feature entitlements based on plan."""
        plan_entitlements = {
            'starter': ['basic_search', 'entity_view'],
            'pro': ['basic_search', 'entity_view', 'advanced_analytics', 'formula_builder'],
            'enterprise': ['basic_search', 'entity_view', 'advanced_analytics', 'formula_builder', 'api_access', 'sso'],
        }
        obj['entitlements'] = plan_entitlements.get(obj.get('plan_id', 'starter'), [])


def create_batch(factory_class, count: int, **kwargs) -> list[dict[str, Any]]:
    """Create a batch of test objects using the specified factory.
    
    Args:
        factory_class: The factory class to use
        count: Number of objects to create
        **kwargs: Additional attributes to set on all objects
        
    Returns:
        List of created objects as dictionaries
    """
    return [factory_class(**kwargs) for _ in range(count)]


def create_tenant_isolated_data(tenant_id: str, entity_count: int = 10) -> dict[str, list[dict]]:
    """Create a complete set of tenant-isolated test data.
    
    Args:
        tenant_id: The tenant ID to use
        entity_count: Number of each entity type to create
        
    Returns:
        Dictionary with all tenant data
    """
    return {
        'entities': create_batch(EntityFactory, entity_count, tenant_id=tenant_id),
        'users': create_batch(UserFactory, 5, tenant_id=tenant_id),
        'value_packs': create_batch(ValuePackFactory, 3, tenant_id=tenant_id),
        'formulas': create_batch(FormulaFactory, 5, tenant_id=tenant_id),
        'business_cases': create_batch(BusinessCaseFactory, 3, tenant_id=tenant_id),
    }
