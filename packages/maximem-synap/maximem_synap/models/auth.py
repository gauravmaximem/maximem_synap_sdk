"""Authentication models for MaximemSynap SDK."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta, timezone


@dataclass
class Token:
    """OAuth2 access token."""
    
    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None


@dataclass
class Cert:
    """mTLS certificate."""
    
    instance_id: str
    client_id: str
    cert_pem: bytes
    issued_at: datetime
    expires_at: datetime
    fingerprint: str
    
    def is_valid(self) -> bool:
        """Check if certificate is not expired.

        Returns:
            True if certificate is valid and not expired
        """
        return datetime.now(timezone.utc) < self.expires_at
    
    def time_until_expiry(self) -> timedelta:
        """Get remaining time until certificate expires.

        Returns:
            Timedelta representing remaining TTL
        """
        remaining = self.expires_at - datetime.now(timezone.utc)
        return max(remaining, timedelta(0))
    
    def ttl_percentage_remaining(self) -> float:
        """Calculate percentage of TTL remaining.

        Returns:
            Float between 0.0 and 1.0 representing TTL percentage
        """
        total_ttl = (self.expires_at - self.issued_at).total_seconds()
        if total_ttl <= 0:
            return 0.0
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, min(1.0, remaining / total_ttl))


@dataclass
class CertMetadata:
    """Certificate metadata for persistence."""
    
    instance_id: str
    client_id: str
    issued_at: datetime
    expires_at: datetime
    fingerprint: str
    ca_fingerprint: str


@dataclass
class AuthContext:
    """Authentication context for requests."""
    
    token: Optional[Token] = None
    cert: Optional[Cert] = None
    instance_id: str = ""
    client_id: str = ""
