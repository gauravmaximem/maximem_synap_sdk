"""Credential and authentication models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Credentials(BaseModel):
    """Stored SDK credentials."""
    api_key: str
    api_key_expires_at: datetime
    mtls_cert: str
    mtls_private_key: str
    mtls_expires_at: datetime
    instance_id: str
    client_id: str
    issued_at: datetime


class BootstrapToken(BaseModel):
    """One-time bootstrap token from dashboard."""
    token: str
    instance_id: str
    expires_at: datetime


class AuthContext(BaseModel):
    """Immutable auth context for requests."""
    client_id: str
    instance_id: str
    api_key: str
    correlation_id: Optional[str] = None
