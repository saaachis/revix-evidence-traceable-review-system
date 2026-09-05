"""Rate limiting, backoff, robots checking and the circuit breaker.

None of this is optional and none of it belongs in a connector. It lives here
so that "be polite to the source" is a property of the framework rather than
something each connector's author has to remember.
"""

from __future__ import annotations

import threading
import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from revix_core.settings import get_settings


class CircuitOpenError(RuntimeError):
    """Raised when a source has refused us often enough that we stop asking."""


class RobotsDisallowedError(RuntimeError):
    """Raised when robots.txt says this path is not for us."""


class TokenBucket:
    """Requests per minute, smoothed.

    A bucket rather than a fixed sleep, so a connector can burst a little
    after an idle period without ever exceeding the average rate.
    """

    def __init__(self, rate_per_minute: int, capacity: int | None = None) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = float(capacity if capacity is not None else max(1, rate_per_minute // 4))
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(
            self.capacity, self._tokens + (now - self._updated) * self.rate_per_second
        )
        self._updated = now

    def acquire(self, *, sleep: bool = True) -> float:
        """Take one token. Returns how long it waited."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return 0.0
            deficit = 1.0 - self._tokens
            wait = deficit / self.rate_per_second
            self._tokens = 0.0
            self._updated = time.monotonic() + wait
        if sleep:
            time.sleep(wait)
        return wait


@dataclass
class CircuitBreaker:
    """Stop asking a source that keeps refusing.

    Continuing to hammer a site returning 403 is both useless and rude. After
    `threshold` consecutive failures the breaker opens and every further call
    fails immediately, until `reset_after` seconds have passed.
    """

    threshold: int = 5
    reset_after: float = 900.0
    failures: int = 0
    opened_at: float | None = field(default=None)

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= self.reset_after:
            # Half-open: allow one attempt through to see if it recovered.
            self.opened_at = None
            self.failures = self.threshold - 1
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold and self.opened_at is None:
            self.opened_at = time.monotonic()

    def check(self, source_key: str) -> None:
        if self.is_open:
            raise CircuitOpenError(
                f"circuit open for '{source_key}' after {self.failures} consecutive failures"
            )


class RobotsCache:
    """One robots.txt lookup per host, cached for the life of the run."""

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def allows(self, url: str, *, client: httpx.Client | None = None) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._parsers:
            self._parsers[origin] = self._load(origin, client)
        parser = self._parsers[origin]
        if parser is None:
            # No robots.txt, or it could not be read. Absence is permission,
            # but we still stay inside the configured rate limit.
            return True
        return parser.can_fetch(self.user_agent, url)

    def _load(
        self, origin: str, client: httpx.Client | None
    ) -> urllib.robotparser.RobotFileParser | None:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        try:
            owns_client = client is None
            client = client or httpx.Client(timeout=10.0, follow_redirects=True)
            try:
                response = client.get(f"{origin}/robots.txt")
            finally:
                if owns_client:
                    client.close()
            if response.status_code >= 400:
                return None
            parser.parse(response.text.splitlines())
            return parser
        except Exception:
            return None


class PoliteClient:
    """An HTTP client that cannot be impolite by accident.

    Every request goes through the rate limiter, is checked against robots,
    is retried with exponential backoff on transient failures, and trips the
    circuit breaker on persistent ones.
    """

    RETRYABLE = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)

    def __init__(
        self,
        source_key: str,
        *,
        rate_limit_rpm: int | None = None,
        respect_robots: bool = True,
        timeout: float | None = None,
        breaker: CircuitBreaker | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        settings = get_settings()
        self.source_key = source_key
        self.respect_robots = respect_robots
        self.bucket = TokenBucket(rate_limit_rpm or settings.default_rate_limit_rpm)
        self.breaker = breaker or CircuitBreaker()
        self.robots = RobotsCache(settings.user_agent)
        self._client = httpx.Client(
            timeout=timeout or settings.default_request_timeout_s,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent, **(headers or {})},
        )

    def set_header(self, name: str, value: str) -> None:
        """For a bearer token obtained after the client was built."""
        self._client.headers[name] = value

    def get(self, url: str, **kwargs: object) -> httpx.Response:
        return self._request("GET", url, kwargs, check_robots=True)

    def post(self, url: str, **kwargs: object) -> httpx.Response:
        """Only for authentication handshakes.

        Nothing in this project writes to a source. A POST here is an OAuth
        token exchange and nothing else, which is also why robots is not
        consulted for it: robots.txt governs crawlers, and a client presenting
        credentials to a documented API endpoint is not crawling.
        """
        return self._request("POST", url, kwargs, check_robots=False)

    def _request(
        self, method: str, url: str, kwargs: dict[str, object], *, check_robots: bool
    ) -> httpx.Response:
        self.breaker.check(self.source_key)
        if (
            check_robots
            and self.respect_robots
            and not self.robots.allows(url, client=self._client)
        ):
            raise RobotsDisallowedError(f"robots.txt disallows {url}")
        self.bucket.acquire()
        try:
            response = self._fetch(method, url, kwargs)
        except Exception:
            self.breaker.record_failure()
            raise
        # 4xx that is not rate limiting means the source is refusing us, and
        # retrying will not change that. Count it against the breaker.
        if response.status_code in (401, 403, 451) or response.status_code == 429:
            self.breaker.record_failure()
        else:
            self.breaker.record_success()
        return response

    @retry(
        retry=retry_if_exception_type(RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _fetch(self, method: str, url: str, kwargs: dict[str, object]) -> httpx.Response:
        return self._client.request(method, url, **kwargs)  # type: ignore[arg-type]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
