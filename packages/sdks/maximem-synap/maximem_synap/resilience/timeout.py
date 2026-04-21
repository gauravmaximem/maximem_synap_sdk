"""Timeout control for operations."""

import asyncio
from typing import Callable, Any

from ..models.config import TimeoutConfig


class TimeoutController:
    """Timeout control for SDK operations."""

    def __init__(self, config: TimeoutConfig):
        """Initialize timeout controller.

        Args:
            config: Timeout configuration
        """
        self.config = config

    async def with_timeout(self, operation: Callable, timeout_ms: int) -> Any:
        """Execute operation with timeout.

        Args:
            operation: Async callable (zero-argument) to execute
            timeout_ms: Timeout in milliseconds

        Returns:
            Result of operation

        Raises:
            TimeoutError: If operation exceeds timeout
        """
        timeout_seconds = timeout_ms / 1000.0
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout_ms}ms")
