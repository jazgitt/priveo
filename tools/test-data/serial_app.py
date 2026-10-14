"""The API for the fixture SQLite database, with one worker thread for requests.

The app's SQLite engine shares a single connection across threads (fine for
unit tests, wrong for a browser that fires parallel calls). Serializing the
request threadpool makes the fixture API safe for browser E2E without changing
application code. Not used for PostgreSQL or any deployment.
"""

from anyio import to_thread

from app.main import app


@app.on_event("startup")
async def _single_request_thread() -> None:
    to_thread.current_default_thread_limiter().total_tokens = 1
