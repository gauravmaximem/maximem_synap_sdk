"""Credential manager - handles bootstrap, storage, and rotation."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .models import Credentials, BootstrapToken, AuthContext
from .storage import CredentialStorage, FileCredentialStorage, EnvironmentCredentialStorage
from .cert_manager import CertManager
from ..models.errors import BootstrapError, AuthenticationError


logger = logging.getLogger("synap.sdk.auth")


class CredentialManager:
    """Manages SDK credential lifecycle.

    Responsibilities:
    - Bootstrap: Exchange one-time token for credentials
    - Storage: Persist credentials securely
    - Rotation: Auto-refresh before expiry
    - Access: Provide AuthContext for requests
    """

    # Renew certificate when this fraction of the TTL has been consumed.
    # Matches CertManager.RENEWAL_THRESHOLD (70% consumed → 30% remaining).
    RENEWAL_THRESHOLD = 0.7

    def __init__(
        self,
        instance_id: str,
        storage: Optional[CredentialStorage] = None,
        credentials_source: str = "file",
        storage_path: Optional[str] = None,
    ):
        self.instance_id = instance_id
        self._credentials: Optional[Credentials] = None

        # Initialize storage backend
        if storage:
            self._storage = storage
        elif credentials_source == "env":
            self._storage = EnvironmentCredentialStorage(instance_id)
        else:
            self._storage = FileCredentialStorage(instance_id, storage_path)

        # HTTP client for auth endpoints (injected later)
        self._auth_client = None

    def set_auth_client(self, client) -> None:
        """Inject the HTTP client for auth API calls."""
        self._auth_client = client

    @property
    def is_bootstrapped(self) -> bool:
        """Check if SDK has valid credentials."""
        return self._storage.exists()

    async def bootstrap(self, bootstrap_token: str) -> Credentials:
        """Exchange one-time bootstrap token for credentials.

        Generates an RSA private key and CSR locally, sends the CSR along
        with the bootstrap key to the cloud, receives a signed certificate,
        and persists everything to disk.

        Args:
            bootstrap_token: One-time bootstrap key from Synap dashboard

        Returns:
            Credentials object

        Raises:
            BootstrapError: If bootstrap fails
        """
        try:
            # 1. Generate RSA private key and CSR
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            csr = (
                x509.CertificateSigningRequestBuilder()
                .subject_name(
                    x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self.instance_id)])
                )
                .sign(private_key, hashes.SHA256())
            )
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

            # 2. POST to /api/v1/certs/bootstrap
            base_url = (
                self._auth_client.base_url
                if self._auth_client
                else "https://synap-cloud-prod.maximem.ai"
            )

            async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
                response = await client.post(
                    "/api/v1/certs/bootstrap",
                    json={
                        "csr": csr_pem,
                        "bootstrap_key": bootstrap_token,
                        "instance_id": self.instance_id,
                    }
                )

                if response.status_code != 200:
                    try:
                        error_detail = response.json().get("detail", "Unknown error")
                    except Exception:
                        error_detail = f"HTTP {response.status_code}: {response.text}"
                    raise BootstrapError(f"Bootstrap failed: {error_detail}")

                data = response.json()

            # 3. Extract response fields
            cert_pem = data["certificate"]
            fingerprint = data["fingerprint"]
            issued_at_str = data["issued_at"]
            expires_at_str = data["expires_at"]
            client_id = data["client_id"]

            mtls_expires_at = datetime.fromisoformat(expires_at_str)

            # 4. Save cert + key locally
            cert_dir = Path.home() / ".synap" / "instances" / self.instance_id
            cert_dir.mkdir(parents=True, exist_ok=True)
            cert_dir.chmod(0o700)

            cert_path = cert_dir / "cert.pem"
            cert_path.write_text(cert_pem)
            cert_path.chmod(0o600)

            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()

            key_path = cert_dir / "key.pem"
            key_path.write_text(key_pem)
            key_path.chmod(0o600)

            metadata_path = cert_dir / "metadata.json"
            metadata_path.write_text(json.dumps({
                "instance_id": self.instance_id,
                "client_id": client_id,
                "fingerprint": fingerprint,
                "issued_at": issued_at_str,
                "expires_at": expires_at_str,
            }))
            metadata_path.chmod(0o600)

            # 5. Create Credentials object.
            #    api_key holds the cert fingerprint — sent as Bearer token on
            #    every request. api_key_expires_at tracks the real 7-day cert
            #    expiry so _is_expired() triggers renewal at 70% TTL.
            now = datetime.now(timezone.utc)

            credentials = Credentials(
                api_key=fingerprint,
                api_key_expires_at=mtls_expires_at,
                mtls_cert=cert_pem,
                mtls_private_key=key_pem,
                mtls_expires_at=mtls_expires_at,
                instance_id=self.instance_id,
                client_id=client_id,
                issued_at=now,
            )

            # 6. Store credentials via existing storage backend
            self._storage.store(credentials)
            self._credentials = credentials

            logger.info(f"Successfully bootstrapped instance {self.instance_id}")
            return credentials

        except Exception as e:
            if isinstance(e, BootstrapError):
                raise
            raise BootstrapError(f"Bootstrap failed: {e}") from e

    async def load_or_bootstrap(self, bootstrap_token: Optional[str] = None) -> Credentials:
        """Load existing credentials or bootstrap if needed.

        Args:
            bootstrap_token: Required if not already bootstrapped

        Returns:
            Valid credentials

        Raises:
            BootstrapError: If bootstrap needed but no token provided
            AuthenticationError: If stored credentials are invalid
        """
        # Try loading existing credentials
        if self._storage.exists():
            try:
                self._credentials = self._storage.load()
                if self._credentials:
                    if not self._is_expired(self._credentials):
                        logger.debug("Loaded existing credentials")
                        return self._credentials
                    # Credentials exist but past renewal threshold — try to renew,
                    # but if renewal is unavailable (e.g. staging), use as-is
                    # since the mTLS cert may still be physically valid.
                    logger.info(
                        "Credentials past renewal threshold — attempting auto-renewal"
                    )
                    try:
                        await self._refresh_credentials()
                        logger.info("Auto-renewal successful")
                        return self._credentials
                    except Exception as renew_exc:
                        logger.warning(
                            f"Auto-renewal failed: {renew_exc}"
                        )
                    # Renewal failed — decide whether to use as-is or require re-bootstrap.
                    if not self._is_physically_expired(self._credentials):
                        # Cert is still within its valid window; let the server decide.
                        logger.warning(
                            "Auto-renewal failed but cert is still physically valid "
                            "— continuing with existing credentials"
                        )
                        return self._credentials
                    # Cert is past notAfter.  Fall through so bootstrap() is attempted
                    # if a token was provided, or raise a clear error if not.
                    logger.warning("Certificate is physically expired; renewal failed.")
            except Exception as e:
                logger.warning(f"Failed to load stored credentials: {e}")

        # Need to bootstrap
        if not bootstrap_token:
            # Distinguish between "never bootstrapped" and "cert expired, no token"
            if self._credentials is not None:
                raise BootstrapError(
                    "Certificate has expired and renewal failed. "
                    "Obtain a fresh bootstrap_token from the dashboard and pass it "
                    "to initialize()."
                )
            raise BootstrapError(
                "SDK not bootstrapped. Provide bootstrap_token from dashboard."
            )

        return await self.bootstrap(bootstrap_token)

    def _is_expired(self, credentials: Credentials) -> bool:
        """Check if certificate needs renewal (70% of TTL consumed)."""
        now = datetime.now(timezone.utc)

        issued = credentials.issued_at
        expires = credentials.mtls_expires_at

        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=timezone.utc)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        total = (expires - issued).total_seconds()
        if total <= 0:
            return True

        elapsed = (now - issued).total_seconds()
        return (elapsed / total) >= self.RENEWAL_THRESHOLD

    def _is_physically_expired(self, credentials: Credentials) -> bool:
        """Check if the mTLS certificate's notAfter date has passed.

        This is the hard boundary — _is_expired() fires at 70% TTL as an
        early-renewal hint, but only this method reflects whether the cert
        is actually rejected by the server.  Prefer parsing the PEM directly
        (authoritative), fall back to the stored mtls_expires_at timestamp.
        """
        now = datetime.now(timezone.utc)
        if credentials.mtls_cert:
            try:
                from cryptography import x509 as _x509
                cert = _x509.load_pem_x509_certificate(credentials.mtls_cert.encode())
                return now >= cert.not_valid_after_utc
            except Exception:
                pass
        # Fall back to the stored expiry
        expires = credentials.mtls_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now >= expires

    async def get_auth_context(self, correlation_id: Optional[str] = None) -> AuthContext:
        """Get current auth context for making requests.

        Will auto-refresh credentials if needed.

        Returns:
            AuthContext with current valid credentials
        """
        if not self._credentials:
            self._credentials = self._storage.load()

        if not self._credentials:
            raise AuthenticationError("No credentials available. Bootstrap required.")

        # Check if refresh needed — if renewal fails, continue only when the cert
        # is still within its physical notAfter window; raise once it is truly dead.
        if self._is_expired(self._credentials):
            try:
                await self._refresh_credentials()
            except Exception as exc:
                logger.warning(
                    "Credential refresh failed: %s", exc
                )
                if self._is_physically_expired(self._credentials):
                    raise AuthenticationError(
                        "Certificate has expired and renewal failed. "
                        "Re-initialize with a fresh bootstrap token."
                    ) from exc
                logger.warning("Using existing cert (still within notAfter window)")

        return AuthContext(
            client_id=self._credentials.client_id,
            instance_id=self._credentials.instance_id,
            api_key=self._credentials.api_key,
            correlation_id=correlation_id,
        )

    async def _refresh_credentials(self) -> None:
        """Renew the mTLS certificate and update credentials with the new fingerprint.

        Sends the existing cert fingerprint as X-Cert-Fingerprint to authenticate
        the renewal request (POST /api/v1/certs/renew). The server issues a new
        7-day cert, revokes the old credential, and the new fingerprint becomes
        the Bearer token for all subsequent requests.
        """
        if not self._credentials:
            raise AuthenticationError("No credentials to refresh")

        cert_dir = Path.home() / ".synap" / "instances" / self.instance_id
        key_path = cert_dir / "key.pem"

        if not key_path.exists():
            raise AuthenticationError("Private key not found on disk. Re-bootstrap required.")

        # Reuse the existing private key — renewal keeps the same key, just gets a new cert.
        private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self.instance_id)]))
            .sign(private_key, hashes.SHA256())
        )
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

        base_url = (
            self._auth_client.base_url
            if self._auth_client and hasattr(self._auth_client, "base_url")
            else "https://synap-cloud-prod.maximem.ai"
        )

        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
                response = await client.post(
                    "/api/v1/certs/renew",
                    json={"csr": csr_pem},
                    headers={"X-Cert-Fingerprint": self._credentials.api_key},
                )
        except Exception as e:
            raise AuthenticationError(f"Certificate renewal request failed: {e}") from e

        if response.status_code != 200:
            try:
                detail = response.json().get("detail", "Unknown error")
            except Exception:
                detail = f"HTTP {response.status_code}"
            raise AuthenticationError(f"Certificate renewal failed: {detail}")

        data = response.json()
        cert_pem = data["certificate"]
        cert_pem_bytes = cert_pem.encode() if isinstance(cert_pem, str) else cert_pem

        # Extract new fingerprint and expiry from the issued certificate.
        from cryptography import x509 as _x509
        cert_obj = _x509.load_pem_x509_certificate(cert_pem_bytes)
        fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
        new_expires_at = cert_obj.not_valid_after_utc

        # Persist new cert to disk (same paths as bootstrap).
        cert_path = cert_dir / "cert.pem"
        cert_path.write_bytes(cert_pem_bytes)
        cert_path.chmod(0o600)

        now = datetime.now(timezone.utc)
        metadata_path = cert_dir / "metadata.json"
        metadata_path.write_text(json.dumps({
            "instance_id": self.instance_id,
            "client_id": self._credentials.client_id,
            "fingerprint": fingerprint,
            "issued_at": now.isoformat(),
            "expires_at": new_expires_at.isoformat(),
        }))
        metadata_path.chmod(0o600)

        self._credentials = Credentials(
            api_key=fingerprint,
            api_key_expires_at=new_expires_at,
            mtls_cert=cert_pem,
            mtls_private_key=self._credentials.mtls_private_key,
            mtls_expires_at=new_expires_at,
            instance_id=self.instance_id,
            client_id=self._credentials.client_id,
            issued_at=now,
        )

        self._storage.store(self._credentials)
        logger.info(f"Certificate renewed for instance {self.instance_id}")

    def clear(self) -> None:
        """Clear stored credentials."""
        self._storage.delete()
        self._credentials = None
        logger.info("Credentials cleared")
