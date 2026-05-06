from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request, limit: int, window_seconds: int) -> None:
        if limit <= 0 or window_seconds <= 0:
            return

        client = request.client.host if request.client else "unknown"
        now = monotonic()
        hits = self._hits[client]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()

        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many unwrap attempts",
            )
        hits.append(now)
