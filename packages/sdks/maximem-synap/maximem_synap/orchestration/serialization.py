"""JSON serialization utilities for requests and responses."""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Any

from ..models.requests import RequestEnvelope

logger = logging.getLogger("synap.sdk.orchestration")


def _json_serializer(obj):
    """Custom JSON serializer for types not natively serializable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_request(request: RequestEnvelope) -> str:
    """Serialize request envelope to JSON.

    Args:
        request: Request envelope to serialize

    Returns:
        JSON string
    """
    data = asdict(request)
    return json.dumps(data, default=_json_serializer)


def deserialize_response(json_str: str) -> Dict[str, Any]:
    """Deserialize JSON response.

    Args:
        json_str: JSON string to deserialize

    Returns:
        Parsed response dictionary
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to deserialize response: %s", e)
        raise ValueError(f"Invalid JSON response: {e}") from e
