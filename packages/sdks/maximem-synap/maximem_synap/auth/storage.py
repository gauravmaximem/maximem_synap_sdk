"""Credential storage backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging
import os

from .models import Credentials
from ..models.errors import AuthenticationError


logger = logging.getLogger("synap.sdk.auth.storage")


class CredentialStorage(ABC):
    """Abstract base for credential storage backends."""

    @abstractmethod
    def store(self, credentials: Credentials) -> None:
        pass

    @abstractmethod
    def load(self) -> Optional[Credentials]:
        pass

    @abstractmethod
    def delete(self) -> None:
        pass

    @abstractmethod
    def exists(self) -> bool:
        pass


class FileCredentialStorage(CredentialStorage):
    """File-based credential storage.

    Credentials are stored as plain JSON with owner-only file permissions
    (0600). Do not commit the credentials file to version control.

    Default location: ~/.synap/instances/{instance_id}/credentials.json
    """

    _FILE_NAME = "credentials.json"

    def __init__(self, instance_id: str, storage_path: Optional[str] = None):
        self.instance_id = instance_id

        if storage_path:
            self.base_path = Path(storage_path)
        else:
            self.base_path = Path.home() / ".synap"

        self.credentials_dir = self.base_path / "instances" / instance_id
        self.credentials_file = self.credentials_dir / self._FILE_NAME

    def store(self, credentials: Credentials) -> None:
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.credentials_dir.chmod(0o700)
        except OSError:
            pass

        self.credentials_file.write_bytes(credentials.model_dump_json().encode())
        try:
            self.credentials_file.chmod(0o600)
        except OSError:
            pass

    def load(self) -> Optional[Credentials]:
        if not self.credentials_file.exists():
            return None
        try:
            return Credentials.model_validate_json(self.credentials_file.read_bytes())
        except Exception as e:
            raise AuthenticationError(f"Failed to load credentials: {e}")

    def delete(self) -> None:
        if self.credentials_file.exists():
            try:
                size = self.credentials_file.stat().st_size
                self.credentials_file.write_bytes(os.urandom(size))
            except OSError:
                pass
            try:
                self.credentials_file.unlink()
            except OSError:
                pass

    def exists(self) -> bool:
        return self.credentials_file.exists()


class EnvironmentCredentialStorage(CredentialStorage):
    """Read credentials from environment variables.

    Required: SYNAP_API_KEY
    Optional: SYNAP_INSTANCE_ID, SYNAP_CLIENT_ID
    """

    def __init__(self, instance_id: str):
        self.instance_id = instance_id

    def store(self, credentials: Credentials) -> None:
        raise NotImplementedError("Cannot store credentials in environment mode")

    def load(self) -> Optional[Credentials]:
        api_key = os.environ.get("SYNAP_API_KEY")
        if not api_key:
            return None
        return Credentials(
            api_key=api_key,
            instance_id=self.instance_id or os.environ.get("SYNAP_INSTANCE_ID", ""),
            client_id=os.environ.get("SYNAP_CLIENT_ID", ""),
        )

    def delete(self) -> None:
        pass

    def exists(self) -> bool:
        return "SYNAP_API_KEY" in os.environ
