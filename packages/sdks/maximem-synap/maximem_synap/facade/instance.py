"""Instance controller for gRPC streaming."""

import logging
from typing import Any, Awaitable, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport.grpc_client import GRPCTransport
    from ..auth.models import AuthContext

logger = logging.getLogger("synap.sdk.facade.instance")


class InstanceController:
    """Controller for instance-level gRPC streaming operations.

    Provides the public API surface for listen/stop lifecycle.
    Wraps GRPCTransport with auth context resolution and
    idempotency guards.
    """

    def __init__(
        self,
        transport_factory: Callable[..., "GRPCTransport"],
        auth_provider: Callable[[], Awaitable["AuthContext"]],
    ):
        """Initialize instance controller.

        Args:
            transport_factory: Callable that creates a GRPCTransport.
                Accepts keyword arguments (on_reconnect, on_disconnect)
                and returns a new transport instance.
            auth_provider: Async callable returning an AuthContext for
                authenticating the gRPC connection.
        """
        self._transport_factory = transport_factory
        self._auth_provider = auth_provider
        self._transport: Optional["GRPCTransport"] = None

    async def listen(
        self,
        on_reconnect: Optional[Callable[[int], None]] = None,
        on_disconnect: Optional[Callable[[str], None]] = None,
        on_message: Optional[Callable] = None,
    ) -> None:
        """Start gRPC bidirectional stream for real-time updates.

        Creates a GRPCTransport via the factory, resolves auth context,
        and establishes the connection.

        Args:
            on_reconnect: Callback when stream reconnects (receives attempt count).
            on_disconnect: Callback when stream disconnects (receives reason).
            on_message: Callback when an anticipated context bundle arrives.

        Raises:
            ListeningAlreadyActiveError: If a stream is already active.
        """
        from ..models.errors import ListeningAlreadyActiveError

        if self.is_listening:
            raise ListeningAlreadyActiveError()

        self._transport = self._transport_factory(
            on_reconnect=on_reconnect,
            on_disconnect=on_disconnect,
            on_message=on_message,
        )

        auth_context = await self._auth_provider()
        await self._transport.connect(auth_context)

        logger.info("Listening started")

    async def stop(self) -> None:
        """Gracefully close bidirectional stream.

        Idempotent — no-op if not currently listening.
        """
        if self._transport is not None:
            await self._transport.close()
            self._transport = None
            logger.info("Listening stopped")

    @property
    def is_listening(self) -> bool:
        """Check if stream is active.

        Returns:
            True if a transport exists and reports connected.
        """
        return self._transport is not None and self._transport.is_connected
