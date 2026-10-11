"""Serves the built admin portal at /portal/ from the same origin as the API.

The Vite build is copied to `services/api/portal` before the deploy (see
.github/workflows/api-deploy.yml). A file that exists is sent as it is. A path
with no file extension is a page of the single-page app, so it gets
index.html and the browser router takes over. A missing file with an
extension is a real 404."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, Response

from app.platform.errors import ApiError

PORTAL_DIR = Path(__file__).resolve().parents[2] / "portal"

router = APIRouter(include_in_schema=False)

_IMMUTABLE = "public, max-age=31536000, immutable"
_REVALIDATE = "no-cache"


def _not_built() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"code": "portal_not_built",
                 "message": "The admin portal is not part of this deployment.",
                 "fields": {}, "request_id": ""})


def _index() -> Response:
    index = PORTAL_DIR / "index.html"
    if not index.is_file():
        return _not_built()
    return FileResponse(index, media_type="text/html",
                        headers={"Cache-Control": _REVALIDATE})


@router.get("/portal")
def portal_root_redirect() -> Response:
    # The app is built for the /portal/ base, so the slash matters.
    return Response(status_code=308, headers={"Location": "/portal/"})


@router.get("/portal/")
def portal_index() -> Response:
    return _index()


@router.get("/portal/{path:path}")
def portal_file(path: str) -> Response:
    root = PORTAL_DIR.resolve()
    target = (root / path).resolve()
    if root in target.parents and target.is_file():
        cache = _IMMUTABLE if target.relative_to(root).parts[0] == "assets" else _REVALIDATE
        return FileResponse(target, headers={"Cache-Control": cache})
    if "." in path.rsplit("/", 1)[-1]:
        raise ApiError("not_found", "Not found.", 404)
    return _index()
