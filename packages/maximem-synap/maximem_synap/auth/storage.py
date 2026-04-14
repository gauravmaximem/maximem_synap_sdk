"""Credential storage backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging
import os
import platform

from datetime import datetime, timezone, timedelta

from .models import Credentials
from ..models.errors import BootstrapError, AuthenticationError


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
    (0600). Protection is provided by the filesystem, not encryption. Do not
    commit the credentials file to version control or share it across users.

    Default storage location: ~/.synap/instances/{instance_id}/credentials.json
    """

    _LEGACY_FILE_NAME = "credentials.enc"
    _FILE_NAME = "credentials.json"

    def __init__(self, instance_id: str, storage_path: Optional[str] = None):
        self.instance_id = instance_id

        if storage_path:
            self.base_path = Path(storage_path)
        else:
            self.base_path = Path.home() / ".synap"

        self.credentials_dir = self.base_path / "instances" / instance_id
        self.credentials_file = self.credentials_dir / self._FILE_NAME
        self.legacy_file = self.credentials_dir / self._LEGACY_FILE_NAME

    def store(self, credentials: Credentials) -> None:
        """Store credentials as JSON with 0600 permissions."""
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.credentials_dir.chmod(0o700)
        except OSError:
            pass

        plaintext = credentials.model_dump_json().encode()
        self.credentials_file.write_bytes(plaintext)

        try:
            self.credentials_file.chmod(0o600)
        except OSError:
            pass

        if self.legacy_file.exists():
            try:
                self.legacy_file.unlink()
            except OSError:
                pass

    def load(self) -> Optional[Credentials]:
        """Load credentials from the JSON file, migrating from legacy if needed."""
        if self.credentials_file.exists():
            try:
                self._verify_permissions(self.credentials_file)
                plaintext = self.credentials_file.read_bytes()
                return Credentials.model_validate_json(plaintext)
            except Exception as e:
                raise AuthenticationError(f"Failed to load credentials: {e}")

        if self.legacy_file.exists():
            migrated = self._migrate_legacy()
            if migrated is not None:
                return migrated

        return None

    def _verify_permissions(self, path: Path) -> None:
        """Warn if the credentials file is not owner-only readable."""
        if os.name == "nt":
            return
        try:
            mode = path.stat().st_mode & 0o777
            if mode & 0o077:
                logger.warning(
                    "Credentials file %s has permissive mode %o. "
                    "Expected 0600. Anyone with access to this file can "
                    "impersonate this SDK client.",
                    path,
                    mode,
                )
        except OSError:
            pass

    def _migrate_legacy(self) -> Optional[Credentials]:
        """Attempt a one-time migration from the legacy encrypted file.

        Reads the old credentials.enc file (encrypted with a machine-derived
        Fernet key), decrypts it, writes a new credentials.json, and removes
        the legacy file. Returns None if decryption fails — the caller will
        treat this as "no credentials" and re-bootstrap.
        """
        try:
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            machine_id = self._get_machine_id_for_migration()
            salt = f"synap:{self.instance_id}".encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
            fernet = Fernet(key)

            encrypted = self.legacy_file.read_bytes()
            plaintext = fernet.decrypt(encrypted)
            credentials = Credentials.model_validate_json(plaintext)

            self.store(credentials)

            logger.info(
                "Migrated legacy credentials file to %s. Old file removed.",
                self.credentials_file,
            )
            return credentials

        except Exception as e:
            logger.warning(
                "Could not migrate legacy credentials from %s: %s. "
                "Re-bootstrap required.",
                self.legacy_file,
                e,
            )
            return None

    def _get_machine_id_for_migration(self) -> str:
        """Recreate the legacy machine_id for one-time decryption only."""
        system = platform.system()

        try:
            if system == "Linux":
                for path in ["/etc/machine-id", "/sys/class/dmi/id/product_uuid"]:
                    if os.path.exists(path):
                        with open(path, "r") as f:
                            return f.read().strip()
            elif system == "Darwin":
                import subprocess
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True, text=True
                )
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        return line.split('"')[-2]
            elif system == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True, text=True
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].strip()
        except Exception:
            pass

        import getpass
        return f"{platform.node()}:{getpass.getuser()}"

    def delete(self) -> None:
        """Delete credentials file(s) from disk."""
        for path in (self.credentials_file, self.legacy_file):
            if path.exists():
                try:
                    size = path.stat().st_size
                    path.write_bytes(os.urandom(size))
                except OSError:
                    pass
                try:
                    path.unlink()
                except OSError:
                    pass

    def exists(self) -> bool:
        return self.credentials_file.exists() or self.legacy_file.exists()


class EnvironmentCredentialStorage(CredentialStorage):
    """Read credentials from environment variables.

    Expected variables:
    - SYNAP_API_KEY
    - SYNAP_MTLS_CERT_PATH
    - SYNAP_MTLS_KEY_PATH
    - SYNAP_CLIENT_ID
    - SYNAP_INSTANCE_ID
    """

    def __init__(self, instance_id: str):
        self.instance_id = instance_id

    def store(self, credentials: Credentials) -> None:
        raise NotImplementedError("Cannot store credentials in environment mode")

    def load(self) -> Optional[Credentials]:
        try:
            api_key = os.environ["SYNAP_API_KEY"]
            client_id = os.environ["SYNAP_CLIENT_ID"]

            cert_path = os.environ.get("SYNAP_MTLS_CERT_PATH", "")
            key_path = os.environ.get("SYNAP_MTLS_KEY_PATH", "")

            mtls_cert = ""
            mtls_key = ""
            if cert_path and key_path:
                with open(cert_path, "r") as f:
                    mtls_cert = f.read()
                with open(key_path, "r") as f:
                    mtls_key = f.read()

            far_future = datetime.now(timezone.utc) + timedelta(days=365)
            now = datetime.now(timezone.utc)

            return Credentials(
                api_key=api_key,
                api_key_expires_at=far_future,
                mtls_cert=mtls_cert,
                mtls_private_key=mtls_key,
                mtls_expires_at=far_future,
                instance_id=self.instance_id,
                client_id=client_id,
                issued_at=now,
            )
        except KeyError as e:
            raise AuthenticationError(f"Missing environment variable: {e}")

    def delete(self) -> None:
        pass

    def exists(self) -> bool:
        return "SYNAP_API_KEY" in os.environ and "SYNAP_CLIENT_ID" in os.environ
