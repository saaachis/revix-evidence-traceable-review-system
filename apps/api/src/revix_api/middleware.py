"""Cross-cutting behaviour that every response needs.

None of this changes what an endpoint returns. It is the layer that makes the
service observable when it is healthy, survivable when it is not, and honest
about what it will let a caller do. The three concerns live in one file
because they share a single pass over the request, and reading them together
is how you can tell what order they run in.

Order matters, and it is the reverse of the order they are added in. The
outermost middleware sees the request first and the response last, so the
timer has to be outermost: it should measure the rate limiter's work too,
otherwise a rejected request reports a duration that excludes the reason it
was rejected.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("revix.api")

Next = Callable[[Request], Awaitable[Response]]

#: Sent back on every response, and quoted in any error body. A user reporting
#: "it was slow at 14:32" is hard to act on; a user quoting a request id is a
#: single grep.
REQUEST_ID_HEADER = "X-Request-ID"

#: Milliseconds, server side, measured across the whole middleware stack. The
#: proposal commits to p95 under 300 ms, and this is what makes that claim
#: checkable from outside the process rather than only in a benchmark we ran
#: on ourselves.
RESPONSE_TIME_HEADER = "X-Response-Time-ms"

#: Static, so they can live in a constant rather than being rebuilt per
#: request. Deliberately conservative: this API returns JSON to one known
#: frontend and serves its own docs page, and nothing here needs to be
#: embeddable, sniffable, or a referrer source.
SECURITY_HEADERS = {
    # Stops a browser deciding a JSON body is really HTML and running it.
    "X-Content-Type-Options": "nosniff",
    # Nothing here should ever be framed, so clickjacking has no surface.
    "X-Frame-Options": "DENY",
    # Send the origin to other sites, never the full path. Variant ids are in
    # our paths and they do not need to travel.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # We ask for none of these, so decline them up front.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Identify and time every request, and never leak a traceback.

    The catch-all matters more than it looks. Starlette's default for an
    unhandled exception is to re-raise it: the connection closes on the caller
    with no usable body, and what reaches the log depends on the server's
    configuration rather than ours. This returns a stable JSON shape carrying
    the request id, and puts the traceback in the log where it belongs.
    """

    async def dispatch(self, request: Request, call_next: Next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "unhandled error on %s",
                request.url.path,
                extra={"request_id": request_id},
            )
            failed = JSONResponse(
                status_code=500,
                content={
                    "detail": "The server could not complete this request.",
                    "request_id": request_id,
                },
            )
            _stamp(failed, request_id, elapsed_ms)
            return failed

        elapsed_ms = (time.perf_counter() - started) * 1000
        _stamp(response, request_id, elapsed_ms)
        # One line per request, at the level the outcome deserves. A 500 that
        # only shows up in a dashboard is a 500 nobody reads.
        logger.log(
            logging.WARNING if response.status_code >= 500 else logging.INFO,
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={"request_id": request_id},
        )
        return response


def _stamp(response: Response, request_id: str, elapsed_ms: float) -> None:
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.1f}"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """The headers above, on everything, including errors."""

    async def dispatch(self, request: Request, call_next: Next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """A per-client ceiling, so one caller cannot take the service down.

    A sliding window rather than a fixed one. A fixed window lets a caller
    spend the whole allowance in the last second of one window and the whole
    allowance again in the first second of the next, which is twice the limit
    across a two-second span, and bounding that span is the entire point.

    In process and in memory, which is a real constraint and worth stating.
    Two instances would each allow the full rate, so this bounds what a single
    instance will absorb rather than enforcing a global quota. That is the
    right shape for the risk we actually have: Revix runs one container on a
    free tier, every endpoint is a read of a precomputed row, and the failure
    being prevented is one scraper walking every variant id in a loop until
    the connection pool everyone else is waiting on is exhausted. A
    distributed quota needs Redis, and adding a second network dependency to
    the read path in order to protect the read path is a bad trade at this
    size.
    """

    def __init__(self, app: object, limit: int, window_seconds: int = 60) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.limit = limit
        self.window = float(window_seconds)
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next: Next) -> Response:
        # Health checks are how the platform decides whether to keep this
        # instance alive. Rate limiting them could take the service down in
        # order to protect it, which is the wrong way round.
        if request.url.path in ("/health", "/openapi.json"):
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        cutoff = now - self.window
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(self.window - (now - hits[0])) + 1)
            request_id = getattr(request.state, "request_id", "")
            logger.warning(
                "rate limited %s on %s",
                key,
                request.url.path,
                extra={"request_id": request_id},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit of {self.limit} requests per "
                        f"{int(self.window)}s exceeded. Retry in {retry_after}s."
                    ),
                    "request_id": request_id,
                },
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        # Unbounded growth otherwise: every distinct client address would keep
        # an entry forever. Sweeping only when the table is large keeps the
        # cost off the common path.
        if len(self._hits) > 2048:
            self._sweep(cutoff)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - len(hits)))
        return response

    def _sweep(self, cutoff: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] < cutoff]:
            del self._hits[key]


def _client_key(request: Request) -> str:
    """Who to count against.

    Render terminates TLS in front of the container, so request.client is the
    proxy for every caller, and counting that would rate limit the whole world
    as a single client. The left-most X-Forwarded-For entry is the original
    address. It is also forgeable, which is acceptable here: a caller who
    forges the header to dodge the limit is a caller who could have used a
    different address anyway, and this exists to stop accidental hammering and
    one naive scraper, not a determined attacker.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
