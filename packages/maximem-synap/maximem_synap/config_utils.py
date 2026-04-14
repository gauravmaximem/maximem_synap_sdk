"""SDK configuration and utilities."""

import logging
from pathlib import Path
from typing import Any, Dict

from .models.config import SDKConfig, TimeoutConfig, RetryPolicy


logger = logging.getLogger("synap.sdk")


def configure_logging(log_level: str) -> None:
    """Configure SDK logging."""
    level = getattr(logging, log_level.upper(), logging.WARNING)
    logging.getLogger("synap.sdk").setLevel(level)


def get_default_storage_path() -> Path:
    """Get default storage path (~/.synap/)."""
    return Path.home() / ".synap"


def merge_config(base: SDKConfig, overrides: Dict[str, Any]) -> SDKConfig:
    """Merge configuration overrides into base config.
    
    Args:
        base: Base SDKConfig to start from
        overrides: Dict of config values to override
        
    Returns:
        New SDKConfig with merged values
    """
    data = base.model_dump()

    for key, value in overrides.items():
        if key == "timeouts" and isinstance(value, dict):
            # Merge timeout config
            existing_timeouts = data.get("timeouts", {})
            if isinstance(existing_timeouts, TimeoutConfig):
                existing_timeouts = existing_timeouts.model_dump()
            data["timeouts"] = TimeoutConfig(**{**existing_timeouts, **value})
        elif key == "retry_policy" and isinstance(value, dict):
            # Merge retry policy
            existing_retry = data.get("retry_policy", {})
            if existing_retry and isinstance(existing_retry, RetryPolicy):
                existing_retry = existing_retry.model_dump()
            data["retry_policy"] = RetryPolicy(**{**(existing_retry or {}), **value})
        elif key == "retry_policy" and value is None:
            # Explicitly disable retry
            data["retry_policy"] = None
        else:
            data[key] = value

    return SDKConfig(**data)
