"""Correlation ID generation for request tracing."""

import secrets
import time


def generate_correlation_id(instance_id: str) -> str:
    """Generate a unique correlation ID for request tracing.

    Format: syn_{instance_prefix}_{timestamp_ms}_{random}
    Example: syn_abc123_1706123456789_x7k9m2

    Args:
        instance_id: The SDK instance ID (first 6 chars used)

    Returns:
        Unique correlation ID string
    """
    prefix = instance_id[:6] if len(instance_id) >= 6 else instance_id
    timestamp = int(time.time() * 1000)
    random_suffix = secrets.token_hex(3)  # 6 chars

    return f"syn_{prefix}_{timestamp}_{random_suffix}"
