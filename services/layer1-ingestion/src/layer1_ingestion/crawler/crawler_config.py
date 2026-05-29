"""Configuration management for PlaywrightCrawler.

Provides CrawlerConfig dataclass with validation and YAML config file support,
bridging the skill framework's config validation approach with production code.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from value_fabric.shared.models.typed_dict import TypedDictModel


class CrawlerConfig_viewportResult(TypedDictModel):
    height: Any
    width: Any


@dataclass
class CrawlerConfig:
    """Configuration for PlaywrightCrawler with validation.

    Supports loading from YAML config files similar to playwright.config.ts
    validation in the skill framework.
    """

    # Concurrency settings
    max_concurrent: int = 5
    timeout_ms: int = 30000
    navigation_timeout_ms: int = 10000

    # Browser settings
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
        "ValueFabricBot/1.0"
    )
    viewport_width: int = 1920
    viewport_height: int = 1080
    headless: bool = True

    # Security settings
    browser_args: list[str] = field(
        default_factory=lambda: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
        ]
    )

    # Resource blocking patterns
    blocked_resource_patterns: list[str] = field(
        default_factory=lambda: [
            "**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}",
        ]
    )

    # Scroll settings
    scroll_enabled: bool = True
    scroll_distance: int = 300
    scroll_interval_ms: int = 100
    scroll_delay_after_ms: int = 500

    # Rate limiting
    per_domain_delay_seconds: float = 1.0
    jitter_percent: float = 20.0

    # Observability
    enable_tracing: bool = True
    trace_attributes: dict = field(
        default_factory=lambda: {
            "service.name": "layer1-crawler",
            "service.version": "1.0.0",
        }
    )

    # Metrics
    emit_metrics: bool = True

    @classmethod
    def from_yaml(cls, path: Path | str) -> "CrawlerConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML config file

        Returns:
            CrawlerConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config contains invalid values
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a YAML object, got: {type(data).__name__}")

        # Validate numeric ranges
        if (mc := data.get("max_concurrent")) is not None:
            if not isinstance(mc, int) or mc < 1 or mc > 50:
                raise ValueError(f"max_concurrent must be between 1 and 50, got: {mc}")

        if (timeout := data.get("timeout_ms")) is not None:
            if not isinstance(timeout, int) or timeout < 1000:
                raise ValueError(f"timeout_ms must be at least 1000, got: {timeout}")

        # Filter unknown fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        if unknown := (set(data.keys()) - known_fields):
            import structlog

            logger = structlog.get_logger()
            logger.warning("Unknown config fields ignored", fields=list(unknown))

        return cls(**filtered_data)

    def to_yaml(self, path: Path | str) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to write config file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False, sort_keys=True)

    @property
    def viewport(self) -> dict:
        """Get viewport configuration as dict for Playwright."""
        return CrawlerConfig_viewportResult.model_validate({"width": self.viewport_width, "height": self.viewport_height}).model_dump()


def load_config(path: Path | str | None = None) -> CrawlerConfig:
    """Load crawler configuration from file or return defaults.

    Args:
        path: Optional path to YAML config. If None, checks common locations.

    Returns:
        CrawlerConfig instance
    """
    if path:
        return CrawlerConfig.from_yaml(path)

    # Check common config locations
    search_paths = [
        Path("crawler.config.yml"),
        Path("config/crawler.yml"),
        Path.home() / ".config/value-fabric/crawler.yml",
    ]

    for config_path in search_paths:
        if config_path.exists():
            return CrawlerConfig.from_yaml(config_path)

    return CrawlerConfig()
