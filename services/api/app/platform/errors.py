import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("priveo.api")


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: dict[str, str] = {}
    request_id: str = ""


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400,
                 fields: dict[str, str] | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


def _response(request: Request, status: int, code: str, message: str,
              fields: dict[str, str] | None = None) -> JSONResponse:
    body = ErrorBody(code=code, message=message, fields=fields or {},
                     request_id=getattr(request.state, "request_id", ""))
    return JSONResponse(status_code=status, content=body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _response(request, exc.status, exc.code, exc.message, exc.fields)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        fields = {".".join(str(p) for p in e["loc"][1:]): e["msg"] for e in exc.errors()}
        return _response(request, 422, "validation_failed", "Please check the details.", fields)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"
        return _response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return _response(request, 500, "internal_error",
                         "Something went wrong. Please try again.")
