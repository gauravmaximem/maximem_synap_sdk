"""OAuth2 token lifecycle management."""

import logging
from datetime import datetime, timezone
from typing import Optional

from .manager import CredentialManager
from ..models.auth import Token
from ..models.requests import RequestEnvelope

logger = logging.getLogger("synap.sdk.auth")


class TokenManager:
    """OAuth2 token lifecycle manager.

    Wraps CredentialManager to provide a Token-based interface.
    """

    def __init__(self, credential_manager: CredentialManager):
        """Initialize token manager.

        Args:
            credential_manager: Credential manager for auth context retrieval
        """
        self._credential_manager = credential_manager
        self._token: Optional[Token] = None

    async def get_token(self) -> Token:
        """Get current token, refreshing if needed.

        Returns:
            Valid access token
        """
        if self._token and self.is_token_valid():
            return self._token

        auth_context = await self._credential_manager.get_auth_context()
        self._token = Token(
            access_token=auth_context.api_key,
            token_type="Bearer",
            expires_at=None,  # Expiry managed by CredentialManager internally
        )
        return self._token

    async def refresh_token(self) -> Token:
        """Force token refresh.

        Returns:
            New access token
        """
        await self._credential_manager._refresh_credentials()
        self._token = None
        return await self.get_token()

    def is_token_valid(self) -> bool:
        """Check if current token is valid.

        Returns:
            True if token is valid and not expired
        """
        if self._token is None:
            return False
        if self._token.expires_at is None:
            return True  # Expiry managed by CredentialManager
        return datetime.now(timezone.utc) < self._token.expires_at

    def inject_auth(self, request: RequestEnvelope) -> RequestEnvelope:
        """Inject authentication into request.

        Args:
            request: Request envelope to authenticate

        Returns:
            Request with authentication headers
        """
        if self._token is None:
            raise ValueError("No token available. Call get_token() first.")
        request.metadata["authorization"] = (
            f"{self._token.token_type} {self._token.access_token}"
        )
        return request
