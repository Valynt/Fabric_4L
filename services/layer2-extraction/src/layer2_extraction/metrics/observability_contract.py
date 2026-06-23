"""Observability contract for Layer 2 extraction.

Defines required log fields, metrics dimensions, and alerting rules
for production-grade observability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Required structured log fields for all extraction operations
_REQUIRED_LOG_FIELDS = {
    "tenant_id",
    "job_id",
    "extraction_stage",
    "timestamp",
    "level",
    "message",
}

# Required fields for error logs
_ERROR_LOG_FIELDS = {
    "tenant_id",
    "job_id",
    "extraction_stage",
    "error_type",
    "error_message",
    "stack_trace",
    "timestamp",
    "level",
}

# Required fields for validation logs
_VALIDATION_LOG_FIELDS = {
    "tenant_id",
    "job_id",
    "entity_type",
    "validation_rule",
    "validation_result",
    "confidence_score",
    "timestamp",
}

# Required metrics dimensions
_REQUIRED_METRIC_DIMENSIONS = {
    "tenant_id",
    "job_id",
    "extraction_stage",
    "entity_type",
    "model_version",
    "schema_version",
}


@dataclass
class ObservabilityContract:
    """Contract definition for Layer 2 observability requirements."""
    
    required_log_fields: set[str]
    error_log_fields: set[str]
    validation_log_fields: set[str]
    required_metric_dimensions: set[str]
    
    def validate_log_entry(self, log_entry: dict[str, Any], log_type: str = "general") -> tuple[bool, list[str]]:
        """Validate a log entry against the contract.
        
        Args:
            log_entry: Log entry to validate
            log_type: Type of log (general, error, validation)
            
        Returns:
            Tuple of (is_valid, list of missing fields)
        """
        if log_type == "error":
            required = self.error_log_fields
        elif log_type == "validation":
            required = self.validation_log_fields
        else:
            required = self.required_log_fields
        
        missing = [field for field in required if field not in log_entry]
        return len(missing) == 0, missing
    
    def validate_metric_dimensions(self, dimensions: dict[str, str]) -> tuple[bool, list[str]]:
        """Validate metric dimensions against the contract.
        
        Args:
            dimensions: Metric dimensions to validate
            
        Returns:
            Tuple of (is_valid, list of missing fields)
        """
        missing = [field for field in self.required_metric_dimensions if field not in dimensions]
        return len(missing) == 0, missing


# Global observability contract instance
_CONTRACT = ObservabilityContract(
    required_log_fields=_REQUIRED_LOG_FIELDS,
    error_log_fields=_ERROR_LOG_FIELDS,
    validation_log_fields=_VALIDATION_LOG_FIELDS,
    required_metric_dimensions=_REQUIRED_METRIC_DIMENSIONS,
)


def get_observability_contract() -> ObservabilityContract:
    """Get the global observability contract instance."""
    return _CONTRACT


# Alert rule definitions for production monitoring
ALERT_RULES = {
    "high_extraction_failure_rate": {
        "condition": "rate(extraction_failure_total[5m]) > 0.1",
        "severity": "critical",
        "description": "Extraction failure rate exceeds 10% over 5 minutes",
        "runbook_url": "/docs/runbooks/extraction-failures",
    },
    "high_validation_failure_rate": {
        "condition": "rate(validation_failure_total[5m]) > 0.2",
        "severity": "warning",
        "description": "Validation failure rate exceeds 20% over 5 minutes",
        "runbook_url": "/docs/runbooks/validation-failures",
    },
    "quarantine_rate_spike": {
        "condition": "rate(quarantine_records_total[10m]) > 0.05",
        "severity": "warning",
        "description": "Quarantine rate exceeds 5% over 10 minutes",
        "runbook_url": "/docs/runbooks/quarantine-spikes",
    },
    "prompt_injection_attempts": {
        "condition": "rate(prompt_injection_attempts_total[1m]) > 0",
        "severity": "critical",
        "description": "Prompt injection attempts detected",
        "runbook_url": "/docs/runbooks/prompt-injection",
    },
    "llm_cost_spike": {
        "condition": "rate(llm_cost_usd_total[1h]) > 10.0",
        "severity": "warning",
        "description": "LLM cost exceeds $10/hour",
        "runbook_url": "/docs/runbooks/cost-monitoring",
    },
    "extraction_latency_p99": {
        "condition": "histogram_quantile(0.99, extraction_duration_seconds) > 300",
        "severity": "warning",
        "description": "P99 extraction latency exceeds 5 minutes",
        "runbook_url": "/docs/runbooks/latency-issues",
    },
    "tenant_isolation_breach": {
        "condition": "rate(tenant_context_missing_total[5m]) > 0",
        "severity": "critical",
        "description": "Tenant context missing in extraction operations",
        "runbook_url": "/docs/runbooks/tenant-isolation",
    },
}


def get_alert_rules() -> dict[str, dict[str, Any]]:
    """Get all alert rule definitions."""
    return ALERT_RULES.copy()


def get_alert_rule(rule_name: str) -> dict[str, Any] | None:
    """Get a specific alert rule by name."""
    return ALERT_RULES.get(rule_name)
