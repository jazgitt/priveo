"""The Vercel Blob store: client tokens the phone uploads with, read
addresses, the size check on confirm, and the choice of store."""
import base64
import hashlib
import hmac
import io
import json
from datetime import UTC, datetime
from urllib.error import HTTPError

import pytest

from app.media import store as store_module
from app.media.store import BlobObjectStore, LocalObjectStore, get_object_store

TOKEN = "vercel_blob_rw_AbCdStore123_secretpart"
WHEN = datetime(2026, 10, 18, 6, 30, tzinfo=UTC)


def decode(client_token: str) -> tuple[str, str, dict]:
    """Splits a client token as Vercel Blob does: store ID, signature, payload."""
    prefix = "vercel_blob_client_"
    assert client_token.startswith(prefix)
    store_id, encoded = client_token[len(prefix):].split("_", 1)
    signature, payload = base64.b64decode(encoded).decode().split(".", 1)
    return store_id, signature, json.loads(base64.b64decode(payload)) | {"_raw": payload}


def test_client_token_is_signed_with_the_read_write_token_and_limits_the_upload():
    blob = BlobObjectStore(TOKEN)
    store_id, signature, payload = decode(blob.client_token("proof/u1", "video/mp4", WHEN))
    assert store_id == "AbCdStore123"
    expected = hmac.new(TOKEN.encode(), payload.pop("_raw").encode(), hashlib.sha256).hexdigest()
    assert signature == expected
    assert payload == {
        "pathname": "proof/u1", "allowedContentTypes": ["video/mp4"],
        "maximumSizeInBytes": 25 * 1024 * 1024, "validUntil": int(WHEN.timestamp() * 1000),
        "addRandomSuffix": False, "allowOverwrite": True,
    }


def test_upload_goes_straight_to_blob_with_the_token_and_the_file_type():
    signed = BlobObjectStore(TOKEN).presign_upload("u1", "proof/u1", "image/jpeg", WHEN)
    assert signed.method == "PUT"
    assert signed.url == "https://vercel.com/api/blob/?pathname=proof%2Fu1"
    assert signed.headers["authorization"].startswith("Bearer vercel_blob_client_AbCdStore123_")
    assert signed.headers["x-content-type"] == "image/jpeg"
    assert signed.headers["x-vercel-blob-access"] == "public"
    assert signed.headers["x-add-random-suffix"] == "0"


def test_read_address_is_the_public_blob_url_in_lower_case():
    url = BlobObjectStore(TOKEN).presign_download("u1", "vehicle/v1/u1", "image/jpeg", WHEN)
    assert url == "https://abcdstore123.public.blob.vercel-storage.com/vehicle/v1/u1"


def test_size_of_reads_the_blob_head_and_is_none_when_missing(monkeypatch):
    seen = {}

    def found(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.headers["Authorization"]
        return io.BytesIO(json.dumps({"size": 2048}).encode())

    monkeypatch.setattr(store_module, "urlopen", found)
    assert BlobObjectStore(TOKEN).size_of("proof/u1") == 2048
    assert seen["url"] == "https://vercel.com/api/blob/?url=proof%2Fu1"
    assert seen["auth"] == f"Bearer {TOKEN}"

    def missing(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(store_module, "urlopen", missing)
    assert BlobObjectStore(TOKEN).size_of("proof/u2") is None

    def broken(request, timeout):
        raise HTTPError(request.full_url, 500, "Error", {}, None)

    monkeypatch.setattr(store_module, "urlopen", broken)
    with pytest.raises(HTTPError):
        BlobObjectStore(TOKEN).size_of("proof/u3")


def test_a_token_that_is_not_read_write_is_refused():
    with pytest.raises(ValueError):
        BlobObjectStore("vercel_blob_client_x_y")


@pytest.mark.parametrize("token, media_store, expected", [
    (TOKEN, "", BlobObjectStore),
    (TOKEN, "local", LocalObjectStore),
    ("", "", LocalObjectStore),
])
def test_the_store_follows_the_configuration(monkeypatch, token, media_store, expected):
    monkeypatch.setattr(store_module, "_store", None)
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", token)
    monkeypatch.setenv("MEDIA_STORE", media_store)
    try:
        assert isinstance(get_object_store(), expected)
    finally:
        store_module._store = None
