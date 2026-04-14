"""Telemetry collection and batching."""

import asyncio
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import secrets
from collections import Counter

from .models import TelemetryEvent, TelemetryEventType, TelemetryBatch


logger = logging.getLogger("synap.sdk.telemetry")


def _trace_events_enabled() -> bool:
    """Enable verbose per-event telemetry logs when explicitly requested."""
    return os.getenv("SYNAP_TELEMETRY_TRACE_EVENTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class TelemetryCollector:
    """Collects and batches telemetry events.

    Features:
    - Non-blocking event emission
    - Time-based and count-based batch flushing
    - Best-effort delivery (drops on failure)
    - Thread-safe
    """

    # Batching settings
    FLUSH_INTERVAL_SECONDS = 10.0
    FLUSH_THRESHOLD_COUNT = 50
    MAX_QUEUE_SIZE = 1000

    # Retry settings
    MAX_RETRIES = 2
    RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        instance_id: str,
        client_id: str,
        sdk_version: str,
        transport_callback: Optional[callable] = None,
        enabled: bool = True,
    ):
        self.instance_id = instance_id
        self.client_id = client_id
        self.sdk_version = sdk_version
        self.transport_callback = transport_callback
        self.enabled = enabled

        # Event queue (thread-safe)
        self._queue: deque[TelemetryEvent] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._lock = threading.Lock()

        # Background flush task
        self._flush_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background flush task."""
        if not self.enabled:
            return

        self._shutdown_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.debug("Telemetry collector started")

    async def stop(self) -> None:
        """Stop the collector and flush remaining events."""
        if not self.enabled:
            return

        self._shutdown_event.set()

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush()
        logger.debug("Telemetry collector stopped")

    def emit(
        self,
        event_type: TelemetryEventType,
        correlation_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status: str = "success",
        error_code: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Emit a telemetry event (non-blocking).

        Args:
            event_type: Type of event
            correlation_id: Request correlation ID
            latency_ms: Operation latency in milliseconds
            status: "success", "error", or "timeout"
            error_code: Error type name if status is "error"
            **kwargs: Additional fields (scope, cache_status, etc.)
        """
        if not self.enabled:
            return

        event = TelemetryEvent(
            event_type=event_type,
            instance_id=self.instance_id,
            client_id=self.client_id,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            **kwargs,
        )

        with self._lock:
            self._queue.append(event)
            queue_size = len(self._queue)

            # Check if we should trigger immediate flush
            if queue_size >= self.FLUSH_THRESHOLD_COUNT:
                asyncio.create_task(self._flush())

        if _trace_events_enabled():
            logger.info(
                "sdk_telemetry_event_queued event_type=%s correlation_id=%s status=%s latency_ms=%s queue_size=%d instance_id=%s client_id=%s",
                event.event_type.value,
                event.correlation_id,
                event.status,
                event.latency_ms,
                queue_size,
                event.instance_id,
                event.client_id,
            )

    def emit_dict(self, data: Dict[str, Any]) -> None:
        """Emit telemetry from a dictionary (for transport callbacks).

        Converts dict to proper TelemetryEvent.
        """
        if not self.enabled:
            return

        # Map string event_type to enum
        event_type_str = data.get("event_type", "error")
        try:
            event_type = TelemetryEventType(event_type_str)
        except ValueError:
            event_type = TelemetryEventType.ERROR

        self.emit(
            event_type=event_type,
            correlation_id=data.get("correlation_id"),
            latency_ms=data.get("latency_ms"),
            status=data.get("status", "success"),
            error_code=data.get("error_code"),
            scope=data.get("scope"),
            cache_status=data.get("cache_status"),
            attempt=data.get("attempt"),
            http_method=data.get("method"),
            http_path=data.get("path"),
            http_status_code=data.get("status_code"),
            metadata={
                k: v for k, v in data.items()
                if k not in {
                    "event_type", "correlation_id", "latency_ms", "status",
                    "error_code", "scope", "cache_status", "attempt",
                    "method", "path", "status_code", "instance_id", "client_id",
                }
            },
        )

    async def _flush_loop(self) -> None:
        """Background loop for periodic flushing."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.FLUSH_INTERVAL_SECONDS)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Flush loop error: {e}")

    async def _flush(self) -> None:
        """Flush pending events to transport."""
        if not self.transport_callback:
            # No transport configured, just clear the queue
            with self._lock:
                dropped = len(self._queue)
                self._queue.clear()
            if dropped:
                logger.warning(
                    "sdk_telemetry_flush_no_transport dropped_events=%d instance_id=%s client_id=%s",
                    dropped,
                    self.instance_id,
                    self.client_id,
                )
            return

        # Get events to send
        with self._lock:
            if not self._queue:
                return

            events = list(self._queue)
            self._queue.clear()

        if not events:
            return

        # Create batch
        batch = TelemetryBatch(
            events=events,
            sdk_version=self.sdk_version,
            batch_id=secrets.token_hex(8),
        )
        event_types = Counter(event.event_type.value for event in events)
        logger.info(
            "sdk_telemetry_flush_start batch_id=%s event_count=%d unique_event_types=%d event_types=%s instance_id=%s client_id=%s",
            batch.batch_id,
            len(events),
            len(event_types),
            dict(event_types),
            self.instance_id,
            self.client_id,
        )

        # Send with retries
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                await self.transport_callback(batch)
                logger.info(
                    "sdk_telemetry_flush_success batch_id=%s event_count=%d attempt=%d instance_id=%s client_id=%s",
                    batch.batch_id,
                    len(events),
                    attempt + 1,
                    self.instance_id,
                    self.client_id,
                )
                return

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        "sdk_telemetry_flush_retry batch_id=%s event_count=%d attempt=%d max_attempts=%d error=%s",
                        batch.batch_id,
                        len(events),
                        attempt + 1,
                        self.MAX_RETRIES + 1,
                        e,
                    )
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS)
                else:
                    # Max retries exceeded, drop the batch
                    logger.warning(
                        "sdk_telemetry_flush_drop batch_id=%s dropped_events=%d attempts=%d error=%s instance_id=%s client_id=%s",
                        batch.batch_id,
                        len(events),
                        self.MAX_RETRIES + 1,
                        e,
                        self.instance_id,
                        self.client_id,
                    )

    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        with self._lock:
            queue_size = len(self._queue)

        return {
            "enabled": self.enabled,
            "queue_size": queue_size,
            "max_queue_size": self.MAX_QUEUE_SIZE,
            "flush_interval_seconds": self.FLUSH_INTERVAL_SECONDS,
            "flush_threshold_count": self.FLUSH_THRESHOLD_COUNT,
        }


# Convenience functions for common events

def emit_fetch_event(
    collector: TelemetryCollector,
    scope: str,
    correlation_id: str,
    latency_ms: int,
    cache_hit: bool,
    status: str = "success",
    error_code: Optional[str] = None,
    mode: str = "fast",
    cache_origin: Optional[str] = None,
) -> None:
    """Emit a context fetch event with cache status."""
    metadata = {"mode": mode}
    if cache_origin:
        metadata["cache_origin"] = cache_origin

    # Emit cache event
    collector.emit(
        event_type=TelemetryEventType.CACHE_HIT if cache_hit else TelemetryEventType.CACHE_MISS,
        correlation_id=correlation_id,
        scope=scope,
        cache_status="hit" if cache_hit else "miss",
        metadata=metadata,
    )

    # Emit fetch event
    event_type_map = {
        "conversation": TelemetryEventType.FETCH_CONVERSATION_CONTEXT,
        "user": TelemetryEventType.FETCH_USER_CONTEXT,
        "customer": TelemetryEventType.FETCH_CUSTOMER_CONTEXT,
        "client": TelemetryEventType.FETCH_CLIENT_CONTEXT,
    }

    collector.emit(
        event_type=event_type_map.get(scope, TelemetryEventType.FETCH_USER_CONTEXT),
        correlation_id=correlation_id,
        latency_ms=latency_ms,
        status=status,
        error_code=error_code,
        scope=scope,
        cache_status="hit" if cache_hit else "miss",
        metadata=metadata,
    )


def emit_memory_event(
    collector: TelemetryCollector,
    event_type: TelemetryEventType,
    correlation_id: str,
    latency_ms: Optional[int] = None,
    status: str = "success",
    error_code: Optional[str] = None,
    **kwargs,
) -> None:
    """Emit a memory operation event."""
    if collector:
        collector.emit(
            event_type=event_type,
            correlation_id=correlation_id,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            **kwargs,
        )
