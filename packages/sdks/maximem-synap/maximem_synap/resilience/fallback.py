"""Fallback strategies for failed operations."""

import inspect
import logging
from typing import Callable, Any

logger = logging.getLogger("synap.sdk.resilience")


class FallbackStrategy:
    """Fallback strategy implementation."""

    async def execute_with_fallback(
        self,
        primary: Callable,
        fallback: Callable
    ) -> Any:
        """Execute primary operation with fallback on failure.

        Supports both sync and async callables for primary and fallback.

        Args:
            primary: Primary operation to attempt
            fallback: Fallback operation if primary fails

        Returns:
            Result from primary or fallback operation
        """
        try:
            result = primary()
            if inspect.isawaitable(result):
                return await result
            return result
        except Exception as e:
            logger.warning("Primary operation failed, executing fallback: %s", e)
            result = fallback()
            if inspect.isawaitable(result):
                return await result
            return result
