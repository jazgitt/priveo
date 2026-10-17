"""Where uploaded files live. With S3 or Vercel Blob the API hands the phone a
signed upload URL and never carries the file itself. The local-disk store is
for development and tests: its URL points back at this API."""
import base64
import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.platform.config import get_settings


@dataclass(frozen=True)
class SignedUpload:
    url: str
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)


class ObjectStore(Protocol):
    def presign_upload(self, upload_id: str, key: str, content_type: str,
                       expires_at: datetime) -> SignedUpload: ...

    def presign_download(self, upload_id: str, key: str, content_type: str,
                         expires_at: datetime) -> str:
        """A URL the customer's or crew member's phone can open to read the
        stored file until `expires_at`. The signature is the only credential,
        so it is safe to hand to an image or video widget. An S3 store returns
        a pre-signed GET URL here."""
        ...

    def size_of(self, key: str) -> int | None:
        """The stored size in bytes, or None when nothing is stored."""
        ...


class LocalObjectStore:
    def __init__(self, root: Path | None = None, secret: str | None = None):
        self.root = root or Path(
            os.environ.get("MEDIA_ROOT") or Path(tempfile.gettempdir()) / "priveo-media")
        self._secret = secret

    def _key_path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("The key is outside the store.")
        return path

    def _sign(self, upload_id: str, expires: int, action: str = "") -> str:
        """The upload URL signs `id:expires`. The download URL adds a `get:`
        prefix, so neither link can be used for the other action."""
        secret = (self._secret or get_settings().token_secret).encode()
        message = f"{action}{upload_id}:{expires}".encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def presign_upload(self, upload_id: str, key: str, content_type: str,
                       expires_at: datetime) -> SignedUpload:
        expires = int(expires_at.timestamp())
        sig = self._sign(upload_id, expires)
        url = f"/v1/media/local/{upload_id}?expires={expires}&sig={sig}"
        return SignedUpload(url=url, headers={"Content-Type": content_type})

    def presign_download(self, upload_id: str, key: str, content_type: str,
                         expires_at: datetime) -> str:
        expires = int(expires_at.timestamp())
        sig = self._sign(upload_id, expires, "get:")
        return f"/v1/media/local/{upload_id}?expires={expires}&sig={sig}"

    def verify(self, upload_id: str, expires: int, sig: str, now: datetime) -> bool:
        return (now.timestamp() <= expires
                and hmac.compare_digest(self._sign(upload_id, expires), sig))

    def verify_download(self, upload_id: str, expires: int, sig: str, now: datetime) -> bool:
        return (now.timestamp() <= expires
                and hmac.compare_digest(self._sign(upload_id, expires, "get:"), sig))

    def path_of(self, key: str) -> Path | None:
        """The file on disk, or None when nothing is stored."""
        path = self._key_path(key)
        return path if path.is_file() else None

    def put(self, key: str, data: bytes) -> None:
        path = self._key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def size_of(self, key: str) -> int | None:
        path = self._key_path(key)
        return path.stat().st_size if path.is_file() else None


BLOB_API = "https://vercel.com/api/blob"
BLOB_API_VERSION = "13"


class BlobObjectStore:
    """Vercel Blob, the stand-in for S3 on the Vercel dev host. The phone
    uploads straight to Blob with a short-lived client token that allows only
    this file's path, type and size, so the file never passes through the API
    (whose requests are capped at 4.5 MB). The store is public: a file's
    address holds the upload's random ID and is the only way to find it."""

    def __init__(self, token: str, max_bytes: int = 25 * 1024 * 1024):
        parts = token.split("_")
        if len(parts) < 5 or not token.startswith("vercel_blob_rw_"):
            raise ValueError("BLOB_READ_WRITE_TOKEN is not a read-write token.")
        self._token = token
        self.store_id = parts[3]
        self._max_bytes = max_bytes

    def client_token(self, key: str, content_type: str, expires_at: datetime) -> str:
        """The same token `generateClientTokenFromReadWriteToken` of @vercel/blob
        makes: an HMAC-SHA256 of the base64 JSON payload, keyed by the
        read-write token."""
        payload = base64.b64encode(json.dumps({
            "pathname": key,
            "allowedContentTypes": [content_type],
            "maximumSizeInBytes": self._max_bytes,
            "validUntil": int(expires_at.timestamp() * 1000),
            "addRandomSuffix": False,
            # A retry after a cut-off upload writes the same path again.
            "allowOverwrite": True,
        }, separators=(",", ":")).encode()).decode()
        signature = hmac.new(self._token.encode(), payload.encode(), hashlib.sha256).hexdigest()
        signed = base64.b64encode(f"{signature}.{payload}".encode()).decode()
        return f"vercel_blob_client_{self.store_id}_{signed}"

    def presign_upload(self, upload_id: str, key: str, content_type: str,
                       expires_at: datetime) -> SignedUpload:
        return SignedUpload(
            url=f"{BLOB_API}/?{urlencode({'pathname': key})}",
            headers={
                "authorization": f"Bearer {self.client_token(key, content_type, expires_at)}",
                "x-api-version": BLOB_API_VERSION,
                "x-vercel-blob-access": "public",
                "x-content-type": content_type,
                "x-add-random-suffix": "0",
                "x-allow-overwrite": "1",
            })

    def presign_download(self, upload_id: str, key: str, content_type: str,
                         expires_at: datetime) -> str:
        # Blob reports the address with the store ID in lower case.
        return f"https://{self.store_id.lower()}.public.blob.vercel-storage.com/{key}"

    def size_of(self, key: str) -> int | None:
        request = Request(f"{BLOB_API}/?{urlencode({'url': key})}", headers={
            "authorization": f"Bearer {self._token}", "x-api-version": BLOB_API_VERSION})
        try:
            with urlopen(request, timeout=15) as response:
                return int(json.load(response)["size"])
        except HTTPError as e:
            if e.code == 404:
                return None
            raise


_store: ObjectStore | None = None


def get_object_store() -> ObjectStore:
    """The one store for this process: Vercel Blob when BLOB_READ_WRITE_TOKEN is
    set (and MEDIA_STORE is not "local"), otherwise files on local disk. A
    deployment with S3 will return an S3 store here."""
    global _store
    if _store is None:
        token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
        if token and os.environ.get("MEDIA_STORE", "").strip().lower() != "local":
            _store = BlobObjectStore(token)
        else:
            _store = LocalObjectStore()
    return _store
