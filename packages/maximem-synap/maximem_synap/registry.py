"""SDK instance registry for singleton pattern."""

import threading
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sdk import MaximemSynapSDK


class SDKRegistry:
    """Registry for SDK instances (singleton per instance_id)."""

    _instances: Dict[str, "MaximemSynapSDK"] = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, instance_id: str) -> Optional["MaximemSynapSDK"]:
        """Get existing SDK instance for instance_id."""
        with cls._lock:
            return cls._instances.get(instance_id)

    @classmethod
    def register(cls, instance_id: str, sdk: "MaximemSynapSDK") -> None:
        """Register an SDK instance."""
        with cls._lock:
            cls._instances[instance_id] = sdk

    @classmethod
    def unregister(cls, instance_id: str) -> None:
        """Unregister an SDK instance."""
        with cls._lock:
            cls._instances.pop(instance_id, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered instances (for testing)."""
        with cls._lock:
            cls._instances.clear()
