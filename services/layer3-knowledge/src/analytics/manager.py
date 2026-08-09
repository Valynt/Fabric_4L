"""Comprehensive API analytics and usage reporting system with business intelligence dashboards."""

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypedDict

import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field


class AnalyticsEventPayload(TypedDict):
    event_id: str
    timestamp: str
    event_type: str
    user_id: str | None
    api_key_id: str | None
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    request_size_bytes: int
    response_size_bytes: int
    user_agent: str | None
    ip_address: str | None
    request_id: str | None
    tags: dict[str, str]
    metadata: dict[str, Any]


class DashboardDataPayload(TypedDict):
    dashboard: dict[str, Any] | None
    data: dict[str, Any] | None
    generated_at: str | None


class MetricsSummaryPayload(TypedDict):
    total_requests: int
    total_errors: int
    success_rate: float
    avg_response_time: float
    throughput_rps: float
    unique_users: int
    unique_api_keys: int
    top_endpoints: list[dict[str, Any]]

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric types for analytics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    BOOLEAN = "boolean"


class AggregationType(str, Enum):
    """Aggregation types."""

    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    DISTINCT_COUNT = "distinct_count"
    PERCENTILE = "percentile"


class TimeGranularity(str, Enum):
    """Time granularity for analytics."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class DashboardType(str, Enum):
    """Dashboard types."""

    OVERVIEW = "overview"
    USAGE = "usage"
    PERFORMANCE = "performance"
    ERRORS = "errors"
    BUSINESS = "business"
    CUSTOM = "custom"


@dataclass
class AnalyticsEvent:
    """Analytics event data."""

    event_id: str
    timestamp: datetime
    event_type: str
    user_id: str | None
    api_key_id: str | None
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    request_size_bytes: int
    response_size_bytes: int
    user_agent: str | None
    ip_address: str | None
    request_id: str | None
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> AnalyticsEventPayload:
        """Convert to dictionary."""
        return AnalyticsEventPayload(
            event_id=self.event_id,
            timestamp=self.timestamp.isoformat(),
            event_type=self.event_type,
            user_id=self.user_id,
            api_key_id=self.api_key_id,
            endpoint=self.endpoint,
            method=self.method,
            status_code=self.status_code,
            response_time_ms=self.response_time_ms,
            request_size_bytes=self.request_size_bytes,
            response_size_bytes=self.response_size_bytes,
            user_agent=self.user_agent,
            ip_address=self.ip_address,
            request_id=self.request_id,
            tags=self.tags,
            metadata=self.metadata,
        )


class MetricDefinition(BaseModel):
    """Metric definition for analytics."""

    name: str = Field(..., description="Metric name")
    type: MetricType = Field(..., description="Metric type")
    description: str = Field(..., description="Metric description")
    unit: str = Field(default="", description="Metric unit")
    tags: dict[str, str] = Field(default_factory=dict, description="Metric tags")
    enabled: bool = Field(default=True, description="Whether metric is enabled")


class AnalyticsQuery(BaseModel):
    """Analytics query definition."""

    metric: str = Field(..., description="Metric name")
    aggregation: AggregationType = Field(..., description="Aggregation type")
    filters: dict[str, Any] = Field(default_factory=dict, description="Query filters")
    group_by: list[str] = Field(default_factory=list, description="Group by fields")
    time_range: dict[str, Any] = Field(..., description="Time range")
    granularity: TimeGranularity = Field(
        default=TimeGranularity.HOUR, description="Time granularity"
    )
    limit: int | None = Field(None, description="Result limit")
    offset: int | None = Field(None, description="Result offset")


class AnalyticsResult(BaseModel):
    """Analytics query result."""

    query: AnalyticsQuery = Field(..., description="Original query")
    data: list[dict[str, Any]] = Field(..., description="Query results")
    total_count: int = Field(..., description="Total result count")
    execution_time_ms: float = Field(..., description="Query execution time")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Result metadata"
    )


class DashboardConfig(BaseModel):
    """Dashboard configuration."""

    id: str = Field(..., description="Dashboard ID")
    name: str = Field(..., description="Dashboard name")
    type: DashboardType = Field(..., description="Dashboard type")
    description: str = Field(..., description="Dashboard description")
    widgets: list[dict[str, Any]] = Field(..., description="Dashboard widgets")
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Dashboard filters"
    )
    refresh_interval: int = Field(
        default=300, description="Refresh interval in seconds"
    )
    enabled: bool = Field(default=True, description="Whether dashboard is enabled")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Update timestamp"
    )


class AnalyticsConfig(BaseModel):
    """Analytics configuration."""

    enabled: bool = Field(default=True, description="Enable analytics")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    retention_days: int = Field(default=30, description="Data retention period in days")
    batch_size: int = Field(default=100, description="Batch size for processing")
    flush_interval: int = Field(default=60, description="Flush interval in seconds")
    max_events_per_second: int = Field(
        default=10000, description="Max events per second"
    )
    sampling_rate: float = Field(default=1.0, description="Event sampling rate")
    enable_real_time: bool = Field(
        default=True, description="Enable real-time analytics"
    )
    enable_historical: bool = Field(
        default=True, description="Enable historical analytics"
    )

    model_config = ConfigDict(use_enum_values=True)


class MetricsCollector:
    """Collects and aggregates metrics from events."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize metrics collector.

        Args:
            config: Analytics configuration
        """
        self.config = config
        self.metrics: dict[str, Any] = defaultdict(lambda: defaultdict(list))
        self.counters: dict[str, int] = defaultdict(int)
        self.gauges: dict[str, float] = defaultdict(float)
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.timers: dict[str, list[float]] = defaultdict(list)

        # Pre-defined metrics
        self.define_default_metrics()

    def define_default_metrics(self):
        """Define default analytics metrics."""
        default_metrics = [
            MetricDefinition(
                name="api_requests_total",
                type=MetricType.COUNTER,
                description="Total number of API requests",
            ),
            MetricDefinition(
                name="api_response_time_ms",
                type=MetricType.HISTOGRAM,
                description="API response time in milliseconds",
            ),
            MetricDefinition(
                name="api_errors_total",
                type=MetricType.COUNTER,
                description="Total number of API errors",
            ),
            MetricDefinition(
                name="api_throughput_rps",
                type=MetricType.GAUGE,
                description="API requests per second",
            ),
            MetricDefinition(
                name="api_success_rate",
                type=MetricType.GAUGE,
                description="API success rate percentage",
            ),
            MetricDefinition(
                name="unique_users_total",
                type=MetricType.GAUGE,
                description="Total number of unique users",
            ),
            MetricDefinition(
                name="unique_api_keys_total",
                type=MetricType.GAUGE,
                description="Total number of unique API keys",
            ),
            MetricDefinition(
                name="top_endpoints",
                type=MetricType.COUNTER,
                description="Most accessed endpoints",
            ),
            MetricDefinition(
                name="data_volume_bytes",
                type=MetricType.COUNTER,
                description="Total data volume in bytes",
            ),
        ]

        # Initialize default metrics
        for metric in default_metrics:
            if metric.type == MetricType.COUNTER:
                self.counters[metric.name] = 0
            elif metric.type == MetricType.GAUGE:
                self.gauges[metric.name] = 0.0

    def collect_event(self, event: AnalyticsEvent):
        """Collect analytics from event.

        Args:
            event: Analytics event
        """
        # Apply sampling
        if (
            self.config.sampling_rate < 1.0
            and hash(event.event_id) % 100 > self.config.sampling_rate * 100
        ):
            return

        # Basic metrics
        self.counters["api_requests_total"] += 1

        if event.status_code >= 400:
            self.counters["api_errors_total"] += 1

        # Response time metrics
        self.histograms["api_response_time_ms"].append(event.response_time_ms)

        # Data volume metrics
        self.counters["data_volume_bytes"] += (
            event.request_size_bytes + event.response_size_bytes
        )

        # Endpoint metrics
        endpoint_key = f"endpoint:{event.endpoint}"
        self.counters[endpoint_key] += 1

        # User metrics
        if event.user_id:
            user_key = f"user:{event.user_id}"
            self.counters[user_key] += 1

        # API key metrics
        if event.api_key_id:
            api_key_key = f"api_key:{event.api_key_id}"
            self.counters[api_key_key] += 1

        # Status code metrics
        status_key = f"status:{event.status_code}"
        self.counters[status_key] += 1

        # Method metrics
        method_key = f"method:{event.method}"
        self.counters[method_key] += 1

        # Store raw event for detailed analysis
        event_key = f"event:{event.event_id}"
        self.metrics[event_key]["raw"] = event.to_dict()

    def get_metric(
        self, metric_name: str, aggregation: AggregationType = AggregationType.SUM
    ) -> Any:
        """Get metric value with aggregation.

        Args:
            metric_name: Metric name
            aggregation: Aggregation type

        Returns:
            Aggregated metric value
        """
        if metric_name in self.counters:
            value = self.counters[metric_name]
            if aggregation == AggregationType.SUM:
                return value
            elif aggregation == AggregationType.AVERAGE:
                return value / max(1, self.counters["api_requests_total"])
            elif aggregation == AggregationType.COUNT:
                return 1 if value > 0 else 0
            else:
                return value

        elif metric_name in self.histograms:
            values = self.histograms[metric_name]
            if not values:
                return 0

            if aggregation == AggregationType.SUM:
                return sum(values)
            elif aggregation == AggregationType.AVERAGE:
                return sum(values) / len(values)
            elif aggregation == AggregationType.MIN:
                return min(values)
            elif aggregation == AggregationType.MAX:
                return max(values)
            elif aggregation == AggregationType.COUNT:
                return len(values)
            elif aggregation == AggregationType.PERCENTILE:
                # Return 95th percentile by default
                sorted_values = sorted(values)
                index = int(len(sorted_values) * 0.95)
                return sorted_values[min(index, len(sorted_values) - 1)]
            else:
                return values[0]

        elif metric_name in self.gauges:
            return self.gauges[metric_name]

        return None

    def get_top_metrics(self, pattern: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get top metrics by pattern.

        Args:
            pattern: Metric pattern (e.g., "endpoint:")
            limit: Number of results

        Returns:
            List of top metrics
        """
        matching_metrics = []

        for key, value in self.counters.items():
            if pattern in key:
                matching_metrics.append({"key": key, "value": value, "type": "counter"})

        # Sort by value descending
        matching_metrics.sort(key=lambda x: x["value"], reverse=True)

        return matching_metrics[:limit]

    def calculate_success_rate(self) -> float:
        """Calculate API success rate.

        Returns:
            Success rate percentage
        """
        total_requests = self.counters.get("api_requests_total", 0)
        total_errors = self.counters.get("api_errors_total", 0)

        if total_requests == 0:
            return 100.0

        return ((total_requests - total_errors) / total_requests) * 100

    def calculate_throughput(self, time_window_seconds: int = 60) -> float:
        """Calculate API throughput.

        Args:
            time_window_seconds: Time window in seconds

        Returns:
            Requests per second
        """
        # This is a simplified calculation
        # In production, this would use time-windowed counters
        total_requests = self.counters.get("api_requests_total", 0)

        if time_window_seconds <= 0:
            return 0.0

        return total_requests / time_window_seconds

    def get_unique_count(self, pattern: str) -> int:
        """Get unique count for pattern.

        Args:
            pattern: Pattern to count (e.g., "user:", "api_key:")

        Returns:
            Unique count
        """
        unique_values = set()

        for key in self.counters.keys():
            if pattern in key:
                value = key.split(":", 1)[1]  # Extract value after pattern
                unique_values.add(value)

        return len(unique_values)


class AnalyticsStore:
    """Analytics data storage backend."""

    def __init__(self, redis_url: str):
        """Initialize analytics store.

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
            logger.info("Connected to Redis for analytics")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def store_event(self, event: AnalyticsEvent, ttl: int = 86400):
        """Store analytics event.

        Args:
            event: Analytics event
            ttl: Time to live in seconds
        """
        if not self.redis_client:
            return

        try:
            # Store raw event
            event_key = f"analytics:event:{event.event_id}"
            await self.redis_client.setex(event_key, ttl, json.dumps(event.to_dict()))

            # Store time-series data
            timestamp = event.timestamp
            time_bucket = timestamp.replace(second=0, microsecond=0).isoformat()
            time_key = f"analytics:events:{time_bucket}"

            # Increment counters for time series
            await self.redis_client.hincrby(time_key, "total", 1)

            if event.status_code >= 400:
                await self.redis_client.hincrby(time_key, "errors", 1)

            await self.redis_client.hincrbyfloat(
                time_key, "response_time", event.response_time_ms
            )

            # Set expiration for time-series data
            await self.redis_client.expire(time_key, ttl)

        except Exception as e:
            logger.error(f"Failed to store event: {e}")

    async def get_time_series_data(
        self,
        metric: str,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity = TimeGranularity.HOUR,
    ) -> list[dict[str, Any]]:
        """Get time-series data for metric.

        Args:
            metric: Metric name
            start_time: Start time
            end_time: End time
            granularity: Time granularity

        Returns:
            Time-series data
        """
        if not self.redis_client:
            return []

        try:
            data = []
            current_time = start_time

            while current_time <= end_time:
                # Generate time bucket key
                if granularity == TimeGranularity.MINUTE:
                    time_bucket = current_time.replace(second=0, microsecond=0)
                elif granularity == TimeGranularity.HOUR:
                    time_bucket = current_time.replace(
                        minute=0, second=0, microsecond=0
                    )
                elif granularity == TimeGranularity.DAY:
                    time_bucket = current_time.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    time_bucket = current_time.replace(second=0, microsecond=0)

                time_key = f"analytics:events:{time_bucket.isoformat()}"

                # Get data for this time bucket
                time_data = await self.redis_client.hgetall(time_key)

                if time_data:
                    data_point = {
                        "timestamp": time_bucket.isoformat(),
                        "total": int(time_data.get("total", 0)),
                        "errors": int(time_data.get("errors", 0)),
                        "avg_response_time": float(time_data.get("response_time", 0))
                        / max(1, int(time_data.get("total", 1))),
                    }
                    data.append(data_point)

                # Move to next time bucket
                if granularity == TimeGranularity.MINUTE:
                    current_time += timedelta(minutes=1)
                elif granularity == TimeGranularity.HOUR:
                    current_time += timedelta(hours=1)
                elif granularity == TimeGranularity.DAY:
                    current_time += timedelta(days=1)
                else:
                    current_time += timedelta(hours=1)

            return data

        except Exception as e:
            logger.error(f"Failed to get time-series data: {e}")
            return []

    async def get_top_endpoints(
        self, start_time: datetime, end_time: datetime, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get top endpoints by request count.

        Args:
            start_time: Start time
            end_time: End time
            limit: Number of results

        Returns:
            Top endpoints data
        """
        if not self.redis_client:
            return []

        try:
            # This is a simplified implementation
            # In production, this would use Redis sorted sets or similar
            endpoints = {}

            # Scan time buckets
            current_time = start_time
            while current_time <= end_time:
                time_bucket = current_time.replace(minute=0, second=0, microsecond=0)
                f"analytics:events:{time_bucket.isoformat()}"

                # Get endpoint data
                pattern = "analytics:event:*"
                keys = await self.redis_client.keys(pattern)

                for key in keys[:100]:  # Limit to avoid too many keys
                    try:
                        event_data = await self.redis_client.get(key)
                        if event_data:
                            event = json.loads(event_data)
                            endpoint = event.get("endpoint")
                            if endpoint:
                                endpoints[endpoint] = endpoints.get(endpoint, 0) + 1
                    except Exception:
                        continue

                current_time += timedelta(hours=1)

            # Sort and return top results
            sorted_endpoints = sorted(
                endpoints.items(), key=lambda x: x[1], reverse=True
            )

            return [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in sorted_endpoints[:limit]
            ]

        except Exception as e:
            logger.error(f"Failed to get top endpoints: {e}")
            return []

    async def cleanup_old_data(self, retention_days: int):
        """Clean up old analytics data.

        Args:
            retention_days: Data retention period in days
        """
        if not self.redis_client:
            return

        try:
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old events
            pattern = "analytics:event:*"
            keys = await self.redis_client.keys(pattern)

            deleted_count = 0
            for key in keys:
                try:
                    # Check if event is older than retention period
                    event_data = await self.redis_client.get(key)
                    if event_data:
                        event = json.loads(event_data)
                        event_time = datetime.fromisoformat(event["timestamp"])

                        if event_time < cutoff_time:
                            await self.redis_client.delete(key)
                            deleted_count += 1
                except Exception:
                    continue

            # Delete old time-series data
            pattern = "analytics:events:*"
            keys = await self.redis_client.keys(pattern)

            for key in keys:
                try:
                    # Parse timestamp from key
                    timestamp_str = key.split(":")[-1]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < cutoff_time:
                        await self.redis_client.delete(key)
                        deleted_count += 1
                except Exception:
                    continue

            logger.info(f"Cleaned up {deleted_count} old analytics records")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


class AnalyticsManager:
    """Manages analytics collection, storage, and querying."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize analytics manager.

        Args:
            config: Analytics configuration
        """
        self.config = config
        self.store = AnalyticsStore(config.redis_url)
        self.collector = MetricsCollector(config)
        self.dashboards: dict[str, DashboardConfig] = {}
        self.query_cache: dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes

        # Initialize default dashboards
        self._setup_default_dashboards()

    def _setup_default_dashboards(self):
        """Setup default analytics dashboards."""
        # Overview dashboard
        self.dashboards["overview"] = DashboardConfig(
            id="overview",
            name="API Overview",
            type=DashboardType.OVERVIEW,
            description="High-level API metrics and health indicators",
            widgets=[
                {
                    "type": "metric",
                    "title": "Total Requests",
                    "metric": "api_requests_total",
                    "aggregation": "sum",
                    "time_range": {"hours": 24},
                },
                {
                    "type": "metric",
                    "title": "Success Rate",
                    "metric": "api_success_rate",
                    "aggregation": "average",
                    "time_range": {"hours": 24},
                },
                {
                    "type": "chart",
                    "title": "Response Time Trend",
                    "metric": "api_response_time_ms",
                    "aggregation": "average",
                    "time_range": {"hours": 24},
                    "chart_type": "line",
                },
            ],
        )

        # Usage dashboard
        self.dashboards["usage"] = DashboardConfig(
            id="usage",
            name="API Usage",
            type=DashboardType.USAGE,
            description="Detailed API usage statistics and trends",
            widgets=[
                {
                    "type": "table",
                    "title": "Top Endpoints",
                    "metric": "top_endpoints",
                    "time_range": {"hours": 24},
                    "limit": 10,
                },
                {
                    "type": "chart",
                    "title": "Requests by Hour",
                    "metric": "api_requests_total",
                    "aggregation": "sum",
                    "time_range": {"days": 7},
                    "chart_type": "bar",
                },
            ],
        )

    async def start(self):
        """Start analytics manager."""
        await self.store.connect()
        logger.info("Analytics manager started")

    async def stop(self):
        """Stop analytics manager."""
        await self.store.disconnect()
        logger.info("Analytics manager stopped")

    async def track_event(self, event: AnalyticsEvent):
        """Track analytics event.

        Args:
            event: Analytics event
        """
        if not self.config.enabled:
            return

        # Collect metrics
        self.collector.collect_event(event)

        # Store event
        await self.store.store_event(event)

    async def query_analytics(self, query: AnalyticsQuery) -> AnalyticsResult:
        """Execute analytics query.

        Args:
            query: Analytics query

        Returns:
            Query result
        """
        start_time = time.time()

        # Check cache
        cache_key = self._generate_cache_key(query)
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                return AnalyticsResult(
                    query=query,
                    data=cache_entry["data"],
                    total_count=len(cache_entry["data"]),
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"cached": True},
                )

        # Execute query
        data = await self._execute_query(query)

        # Cache result
        self.query_cache[cache_key] = {"data": data, "timestamp": time.time()}

        return AnalyticsResult(
            query=query,
            data=data,
            total_count=len(data),
            execution_time_ms=(time.time() - start_time) * 1000,
            metadata={"cached": False},
        )

    def _generate_cache_key(self, query: AnalyticsQuery) -> str:
        """Generate cache key for query.

        Args:
            query: Analytics query

        Returns:
            Cache key
        """
        key_parts = [
            query.metric,
            query.aggregation.value,
            str(query.time_range),
            query.granularity.value,
        ]

        if query.filters:
            key_parts.append(json.dumps(query.filters, sort_keys=True))

        if query.group_by:
            key_parts.append(",".join(query.group_by))

        return hashlib.md5(":".join(key_parts).encode(), usedforsecurity=False).hexdigest()

    async def _execute_query(self, query: AnalyticsQuery) -> list[dict[str, Any]]:
        """Execute analytics query.

        Args:
            query: Analytics query

        Returns:
            Query results
        """
        # Parse time range
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()

        if "hours" in query.time_range:
            start_time = end_time - timedelta(hours=query.time_range["hours"])
        elif "days" in query.time_range:
            start_time = end_time - timedelta(days=query.time_range["days"])
        elif "start" in query.time_range and "end" in query.time_range:
            start_time = datetime.fromisoformat(query.time_range["start"])
            end_time = datetime.fromisoformat(query.time_range["end"])

        # Execute query based on metric
        if query.metric == "api_requests_total":
            data = await self._get_requests_data(query, start_time, end_time)
        elif query.metric == "api_response_time_ms":
            data = await self._get_response_time_data(query, start_time, end_time)
        elif query.metric == "api_success_rate":
            data = await self._get_success_rate_data(query, start_time, end_time)
        elif query.metric == "top_endpoints":
            data = await self.store.get_top_endpoints(
                start_time, end_time, query.limit or 10
            )
        else:
            data = []

        return data

    async def _get_requests_data(
        self, query: AnalyticsQuery, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        """Get requests data.

        Args:
            query: Analytics query
            start_time: Start time
            end_time: End time

        Returns:
            Requests data
        """
        time_series_data = await self.store.get_time_series_data(
            "total", start_time, end_time, query.granularity
        )

        # Apply aggregation
        if (
            query.aggregation == AggregationType.SUM
            or query.aggregation == AggregationType.AVERAGE
        ):
            return time_series_data
        else:
            return time_series_data

    async def _get_response_time_data(
        self, query: AnalyticsQuery, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        """Get response time data.

        Args:
            query: Analytics query
            start_time: Start time
            end_time: End time

        Returns:
            Response time data
        """
        time_series_data = await self.store.get_time_series_data(
            "response_time", start_time, end_time, query.granularity
        )

        # Apply aggregation
        if query.aggregation == AggregationType.AVERAGE:
            return time_series_data
        elif query.aggregation == AggregationType.PERCENTILE:
            # Calculate percentiles
            for data_point in time_series_data:
                # This would need more sophisticated percentile calculation
                data_point["percentile_95"] = data_point.get("avg_response_time", 0)
            return time_series_data
        else:
            return time_series_data

    async def _get_success_rate_data(
        self, query: AnalyticsQuery, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        """Get success rate data.

        Args:
            query: Analytics query
            start_time: Start time
            end_time: End time

        Returns:
            Success rate data
        """
        time_series_data = await self.store.get_time_series_data(
            "total", start_time, end_time, query.granularity
        )

        # Calculate success rate for each time point
        for data_point in time_series_data:
            total = data_point.get("total", 0)
            errors = data_point.get("errors", 0)

            if total > 0:
                data_point["success_rate"] = ((total - errors) / total) * 100
            else:
                data_point["success_rate"] = 100.0

        return time_series_data

    async def get_dashboard(self, dashboard_id: str) -> DashboardConfig | None:
        """Get dashboard configuration.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            Dashboard configuration or None
        """
        return self.dashboards.get(dashboard_id)

    async def get_dashboard_data(self, dashboard_id: str) -> DashboardDataPayload:
        """Get dashboard data.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            Dashboard data
        """
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            return DashboardDataPayload(dashboard=None, data=None, generated_at=None)

        # Execute queries for all widgets
        widget_data = {}

        for i, widget in enumerate(dashboard.widgets):
            if widget["type"] == "metric" or widget["type"] == "chart":
                query = AnalyticsQuery(
                    metric=widget["metric"],
                    aggregation=AggregationType(widget["aggregation"]),
                    time_range=widget["time_range"],
                    granularity=TimeGranularity.HOUR,
                )
                result = await self.query_analytics(query)
                widget_data[f"widget_{i}"] = result.data
            elif widget["type"] == "table":
                if widget["metric"] == "top_endpoints":
                    time_range = widget["time_range"]
                    start_time = datetime.utcnow()
                    end_time = datetime.utcnow()

                    if "hours" in time_range:
                        start_time = end_time - timedelta(hours=time_range["hours"])

                    data = await self.store.get_top_endpoints(
                        start_time, end_time, widget.get("limit", 10)
                    )
                    widget_data[f"widget_{i}"] = data

        return DashboardDataPayload(
            dashboard=dashboard.dict(),
            data=widget_data,
            generated_at=datetime.utcnow().isoformat(),
        )


    async def get_metrics_summary(self) -> MetricsSummaryPayload:
        """Get metrics summary.

        Returns:
            Metrics summary
        """
        return MetricsSummaryPayload(
            total_requests=self.collector.counters.get("api_requests_total", 0),
            total_errors=self.collector.counters.get("api_errors_total", 0),
            success_rate=self.collector.calculate_success_rate(),
            throughput_rps=self.collector.calculate_throughput(),
            unique_users=self.collector.get_unique_count("user:"),
            unique_api_keys=self.collector.get_unique_count("api_key:"),
            avg_response_time=self.collector.get_metric(
                "api_response_time_ms", AggregationType.AVERAGE
            ),
            top_endpoints=self.collector.get_top_metrics("endpoint:", 10),
        )


    async def cleanup(self):
        """Cleanup old analytics data."""
        await self.store.cleanup_old_data(self.config.retention_days)

        # Clean up query cache
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self.query_cache.items()
            if current_time - entry["timestamp"] > self.cache_ttl
        ]

        for key in expired_keys:
            del self.query_cache[key]

        logger.info(f"Cleaned up {len(expired_keys)} cached queries")


# Global analytics manager instance
_analytics_manager: AnalyticsManager | None = None


def get_analytics_manager() -> AnalyticsManager | None:
    """Get global analytics manager instance.

    Returns:
        Analytics manager instance
    """
    return _analytics_manager


async def initialize_analytics(config: AnalyticsConfig) -> AnalyticsManager:
    """Initialize global analytics system.

    Args:
        config: Analytics configuration

    Returns:
        Analytics manager instance
    """
    global _analytics_manager
    _analytics_manager = AnalyticsManager(config)
    await _analytics_manager.start()
    logger.info("Analytics system initialized")
    return _analytics_manager
