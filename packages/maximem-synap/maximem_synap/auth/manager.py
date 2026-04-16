"""Credential manager for API key authentication."""

import logging
import os
from typing import Optional

import httpx

from .models import Credentials, AuthContext
from .storage import FileCredentialStorage, EnvironmentCredentialStorage, CredentialStorage
from ..models.errors import BootstrapError, AuthenticationError


logger = logging.getLogger("synap.sdk.auth")


class CredentialManager:
    """Manages SDK credentials.

    Two auth modes:
    1. API key provided directly (via constructor, env var, or stored file).
       No network calls needed — the key is used as-is.
    2. Bootstrap token exchanged for an API key via the server.
       The resulting key is stored locally for subsequent runs.
    """

    def __init__(
        self,
        instance_id: str,
        storage: Optional[CredentialStorage] = None,
        credentials_source: str = "file",
        storage_path: Optional[str] = None,
    ):
        self.instance_id = instance_id
        self._credentials: Optional[Credentials] = None
        self._base_url: Optional[str] = None

        if storage:
            self._storage = storage
        elif credentials_source == "env":
            self._storage = EnvironmentCredentialStorage(instance_id)
        else:
            self._storage = FileCredentialStorage(instance_id, storage_path)

    def set_base_url(self, base_url: str) -> None:
        """Set the server base URL for bootstrap requests."""
        self._base_url = base_url

    @property
    def is_bootstrapped(self) -> bool:
        return self._storage.exists()

    async def load_or_bootstrap(
        self,
        api_key: Optional[str] = None,
        bootstrap_token: Optional[str] = None,
    ) -> Credentials:
        """Load existing credentials, use a provided API key, or bootstrap.

        Priority order:
        1. api_key parameter (direct)
        2. SYNAP_API_KEY environment variable
        3. Stored credentials on disk
        4. bootstrap_token exchange with server

        Returns:
            Valid Credentials object.
        """
        # Priority 1: API key passed directly
        key = api_key or os.environ.get("SYNAP_API_KEY")
        if key:
            instance_id = self.instance_id or os.environ.get("SYNAP_INSTANCE_ID", "")
            credentials = Credentials(
                api_key=key,
                instance_id=instance_id,
                client_id="",
            )
            self._credentials = credentials
            return credentials

        # Priority 2: Stored credentials
        if self._storage.exists():
            try:
                stored = self._storage.load()
                if stored:
                    self._credentials = stored
                    logger.debug("Loaded stored credentials")
                    return stored
            except Exception as e:
                logger.warning("Failed to load stored credentials: %s", e)

        # Priority 3: Bootstrap token exchange
        if not bootstrap_token:
            raise BootstrapError(
                "No API key provided. Set SYNAP_API_KEY environment variable, "
                "pass api_key= to MaximemSynapSDK(), or provide a bootstrap_token."
            )

        return await self._bootstrap(bootstrap_token)

    async def _bootstrap(self, bootstrap_token: str) -> Credentials:
        """Exchange a one-time bootstrap token for an API key."""
        base_url = self._base_url or "https://synap-cloud-prod.maximem.ai"

        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
                response = await client.post(
                    "/api/v1/keys/bootstrap",
                    json={
                        "bootstrap_key": bootstrap_token,
                        "instance_id": self.instance_id,
                    },
                )

                if response.status_code != 200:
                    try:
                        detail = response.json().get("detail", "Unknown error")
                    except Exception:
                        detail = f"HTTP {response.status_code}: {response.text}"
                    raise BootstrapError(f"Bootstrap failed: {detail}")

                data = response.json()

        except BootstrapError:
            raise
        except Exception as e:
            raise BootstrapError(f"Bootstrap request failed: {e}") from e

        credentials = Credentials(
            api_key=data["api_key"],
            instance_id=data["instance_id"],
            client_id=data["client_id"],
        )

        try:
            self._storage.store(credentials)
        except NotImplementedError:
            pass  # env mode can't store

        self._credentials = credentials
        logger.info("Bootstrapped instance %s", self.instance_id)
        return credentials

    async def get_auth_context(self, correlation_id: Optional[str] = None) -> AuthContext:
        """Get auth context for making requests."""
        if not self._credentials:
            self._credentials = self._storage.load()

        if not self._credentials:
            raise AuthenticationError("No credentials available. Initialize the SDK first.")

        return AuthContext(
            client_id=self._credentials.client_id,
            instance_id=self._credentials.instance_id,
            api_key=self._credentials.api_key,
            correlation_id=correlation_id,
        )

    def clear(self) -> None:
        """Clear stored credentials."""
        self._storage.delete()
        self._credentials = None
