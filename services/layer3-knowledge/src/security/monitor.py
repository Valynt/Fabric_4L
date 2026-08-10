"""Comprehensive API security monitoring and threat detection system with anomaly detection."""

import json
import logging
import re
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal, TypedDict

import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field


class SecurityEventPayload(TypedDict):
    event_id: str
    timestamp: str
    event_type: str
    source_ip: str
    user_id: str | None
    api_key_id: str | None
    endpoint: str
    method: str
    user_agent: str | None
    request_size: int
    response_size: int
    status_code: int
    response_time_ms: float
    request_headers: dict[str, str]
    request_body: str | None
    response_headers: dict[str, str]
    geo_location: dict[str, str] | None
    reputation_score: float
    risk_score: float
    tags: list[str]
    metadata: dict[str, Any]


class SecuritySummaryPayload(TypedDict):
    stats: dict[str, int]
    alert_levels: dict[Literal["low", "medium", "high", "critical"], int]
    recent_alerts: int
    blocked_ips: int
    blocked_users: int
    active_signatures: int

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats."""

    BRUTE_FORCE = "brute_force"
    INJECTION = "injection"
    XSS = "xss"
    CSRF = "csrf"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALICIOUS_PAYLOAD = "malicious_payload"
    RECONNAISSANCE = "reconnaissance"


class DetectionMethod(str, Enum):
    """Threat detection methods."""

    SIGNATURE_BASED = "signature_based"
    ANOMALY_DETECTION = "anomaly_detection"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    PATTERN_MATCHING = "pattern_matching"
    THRESHOLD_BASED = "threshold_based"
    MACHINE_LEARNING = "machine_learning"


class AlertStatus(str, Enum):
    """Security alert status."""

    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


@dataclass
class SecurityEvent:
    """Security event data."""

    event_id: str
    timestamp: datetime
    event_type: str
    source_ip: str
    user_id: str | None
    api_key_id: str | None
    endpoint: str
    method: str
    user_agent: str | None
    request_size: int
    response_size: int
    status_code: int
    response_time_ms: float
    request_headers: dict[str, str]
    request_body: str | None
    response_headers: dict[str, str]
    geo_location: dict[str, str] | None = None
    reputation_score: float = 0.0
    risk_score: float = 0.0
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> SecurityEventPayload:
        """Convert to dictionary."""
        return SecurityEventPayload(
            event_id=self.event_id,
            timestamp=self.timestamp.isoformat(),
            event_type=self.event_type,
            source_ip=self.source_ip,
            user_id=self.user_id,
            api_key_id=self.api_key_id,
            endpoint=self.endpoint,
            method=self.method,
            user_agent=self.user_agent,
            request_size=self.request_size,
            response_size=self.response_size,
            status_code=self.status_code,
            response_time_ms=self.response_time_ms,
            request_headers=self.request_headers,
            request_body=self.request_body,
            response_headers=self.response_headers,
            geo_location=self.geo_location,
            reputation_score=self.reputation_score,
            risk_score=self.risk_score,
            tags=list(self.tags),
            metadata=self.metadata,
        )


class ThreatSignature(BaseModel):
    """Threat detection signature."""

    id: str = Field(..., description="Signature ID")
    name: str = Field(..., description="Signature name")
    type: ThreatType = Field(..., description="Threat type")
    pattern: str = Field(..., description="Detection pattern")
    method: DetectionMethod = Field(..., description="Detection method")
    severity: ThreatLevel = Field(..., description="Threat severity")
    description: str = Field(..., description="Signature description")
    enabled: bool = Field(default=True, description="Whether signature is enabled")
    conditions: dict[str, Any] = Field(
        default_factory=dict, description="Additional conditions"
    )
    false_positive_rate: float = Field(default=0.0, description="False positive rate")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Update timestamp"
    )


class SecurityAlert(BaseModel):
    """Security alert."""

    alert_id: str = Field(..., description="Alert ID")
    event_id: str = Field(..., description="Related event ID")
    threat_type: ThreatType = Field(..., description="Threat type")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    source_ip: str = Field(..., description="Source IP")
    user_id: str | None = Field(None, description="User ID")
    api_key_id: str | None = Field(None, description="API key ID")
    endpoint: str = Field(..., description="Target endpoint")
    signature_id: str | None = Field(None, description="Detection signature ID")
    confidence: float = Field(..., description="Detection confidence (0.0-1.0)")
    risk_score: float = Field(..., description="Risk score (0.0-1.0)")
    status: AlertStatus = Field(default=AlertStatus.NEW, description="Alert status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Update timestamp"
    )
    resolved_at: datetime | None = Field(None, description="Resolution timestamp")
    assigned_to: str | None = Field(None, description="Assigned analyst")
    notes: list[str] = Field(default_factory=list, description="Investigation notes")
    tags: list[str] = Field(default_factory=list, description="Alert tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SecurityConfig(BaseModel):
    """Security monitoring configuration."""

    enabled: bool = Field(default=True, description="Enable security monitoring")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    retention_days: int = Field(default=30, description="Data retention period")
    alert_threshold: float = Field(default=0.7, description="Alert threshold")
    anomaly_threshold: float = Field(
        default=2.0, description="Anomaly detection threshold (std deviations)"
    )
    max_events_per_second: int = Field(
        default=1000, description="Max events per second"
    )
    geo_ip_enabled: bool = Field(default=True, description="Enable GeoIP lookup")
    reputation_enabled: bool = Field(
        default=True, description="Enable IP reputation lookup"
    )
    ml_enabled: bool = Field(default=False, description="Enable ML-based detection")
    auto_block_enabled: bool = Field(
        default=False, description="Enable automatic blocking"
    )

    model_config = ConfigDict(use_enum_values=True)


class AnomalyDetector:
    """Detects anomalous patterns in security events."""

    def __init__(self, config: SecurityConfig):
        """Initialize anomaly detector.

        Args:
            config: Security configuration
        """
        self.config = config
        self.baseline_metrics: dict[str, float] = {}
        self.recent_events: deque = deque(maxlen=1000)
        self.user_patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.ip_patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.endpoint_patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: defaultdict(list)
        )

    def add_event(self, event: SecurityEvent):
        """Add event for anomaly detection.

        Args:
            event: Security event
        """
        self.recent_events.append(event)

        # Update user patterns
        if event.user_id:
            self.user_patterns[event.user_id]["endpoints"].append(event.endpoint)
            self.user_patterns[event.user_id]["methods"].append(event.method)
            self.user_patterns[event.user_id]["response_times"].append(
                event.response_time_ms
            )
            self.user_patterns[event.user_id]["request_sizes"].append(
                event.request_size
            )

        # Update IP patterns
        self.ip_patterns[event.source_ip]["endpoints"].append(event.endpoint)
        self.ip_patterns[event.source_ip]["methods"].append(event.method)
        self.ip_patterns[event.source_ip]["response_times"].append(
            event.response_time_ms
        )
        self.ip_patterns[event.source_ip]["request_sizes"].append(event.request_size)

        # Update endpoint patterns
        self.endpoint_patterns[event.endpoint]["ips"].append(event.source_ip)
        self.endpoint_patterns[event.endpoint]["methods"].append(event.method)
        self.endpoint_patterns[event.endpoint]["response_times"].append(
            event.response_time_ms
        )

    def detect_anomalies(self, event: SecurityEvent) -> list[dict[str, Any]]:
        """Detect anomalies in event.

        Args:
            event: Security event to analyze

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Detect response time anomalies
        if event.response_time_ms > 0:
            avg_response_time = self._calculate_average_response_time(event.endpoint)
            if avg_response_time > 0:
                std_dev = self._calculate_response_time_std_dev(event.endpoint)
                if std_dev > 0:
                    z_score = (event.response_time_ms - avg_response_time) / std_dev
                    if abs(z_score) > self.config.anomaly_threshold:
                        anomalies.append(
                            {
                                "type": "response_time_anomaly",
                                "severity": "high" if abs(z_score) > 3.0 else "medium",
                                "z_score": z_score,
                                "description": f"Response time {z_score:.2f} std deviations from normal",
                            }
                        )

        # Detect request size anomalies
        if event.request_size > 0:
            avg_request_size = self._calculate_average_request_size(event.endpoint)
            if avg_request_size > 0:
                std_dev = self._calculate_request_size_std_dev(event.endpoint)
                if std_dev > 0:
                    z_score = (event.request_size - avg_request_size) / std_dev
                    if abs(z_score) > self.config.anomaly_threshold:
                        anomalies.append(
                            {
                                "type": "request_size_anomaly",
                                "severity": "medium",
                                "z_score": z_score,
                                "description": f"Request size {z_score:.2f} std deviations from normal",
                            }
                        )

        # Detect frequency anomalies
        if event.user_id:
            recent_user_events = [
                e for e in self.recent_events if e.user_id == event.user_id
            ]
            if len(recent_user_events) > 10:
                events_per_minute = len(recent_user_events) / 10  # Last 10 minutes
                if events_per_minute > 100:  # More than 100 requests per minute
                    anomalies.append(
                        {
                            "type": "frequency_anomaly",
                            "severity": "high",
                            "events_per_minute": events_per_minute,
                            "description": f"Unusually high request frequency: {events_per_minute:.1f} req/min",
                        }
                    )

        # Detect endpoint access anomalies
        if event.endpoint:
            recent_endpoint_events = [
                e for e in self.recent_events if e.endpoint == event.endpoint
            ]
            unique_ips = set(e.source_ip for e in recent_endpoint_events)
            if (
                len(unique_ips) > len(recent_endpoint_events) * 0.8
            ):  # Most requests from different IPs
                anomalies.append(
                    {
                        "type": "endpoint_anomaly",
                        "severity": "medium",
                        "unique_ips": len(unique_ips),
                        "total_requests": len(recent_endpoint_events),
                        "description": f"Unusual access pattern from {len(unique_ips)} unique IPs",
                    }
                )

        return anomalies

    def _calculate_average_response_time(self, endpoint: str) -> float:
        """Calculate average response time for endpoint.

        Args:
            endpoint: Endpoint name

        Returns:
            Average response time
        """
        response_times = self.endpoint_patterns[endpoint]["response_times"]
        return sum(response_times) / len(response_times) if response_times else 0.0

    def _calculate_response_time_std_dev(self, endpoint: str) -> float:
        """Calculate response time standard deviation.

        Args:
            endpoint: Endpoint name

        Returns:
            Standard deviation
        """
        response_times = self.endpoint_patterns[endpoint]["response_times"]
        if len(response_times) < 2:
            return 0.0

        avg = sum(response_times) / len(response_times)
        variance = sum((rt - avg) ** 2 for rt in response_times) / len(response_times)
        return variance**0.5

    def _calculate_average_request_size(self, endpoint: str) -> float:
        """Calculate average request size for endpoint.

        Args:
            endpoint: Endpoint name

        Returns:
            Average request size
        """
        request_sizes = self.endpoint_patterns[endpoint]["request_sizes"]
        return sum(request_sizes) / len(request_sizes) if request_sizes else 0.0

    def _calculate_request_size_std_dev(self, endpoint: str) -> float:
        """Calculate request size standard deviation.

        Args:
            endpoint: Endpoint name

        Returns:
            Standard deviation
        """
        request_sizes = self.endpoint_patterns[endpoint]["request_sizes"]
        if len(request_sizes) < 2:
            return 0.0

        avg = sum(request_sizes) / len(request_sizes)
        variance = sum((rs - avg) ** 2 for rs in request_sizes) / len(request_sizes)
        return variance**0.5


class SignatureMatcher:
    """Matches events against threat signatures."""

    def __init__(self):
        """Initialize signature matcher."""
        self.signatures: dict[str, ThreatSignature] = {}
        self._load_default_signatures()

    def _load_default_signatures(self):
        """Load default threat signatures."""
        default_signatures = [
            ThreatSignature(
                id="sql_injection_1",
                name="SQL Injection Pattern",
                type=ThreatType.INJECTION,
                pattern=r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|script)",
                method=DetectionMethod.PATTERN_MATCHING,
                severity=ThreatLevel.HIGH,
                description="Detects potential SQL injection attacks",
            ),
            ThreatSignature(
                id="xss_1",
                name="XSS Pattern",
                type=ThreatType.XSS,
                pattern=r"(?i)(<script|javascript:|onload|onerror|onclick)",
                method=DetectionMethod.PATTERN_MATCHING,
                severity=ThreatLevel.MEDIUM,
                description="Detects potential XSS attacks",
            ),
            ThreatSignature(
                id="brute_force_1",
                name="Brute Force Login",
                type=ThreatType.BRUTE_FORCE,
                pattern=r"",
                method=DetectionMethod.THRESHOLD_BASED,
                severity=ThreatLevel.HIGH,
                description="Detects brute force login attempts",
                conditions={
                    "endpoint": "/auth/login",
                    "max_attempts": 10,
                    "time_window": 300,
                },
            ),
            ThreatSignature(
                id="suspicious_user_agent_1",
                name="Suspicious User Agent",
                type=ThreatType.SUSPICIOUS_PATTERN,
                pattern=r"(?i)(bot|crawler|scanner|exploit)",
                method=DetectionMethod.PATTERN_MATCHING,
                severity=ThreatLevel.LOW,
                description="Detects suspicious user agents",
            ),
            ThreatSignature(
                id="large_request_1",
                name="Large Request Size",
                type=ThreatType.DATA_EXFILTRATION,
                pattern=r"",
                method=DetectionMethod.THRESHOLD_BASED,
                severity=ThreatLevel.MEDIUM,
                description="Detects unusually large requests",
                conditions={"max_size": 10485760},  # 10MB
            ),
        ]

        for signature in default_signatures:
            self.signatures[signature.id] = signature

    def add_signature(self, signature: ThreatSignature):
        """Add threat signature.

        Args:
            signature: Threat signature to add
        """
        self.signatures[signature.id] = signature
        logger.info(f"Added threat signature: {signature.name}")

    def remove_signature(self, signature_id: str) -> bool:
        """Remove threat signature.

        Args:
            signature_id: Signature ID to remove

        Returns:
            True if removed
        """
        if signature_id in self.signatures:
            del self.signatures[signature_id]
            logger.info(f"Removed threat signature: {signature_id}")
            return True
        return False

    def match_event(self, event: SecurityEvent) -> list[ThreatSignature]:
        """Match event against threat signatures.

        Args:
            event: Security event to match

        Returns:
            List of matching signatures
        """
        matches = []

        for signature in self.signatures.values():
            if not signature.enabled:
                continue

            if self._matches_signature(event, signature):
                matches.append(signature)

        return matches

    def _matches_signature(
        self, event: SecurityEvent, signature: ThreatSignature
    ) -> bool:
        """Check if event matches signature.

        Args:
            event: Security event
            signature: Threat signature

        Returns:
            True if matches
        """
        if signature.method == DetectionMethod.PATTERN_MATCHING:
            return self._pattern_match(event, signature)
        elif signature.method == DetectionMethod.THRESHOLD_BASED:
            return self._threshold_match(event, signature)
        elif signature.method == DetectionMethod.SIGNATURE_BASED:
            return self._signature_match(event, signature)

        return False

    def _pattern_match(self, event: SecurityEvent, signature: ThreatSignature) -> bool:
        """Pattern-based matching.

        Args:
            event: Security event
            signature: Threat signature

        Returns:
            True if matches
        """
        pattern = signature.pattern

        # Check in request body
        if event.request_body and re.search(pattern, event.request_body):
            return True

        # Check in headers
        for header_name, header_value in event.request_headers.items():
            if re.search(pattern, header_value):
                return True

        # Check in query parameters (if available)
        if event.metadata.get("query_params"):
            for param_value in event.metadata["query_params"].values():
                if re.search(pattern, str(param_value)):
                    return True

        return False

    def _threshold_match(
        self, event: SecurityEvent, signature: ThreatSignature
    ) -> bool:
        """Threshold-based matching.

        Args:
            event: Security event
            signature: Threat signature

        Returns:
            True if matches
        """
        conditions = signature.conditions

        # Check request size threshold
        if "max_size" in conditions and event.request_size > conditions["max_size"]:
            return True

        # Check response size threshold
        if (
            "max_response_size" in conditions
            and event.response_size > conditions["max_response_size"]
        ):
            return True

        # Check response time threshold
        if (
            "max_response_time" in conditions
            and event.response_time_ms > conditions["max_response_time"]
        ):
            return True

        return False

    def _signature_match(
        self, event: SecurityEvent, signature: ThreatSignature
    ) -> bool:
        """Signature-based matching.

        Args:
            event: Security event
            signature: Threat signature

        Returns:
            True if matches
        """
        # This would implement more complex signature matching
        # For now, delegate to pattern matching
        return self._pattern_match(event, signature)


class SecurityStore:
    """Security data storage backend."""

    def __init__(self, redis_url: str):
        """Initialize security store.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis for security monitoring")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def store_event(self, event: SecurityEvent, ttl: int = 86400):
        """Store security event.

        Args:
            event: Security event
            ttl: Time to live in seconds
        """
        if not self.redis_client:
            return

        try:
            # Store raw event
            event_key = f"security:event:{event.event_id}"
            await self.redis_client.setex(event_key, ttl, json.dumps(event.to_dict()))

            # Store by IP
            ip_key = f"security:ip:{event.source_ip}"
            await self.redis_client.lpush(ip_key, event.event_id)
            await self.redis_client.expire(ip_key, ttl)

            # Store by user
            if event.user_id:
                user_key = f"security:user:{event.user_id}"
                await self.redis_client.lpush(user_key, event.event_id)
                await self.redis_client.expire(user_key, ttl)

            # Store by endpoint
            endpoint_key = f"security:endpoint:{event.endpoint}"
            await self.redis_client.lpush(endpoint_key, event.event_id)
            await self.redis_client.expire(endpoint_key, ttl)

        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

    async def store_alert(self, alert: SecurityAlert, ttl: int = 2592000):  # 30 days
        """Store security alert.

        Args:
            alert: Security alert
            ttl: Time to live in seconds
        """
        if not self.redis_client:
            return

        try:
            alert_key = f"security:alert:{alert.alert_id}"
            await self.redis_client.setex(alert_key, ttl, alert.json())

            # Store by status
            status_key = f"security:alerts:{alert.status.value}"
            await self.redis_client.lpush(status_key, alert.alert_id)
            await self.redis_client.expire(status_key, ttl)

            # Store by threat level
            level_key = f"security:alerts:{alert.threat_level.value}"
            await self.redis_client.lpush(level_key, alert.alert_id)
            await self.redis_client.expire(level_key, ttl)

        except Exception as e:
            logger.error(f"Failed to store security alert: {e}")

    async def get_events_by_ip(self, ip: str, limit: int = 100) -> list[SecurityEvent]:
        """Get events by IP address.

        Args:
            ip: IP address
            limit: Maximum number of events

        Returns:
            List of security events
        """
        if not self.redis_client:
            return []

        try:
            ip_key = f"security:ip:{ip}"
            event_ids = await self.redis_client.lrange(ip_key, 0, limit - 1)

            events = []
            for event_id in event_ids:
                event_key = f"security:event:{event_id.decode() if isinstance(event_id, bytes) else event_id}"
                event_data = await self.redis_client.get(event_key)
                if event_data:
                    event_dict = json.loads(event_data)
                    events.append(SecurityEvent(**event_dict))

            return events

        except Exception as e:
            logger.error(f"Failed to get events by IP: {e}")
            return []

    async def get_alerts_by_status(
        self, status: AlertStatus, limit: int = 100
    ) -> list[SecurityAlert]:
        """Get alerts by status.

        Args:
            status: Alert status
            limit: Maximum number of alerts

        Returns:
            List of security alerts
        """
        if not self.redis_client:
            return []

        try:
            status_key = f"security:alerts:{status.value}"
            alert_ids = await self.redis_client.lrange(status_key, 0, limit - 1)

            alerts = []
            for alert_id in alert_ids:
                alert_key = f"security:alert:{alert_id.decode() if isinstance(alert_id, bytes) else alert_id}"
                alert_data = await self.redis_client.get(alert_key)
                if alert_data:
                    alerts.append(SecurityAlert.parse_raw(alert_data))

            return alerts

        except Exception as e:
            logger.error(f"Failed to get alerts by status: {e}")
            return []

    async def cleanup_old_data(self, retention_days: int):
        """Clean up old security data.

        Args:
            retention_days: Data retention period in days
        """
        if not self.redis_client:
            return

        try:
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)

            # Clean up old events
            pattern = "security:event:*"
            keys = await self.redis_client.keys(pattern)

            deleted_count = 0
            for key in keys:
                try:
                    event_data = await self.redis_client.get(key)
                    if event_data:
                        event_dict = json.loads(event_data)
                        event_time = datetime.fromisoformat(event_dict["timestamp"])

                        if event_time < cutoff_time:
                            await self.redis_client.delete(key)
                            deleted_count += 1
                except Exception:
                    continue

            logger.info(f"Cleaned up {deleted_count} old security records")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


class SecurityMonitor:
    """Main security monitoring system."""

    def __init__(self, config: SecurityConfig):
        """Initialize security monitor.

        Args:
            config: Security configuration
        """
        self.config = config
        self.store = SecurityStore(config.redis_url)
        self.anomaly_detector = AnomalyDetector(config)
        self.signature_matcher = SignatureMatcher()
        self.alert_callbacks: list[Callable[[SecurityAlert], None]] = []
        self.blocked_ips: set[str] = set()
        self.blocked_users: set[str] = set()

        # Statistics
        self.stats = {
            "events_processed": 0,
            "alerts_generated": 0,
            "threats_blocked": 0,
            "false_positives": 0,
        }

    async def start(self):
        """Start security monitor."""
        await self.store.connect()
        logger.info("Security monitor started")

    async def stop(self):
        """Stop security monitor."""
        await self.store.disconnect()
        logger.info("Security monitor stopped")

    def add_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Add alert callback.

        Args:
            callback: Alert callback function
        """
        self.alert_callbacks.append(callback)

    async def process_event(self, event: SecurityEvent) -> list[SecurityAlert]:
        """Process security event and generate alerts.

        Args:
            event: Security event

        Returns:
            List of generated alerts
        """
        if not self.config.enabled:
            return []

        self.stats["events_processed"] += 1

        # Store event
        await self.store.store_event(event)

        # Add to anomaly detector
        self.anomaly_detector.add_event(event)

        alerts = []

        # Check for blocked entities
        if self._is_blocked(event):
            alerts.append(self._create_block_alert(event))

        # Signature-based detection
        matching_signatures = self.signature_matcher.match_event(event)
        for signature in matching_signatures:
            alert = self._create_signature_alert(event, signature)
            alerts.append(alert)

        # Anomaly detection
        anomalies = self.anomaly_detector.detect_anomalies(event)
        for anomaly in anomalies:
            alert = self._create_anomaly_alert(event, anomaly)
            alerts.append(alert)

        # Store and process alerts
        for alert in alerts:
            await self.store.store_alert(alert)
            self.stats["alerts_generated"] += 1

            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

            # Auto-block if enabled
            if self.config.auto_block_enabled and alert.threat_level in [
                ThreatLevel.HIGH,
                ThreatLevel.CRITICAL,
            ]:
                await self._auto_block(alert)

        return alerts

    def _is_blocked(self, event: SecurityEvent) -> bool:
        """Check if event source is blocked.

        Args:
            event: Security event

        Returns:
            True if blocked
        """
        return event.source_ip in self.blocked_ips or (
            event.user_id and event.user_id in self.blocked_users
        )

    def _create_block_alert(self, event: SecurityEvent) -> SecurityAlert:
        """Create alert for blocked entity.

        Args:
            event: Security event

        Returns:
            Security alert
        """
        return SecurityAlert(
            alert_id=str(uuid.uuid4()),
            event_id=event.event_id,
            threat_type=ThreatType.UNAUTHORIZED_ACCESS,
            threat_level=ThreatLevel.HIGH,
            title="Blocked Entity Access Attempt",
            description=f"Access attempt from blocked entity: {event.source_ip}",
            source_ip=event.source_ip,
            user_id=event.user_id,
            api_key_id=event.api_key_id,
            endpoint=event.endpoint,
            confidence=1.0,
            risk_score=0.9,
            metadata={"block_type": "existing_block"},
        )

    def _create_signature_alert(
        self, event: SecurityEvent, signature: ThreatSignature
    ) -> SecurityAlert:
        """Create alert for signature match.

        Args:
            event: Security event
            signature: Matching signature

        Returns:
            Security alert
        """
        return SecurityAlert(
            alert_id=str(uuid.uuid4()),
            event_id=event.event_id,
            threat_type=signature.type,
            threat_level=signature.severity,
            title=f"Threat Detected: {signature.name}",
            description=signature.description,
            source_ip=event.source_ip,
            user_id=event.user_id,
            api_key_id=event.api_key_id,
            endpoint=event.endpoint,
            signature_id=signature.id,
            confidence=1.0 - signature.false_positive_rate,
            risk_score=self._calculate_risk_score(
                signature.severity, signature.false_positive_rate
            ),
            metadata={"signature_name": signature.name},
        )

    def _create_anomaly_alert(
        self, event: SecurityEvent, anomaly: dict[str, Any]
    ) -> SecurityAlert:
        """Create alert for anomaly detection.

        Args:
            event: Security event
            anomaly: Anomaly information

        Returns:
            Security alert
        """
        threat_level = ThreatLevel(anomaly.get("severity", "medium"))

        return SecurityAlert(
            alert_id=str(uuid.uuid4()),
            event_id=event.event_id,
            threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
            threat_level=threat_level,
            title=f"Anomaly Detected: {anomaly['type'].replace('_', ' ').title()}",
            description=anomaly.get("description", "Anomalous behavior detected"),
            source_ip=event.source_ip,
            user_id=event.user_id,
            api_key_id=event.api_key_id,
            endpoint=event.endpoint,
            confidence=0.8,
            risk_score=self._calculate_risk_score(threat_level, 0.2),
            metadata=anomaly,
        )

    def _calculate_risk_score(
        self, threat_level: ThreatLevel, false_positive_rate: float
    ) -> float:
        """Calculate risk score.

        Args:
            threat_level: Threat severity level
            false_positive_rate: False positive rate

        Returns:
            Risk score (0.0-1.0)
        """
        level_scores = {
            ThreatLevel.LOW: 0.2,
            ThreatLevel.MEDIUM: 0.5,
            ThreatLevel.HIGH: 0.8,
            ThreatLevel.CRITICAL: 1.0,
        }

        base_score = level_scores.get(threat_level, 0.5)
        adjusted_score = base_score * (1.0 - false_positive_rate)

        return min(1.0, max(0.0, adjusted_score))

    async def _auto_block(self, alert: SecurityAlert):
        """Automatically block threat source.

        Args:
            alert: Security alert
        """
        if alert.source_ip:
            self.blocked_ips.add(alert.source_ip)
            logger.warning(f"Auto-blocked IP: {alert.source_ip}")

        if alert.user_id:
            self.blocked_users.add(alert.user_id)
            logger.warning(f"Auto-blocked user: {alert.user_id}")

        self.stats["threats_blocked"] += 1

    async def get_security_summary(self) -> SecuritySummaryPayload:
        """Get security monitoring summary.

        Returns:
            Security summary
        """
        recent_alerts = await self.store.get_alerts_by_status(AlertStatus.NEW, limit=10)

        return SecuritySummaryPayload(
            stats=self.stats,
            blocked_ips=len(self.blocked_ips),
            blocked_users=len(self.blocked_users),
            active_signatures=len(
                [s for s in self.signature_matcher.signatures.values() if s.enabled]
            ),
            recent_alerts=len(recent_alerts),
            alert_levels={
                "low": len(
                    [a for a in recent_alerts if a.threat_level == ThreatLevel.LOW]
                ),
                "medium": len(
                    [a for a in recent_alerts if a.threat_level == ThreatLevel.MEDIUM]
                ),
                "high": len(
                    [a for a in recent_alerts if a.threat_level == ThreatLevel.HIGH]
                ),
                "critical": len(
                    [a for a in recent_alerts if a.threat_level == ThreatLevel.CRITICAL]
                ),
            },
        )


    async def cleanup(self):
        """Cleanup old security data."""
        await self.store.cleanup_old_data(self.config.retention_days)
        logger.info("Security cleanup completed")


# Global security monitor instance
_security_monitor: SecurityMonitor | None = None


def get_security_monitor() -> SecurityMonitor | None:
    """Get global security monitor instance.

    Returns:
        Security monitor instance
    """
    return _security_monitor


async def initialize_security_monitoring(config: SecurityConfig) -> SecurityMonitor:
    """Initialize global security monitoring system.

    Args:
        config: Security configuration

    Returns:
        Security monitor instance
    """
    global _security_monitor
    _security_monitor = SecurityMonitor(config)
    await _security_monitor.start()
    logger.info("Security monitoring system initialized")
    return _security_monitor
