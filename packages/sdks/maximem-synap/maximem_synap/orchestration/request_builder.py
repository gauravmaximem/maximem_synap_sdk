"""Request envelope builder with correlation ID generation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from ..models.requests import RequestEnvelope


class RequestBuilder:
    """Build request envelopes with metadata and correlation tracking."""

    def build_fetch_request(
        self,
        scope: str,
        entity_id: str,
        filters: Dict[str, Any]
    ) -> RequestEnvelope:
        """Build fetch request envelope.

        Args:
            scope: Scope of the request (e.g., "conversation", "user")
            entity_id: Entity identifier
            filters: Request filters (search_query, max_results, types)

        Returns:
            Request envelope ready for transport
        """
        return RequestEnvelope(
            correlation_id=self.generate_correlation_id(),
            scope=scope,
            entity_id=entity_id,
            filters=filters,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

    def generate_correlation_id(self) -> str:
        """Generate unique correlation ID.

        Returns:
            UUID v4 correlation ID
        """
        return str(uuid.uuid4())
