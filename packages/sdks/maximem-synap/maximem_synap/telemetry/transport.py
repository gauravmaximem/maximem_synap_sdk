"""Telemetry transport - sends batches to Synap cloud."""

import logging
from collections import Counter
from typing import Optional

import httpx

from .models import TelemetryBatch
from ..auth.models import AuthContext


logger = logging.getLogger("synap.sdk.telemetry")


class TelemetryTransport:
    """Sends telemetry batches to Synap cloud.

    Best-effort, async, non-blocking on the main request path.
    """

    TELEMETRY_ENDPOINT = "/v1/telemetry/batch"

    def __init__(
        self,
        base_url: str,
        get_auth_context: callable,
    ):
        self.base_url = base_url
        self.get_auth_context = get_auth_context

        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(5.0),  # Short timeout for telemetry
        )

    async def send(self, batch: TelemetryBatch) -> None:
        """Send a telemetry batch.

        Args:
            batch: Batch of events to send

        Raises:
            Exception: On transport failure (caller handles retry)
        """
        try:
            auth_context = await self.get_auth_context()
        except Exception as e:
            # If we can't get auth, skip telemetry silently
            logger.warning(
                "sdk_telemetry_send_skipped_no_auth batch_id=%s event_count=%d error=%s",
                batch.batch_id,
                len(batch.events),
                e,
            )
            return

        event_types = Counter(event.event_type.value for event in batch.events)
        logger.info(
            "sdk_telemetry_send_start batch_id=%s event_count=%d unique_event_types=%d event_types=%s endpoint=%s base_url=%s client_id=%s instance_id=%s",
            batch.batch_id,
            len(batch.events),
            len(event_types),
            dict(event_types),
            self.TELEMETRY_ENDPOINT,
            self.base_url,
            auth_context.client_id,
            auth_context.instance_id,
        )

        headers = {
            "Authorization": f"Bearer {auth_context.api_key}",
            "X-Client-ID": auth_context.client_id,
            "X-Instance-ID": auth_context.instance_id,
            "Content-Type": "application/json",
        }

        # Serialize batch
        payload = {
            "events": [
                {
                    "event_type": e.event_type.value,
                    "instance_id": e.instance_id,
                    "client_id": e.client_id,
                    "correlation_id": e.correlation_id,
                    "timestamp": e.timestamp.isoformat(),
                    "latency_ms": e.latency_ms,
                    "status": e.status,
                    "error_code": e.error_code,
                    "scope": e.scope,
                    "cache_status": e.cache_status,
                    "attempt": e.attempt,
                    "http_method": e.http_method,
                    "http_path": e.http_path,
                    "http_status_code": e.http_status_code,
                    "metadata": e.metadata,
                }
                for e in batch.events
            ],
            "sdk_version": batch.sdk_version,
            "batch_id": batch.batch_id,
            "created_at": batch.created_at.isoformat(),
        }

        response = await self._client.post(
            self.TELEMETRY_ENDPOINT,
            headers=headers,
            json=payload,
        )

        if response.status_code not in (200, 202):
            body_preview = response.text[:400] if response.text else ""
            logger.warning(
                "sdk_telemetry_send_failed batch_id=%s status_code=%d body_preview=%s client_id=%s instance_id=%s",
                batch.batch_id,
                response.status_code,
                body_preview,
                auth_context.client_id,
                auth_context.instance_id,
            )
            raise Exception(f"Telemetry send failed: {response.status_code}")

        logger.info(
            "sdk_telemetry_send_success batch_id=%s status_code=%d event_count=%d client_id=%s instance_id=%s",
            batch.batch_id,
            response.status_code,
            len(batch.events),
            auth_context.client_id,
            auth_context.instance_id,
        )

    async def close(self) -> None:
        """Close the transport client."""
        await self._client.aclose()
