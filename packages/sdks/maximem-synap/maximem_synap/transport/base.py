"""Abstract base transport interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.requests import RequestEnvelope, ResponseEnvelope


class BaseTransport(ABC):
    """Abstract base class for transport implementations."""
    
    @abstractmethod
    async def send(self, request: "RequestEnvelope") -> "ResponseEnvelope":
        """Send a request and return response."""
        raise NotImplementedError("Must be implemented by subclass")
    
    @abstractmethod
    async def close(self) -> None:
        """Close transport connection."""
        raise NotImplementedError("Must be implemented by subclass")
