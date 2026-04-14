"""mTLS certificate management.

Handles the full certificate lifecycle on the SDK side:
- Private key generation/loading (key never leaves SDK)
- CSR generation for cloud signing
- Certificate bootstrap via one-time key
- Certificate renewal via mTLS
- Local persistence (cert.pem, key.pem, metadata.json)
- SSL context attachment for gRPC/streaming
"""

import json
import logging
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509.oid import NameOID

from ..models.auth import Cert, CertMetadata
from ..models.errors import (
    BootstrapError,
    BootstrapKeyInvalidError,
    CertificateExpiredError,
    CertificateRenewalError,
)

logger = logging.getLogger("synap.sdk.cert")

# RSA key size for SDK-generated private keys
_RSA_KEY_SIZE = 2048


class CertManager:
    """mTLS certificate manager with persistent storage and lifecycle management.

    The SDK owns the private key — it is generated locally and never transmitted.
    Certificates are obtained by submitting a CSR to the cloud, which signs it
    via its Certificate Authority.
    """

    CERT_DIR = ".synap/instances/{instance_id}"
    RENEWAL_THRESHOLD = 0.7  # Renew when <30% TTL remaining

    def __init__(
        self,
        instance_id: str,
        client_id: str,
        auth_client: Optional[Any] = None,
        base_path: Optional[Path] = None,
    ):
        """Initialize certificate manager.

        Args:
            instance_id: Instance ID for certificate binding
            client_id: Client ID for certificate binding
            auth_client: HTTP client for cloud auth endpoints
            base_path: Override base storage path (default: ~/.synap/instances/...)
        """
        self.instance_id = instance_id
        self.client_id = client_id
        self._cert: Optional[Cert] = None
        self._private_key: Optional[PrivateKeyTypes] = None
        self._auth_client = auth_client

        if base_path is not None:
            self._cert_dir = base_path / instance_id
        else:
            self._cert_dir = (
                Path.home() / self.CERT_DIR.format(instance_id=instance_id)
            )

    def set_auth_client(self, client: Any) -> None:
        """Inject the HTTP client for cloud auth calls."""
        self._auth_client = client

    # ------------------------------------------------------------------
    # Local storage
    # ------------------------------------------------------------------

    def load_cert(self) -> Optional[Cert]:
        """Load certificate from local storage.

        Reads cert.pem and metadata.json from the instance cert directory.

        Returns:
            Cert if exists and loadable, else None
        """
        cert_path = self._cert_dir / "cert.pem"
        meta_path = self._cert_dir / "metadata.json"

        if not cert_path.exists() or not meta_path.exists():
            return None

        try:
            cert_pem = cert_path.read_bytes()
            meta_raw = json.loads(meta_path.read_text())

            self._cert = Cert(
                instance_id=meta_raw["instance_id"],
                client_id=meta_raw["client_id"],
                cert_pem=cert_pem,
                issued_at=datetime.fromisoformat(meta_raw["issued_at"]),
                expires_at=datetime.fromisoformat(meta_raw["expires_at"]),
                fingerprint=meta_raw["fingerprint"],
            )
            return self._cert
        except Exception as e:
            logger.warning(f"Failed to load certificate: {e}")
            return None

    def save_cert(self, cert: Cert) -> None:
        """Persist certificate to local storage.

        Creates directory structure and saves:
        - cert.pem (PEM certificate)
        - metadata.json (CertMetadata as JSON)

        Args:
            cert: Certificate to persist
        """
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        self._cert_dir.chmod(0o700)

        cert_path = self._cert_dir / "cert.pem"
        cert_path.write_bytes(
            cert.cert_pem if isinstance(cert.cert_pem, bytes)
            else cert.cert_pem.encode()
        )
        cert_path.chmod(0o600)

        meta = CertMetadata(
            instance_id=cert.instance_id,
            client_id=cert.client_id,
            issued_at=cert.issued_at,
            expires_at=cert.expires_at,
            fingerprint=cert.fingerprint,
            ca_fingerprint="",
        )
        meta_path = self._cert_dir / "metadata.json"
        meta_path.write_text(json.dumps({
            "instance_id": meta.instance_id,
            "client_id": meta.client_id,
            "issued_at": meta.issued_at.isoformat(),
            "expires_at": meta.expires_at.isoformat(),
            "fingerprint": meta.fingerprint,
            "ca_fingerprint": meta.ca_fingerprint,
        }))
        meta_path.chmod(0o600)

        self._cert = cert

    # ------------------------------------------------------------------
    # Private key management
    # ------------------------------------------------------------------

    def get_private_key(self) -> PrivateKeyTypes:
        """Load or generate private key.

        The private key is SDK-owned and never leaves the SDK host.
        If a key already exists on disk it is loaded; otherwise a new
        RSA key is generated and persisted.

        Returns:
            RSA private key
        """
        if self._private_key is not None:
            return self._private_key

        key_path = self._cert_dir / "key.pem"

        if key_path.exists():
            key_data = key_path.read_bytes()
            self._private_key = serialization.load_pem_private_key(key_data, password=None)
            return self._private_key

        # Generate new key
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=_RSA_KEY_SIZE,
        )

        # Persist
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        self._cert_dir.chmod(0o700)

        key_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(key_pem)
        key_path.chmod(0o600)

        return self._private_key

    # ------------------------------------------------------------------
    # CSR generation
    # ------------------------------------------------------------------

    def generate_csr(self) -> str:
        """Create a PEM-encoded Certificate Signing Request.

        Uses the SDK-owned private key. The CSR subject CN is set to
        the instance_id so the cloud can bind the certificate.

        Returns:
            PEM-encoded CSR string
        """
        key = self.get_private_key()
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self.instance_id)])
            )
            .sign(key, hashes.SHA256())
        )
        return csr.public_bytes(serialization.Encoding.PEM).decode()

    # ------------------------------------------------------------------
    # Renewal check
    # ------------------------------------------------------------------

    def needs_renewal(self) -> bool:
        """Check if certificate needs renewal.

        Returns True when the TTL percentage remaining drops below
        (1 - RENEWAL_THRESHOLD), i.e. less than 30% of the total
        lifetime remains.

        Returns:
            True if renewal is recommended
        """
        if self._cert is None:
            return False
        return self._cert.ttl_percentage_remaining() < (1.0 - self.RENEWAL_THRESHOLD)

    # ------------------------------------------------------------------
    # Bootstrap (first-time certificate acquisition)
    # ------------------------------------------------------------------

    def bootstrap_cert(self, bootstrap_key: str) -> Cert:
        """Bootstrap certificate using a one-time bootstrap key.

        Flow:
        1. Generate or load private key
        2. Generate CSR
        3. POST CSR + bootstrap_key to cloud
        4. Receive signed certificate
        5. Save certificate and metadata locally

        Args:
            bootstrap_key: One-time bootstrap key from the dashboard

        Returns:
            Newly bootstrapped Cert

        Raises:
            BootstrapKeyInvalidError: If the bootstrap key is rejected
            BootstrapError: If the bootstrap call fails
        """
        if self._auth_client is None:
            raise BootstrapError("Auth client not initialized")

        csr_pem = self.generate_csr()

        try:
            response = self._auth_client.post(
                "/api/v1/certs/bootstrap",
                json={
                    "csr": csr_pem,
                    "bootstrap_key": bootstrap_key,
                },
            )
        except Exception as e:
            raise BootstrapError(f"Bootstrap request failed: {e}") from e

        status = getattr(response, "status_code", None)
        if status == 401 or status == 403:
            raise BootstrapKeyInvalidError("Bootstrap key rejected by cloud")
        if status is not None and status >= 400:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except Exception:
                pass
            raise BootstrapError(f"Bootstrap failed (HTTP {status}): {detail}")

        data = response.json()
        cert_pem = data["certificate"]
        cert_pem_bytes = cert_pem.encode() if isinstance(cert_pem, str) else cert_pem

        cert = Cert(
            instance_id=self.instance_id,
            client_id=self.client_id,
            cert_pem=cert_pem_bytes,
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            fingerprint=data["fingerprint"],
        )

        self.save_cert(cert)
        return cert

    # ------------------------------------------------------------------
    # Renewal (using current cert as mTLS auth)
    # ------------------------------------------------------------------

    def renew_cert(self) -> Cert:
        """Renew certificate using current cert as mTLS authentication.

        Flow:
        1. Generate CSR with existing private key
        2. POST CSR via mTLS-authenticated request (current cert fingerprint)
        3. Receive renewed certificate
        4. Save certificate and metadata locally

        Returns:
            Renewed Cert

        Raises:
            CertificateRenewalError: If renewal fails
        """
        if self._auth_client is None:
            raise CertificateRenewalError("Auth client not initialized")
        if self._cert is None:
            raise CertificateRenewalError("No current certificate to renew")

        csr_pem = self.generate_csr()

        try:
            response = self._auth_client.post(
                "/api/v1/certs/renew",
                json={"csr": csr_pem},
                headers={"X-Cert-Fingerprint": self._cert.fingerprint},
            )
        except Exception as e:
            raise CertificateRenewalError(f"Renewal request failed: {e}") from e

        status = getattr(response, "status_code", None)
        if status is not None and status >= 400:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except Exception:
                pass
            raise CertificateRenewalError(
                f"Renewal failed (HTTP {status}): {detail}"
            )

        data = response.json()
        cert_pem = data["certificate"]
        cert_pem_bytes = cert_pem.encode() if isinstance(cert_pem, str) else cert_pem

        # Extract fingerprint and expiry from the new certificate
        x509_cert = x509.load_pem_x509_certificate(cert_pem_bytes)
        fingerprint = x509_cert.fingerprint(hashes.SHA256()).hex()

        cert = Cert(
            instance_id=self.instance_id,
            client_id=self.client_id,
            cert_pem=cert_pem_bytes,
            issued_at=datetime.now(timezone.utc),
            expires_at=x509_cert.not_valid_after_utc,
            fingerprint=fingerprint,
        )

        self.save_cert(cert)
        return cert

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    def ensure_valid_cert(self, bootstrap_key: Optional[str] = None) -> Cert:
        """Main entry point: load, renew, or bootstrap a certificate.

        Flow:
        1. Try to load existing cert from disk
        2. If no cert exists: bootstrap with bootstrap_key (required)
        3. If cert expired: bootstrap with bootstrap_key (required)
        4. If cert needs renewal (>70% TTL consumed): renew via mTLS
        5. Return valid cert

        Args:
            bootstrap_key: Bootstrap key for initial certificate acquisition

        Returns:
            Valid Cert object

        Raises:
            BootstrapKeyInvalidError: If bootstrap_key required but invalid
            CertificateExpiredError: If cert expired and no bootstrap_key
            CertificateRenewalError: If renewal fails
        """
        cert = self.load_cert()

        if cert is None or not cert.is_valid():
            # No cert or expired — need bootstrap
            if not bootstrap_key:
                if cert is not None:
                    raise CertificateExpiredError(
                        "Certificate expired. Provide bootstrap_key to re-bootstrap."
                    )
                raise BootstrapError(
                    "No certificate found. Provide bootstrap_key to bootstrap."
                )
            return self.bootstrap_cert(bootstrap_key)

        # Cert exists and is valid — check if renewal is needed
        if self.needs_renewal():
            try:
                return self.renew_cert()
            except CertificateRenewalError as e:
                logger.warning(f"Renewal failed, using existing cert: {e}")
                return cert

        return cert

    # ------------------------------------------------------------------
    # SSL context
    # ------------------------------------------------------------------

    def attach_to_context(self, ssl_context: ssl.SSLContext) -> None:
        """Attach certificate and private key to an SSL context.

        Loads cert.pem and key.pem into the SSL context for mTLS
        handshake with the cloud gateway.

        Args:
            ssl_context: SSL context to configure
        """
        cert_path = self._cert_dir / "cert.pem"
        key_path = self._cert_dir / "key.pem"

        if not cert_path.exists() or not key_path.exists():
            raise CertificateRenewalError(
                "Certificate or key not found on disk. Run ensure_valid_cert() first."
            )

        ssl_context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
        )
