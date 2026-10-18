"""The API for the fixture SQLite database, one request at a time.

The app's SQLite engine shares a single connection across threads (fine for
unit tests, wrong for a browser that fires parallel calls). Limiting the request
threadpool to one thread is not enough: the sign-in check runs on the event loop
while a request runs on the worker thread, so two calls could still use the
connection together and fail with "bad parameter or other API misuse". Here a
whole request, including its checks, finishes before the next one starts. That
makes the fixture API safe for browser E2E without changing application code.
Not used for PostgreSQL or any deployment.
"""

import asyncio

from anyio import to_thread

from app.main import app


class _OneAtATime:
    """Lets one HTTP request run from start to finish at a time."""

    def __init__(self, inner):
        self.inner = inner
        self.lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        async with self.lock:
            await self.inner(scope, receive, send)


app.add_middleware(_OneAtATime)


@app.on_event("startup")
async def _single_request_thread() -> None:
    to_thread.current_default_thread_limiter().total_tokens = 1
