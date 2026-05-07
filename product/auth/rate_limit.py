import time
from collections import defaultdict, deque
from json import dumps
from typing import Protocol

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.logger import get_logger


LOGIN_RATE_LIMIT = "5/15minutes"
UPLOAD_RATE_LIMIT = "10/hour"

logger = get_logger(__name__)


class RateLimitBackend(Protocol):
    def hit(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        ...


class InMemoryRateLimitBackend:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self._attempts[key]
        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()
        if len(bucket) >= max_attempts:
            return False
        bucket.append(now)
        return True


_memory_backend = InMemoryRateLimitBackend()


def _get_backend() -> RateLimitBackend:
    storage_uri = get_settings().RATE_LIMIT_STORAGE_URI
    if storage_uri.startswith("memory://"):
        return _memory_backend
    return _memory_backend


def _parse_limit(limit: str) -> tuple[int, int]:
    count, window = limit.split("/", 1)
    if window.endswith("minutes"):
        seconds = int(window.removesuffix("minutes")) * 60
    elif window.endswith("minute"):
        amount = window.removesuffix("minute")
        seconds = int(amount or "1") * 60
    elif window.endswith("hours"):
        seconds = int(window.removesuffix("hours")) * 3600
    elif window.endswith("hour"):
        amount = window.removesuffix("hour")
        seconds = int(amount or "1") * 3600
    else:
        raise ValueError(f"Unsupported rate limit window: {window}")
    return int(count), seconds


def check_rate_limit(
    key: str,
    limit: str,
    user_id: str | None = None,
    action: str = "RATE_LIMITED",
    db: Session | None = None,
) -> None:
    max_attempts, window_seconds = _parse_limit(limit)
    backend = _get_backend()
    now = time.time()
    bucket = getattr(backend, "_attempts", {}).get(key)
    if not backend.hit(key, max_attempts, window_seconds):
        if db is not None:
            db.execute(
                text(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata)
                    VALUES (:user_id, :action, 'rate_limit', :entity_id, CAST(:metadata AS JSONB))
                    """
                ),
                {
                    "user_id": user_id,
                    "action": action,
                    "entity_id": key,
                    "metadata": dumps({"key": key, "limit": limit}),
                },
            )
        logger.warning(
            "rate_limited",
            action=action,
            user_id=user_id,
            key=key,
            limit=limit,
        )
        raise HTTPException(status_code=429, detail="Too many requests")
    if bucket is not None and (not bucket or bucket[-1] != now):
        pass


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_login_rate_limit(request: Request, db: Session | None = None) -> None:
    check_rate_limit(
        key=f"login:{get_client_ip(request)}",
        limit=LOGIN_RATE_LIMIT,
        action="RATE_LIMITED",
        db=db,
    )


def check_upload_rate_limit(user_id: str, db: Session | None = None) -> None:
    check_rate_limit(
        key=f"upload:{user_id}",
        limit=UPLOAD_RATE_LIMIT,
        user_id=user_id,
        action="RATE_LIMITED",
        db=db,
    )
