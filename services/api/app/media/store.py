"""Where uploaded files live. With S3 the API hands the phone a signed upload
URL and never carries the file itself. The local-disk store is for
development and tests: its URL points back at this API."""
import hashlib
import hmac
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

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


_store: LocalObjectStore | None = None


def get_object_store() -> ObjectStore:
    """The one store for this process. A deployment with S3 returns an S3
    store here, chosen by configuration."""
    global _store
    if _store is None:
        _store = LocalObjectStore()
    return _store
