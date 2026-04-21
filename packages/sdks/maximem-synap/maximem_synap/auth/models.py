"""Authentication models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Credentials(BaseModel):
    """Stored SDK credentials."""
    api_key: str
    instance_id: str
    client_id: str = ""


class AuthContext(BaseModel):
    """Auth context attached to every request."""
    client_id: str
    instance_id: str
    api_key: str
    correlation_id: Optional[str] = None
