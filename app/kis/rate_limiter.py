"""환경별 토큰 버킷 레이트 리미터.

- KIS 약관: 실전 ≤20 calls/sec, 모의 ≤5 calls/sec
- 본 구현: 실전 15/sec, 모의 4/sec (안전 마진)
- 환경별로 싱글톤 인스턴스를 공유하여 멀티스레드 안전.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from app.kis.config import KisEnvironment, get_env_config


@dataclass
class TokenBucket:
    """단순 토큰 버킷 — 매 초 `rate`개 토큰 충전, 최대 `capacity`개."""

    rate: float
    capacity: float
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    def acquire(self, n: float = 1.0) -> None:
        """n개 토큰을 얻을 때까지 블로킹."""
        if n > self.capacity:
            raise ValueError(f"requested {n} > capacity {self.capacity}")
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                self._last_refill = now
                if self._tokens >= n:
                    self._tokens -= n
                    return
                deficit = n - self._tokens
                wait = deficit / self.rate
            time.sleep(wait)


_BUCKETS: dict[KisEnvironment, TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()


def get_bucket(env: KisEnvironment) -> TokenBucket:
    """환경별 싱글톤 토큰 버킷.

    capacity=1로 strict 페이싱 (burst 금지). KIS 서버는 sliding-window 카운터라
    capacity>1로 burst 허용하면 서버 측 EGW00201을 트리거함.
    """
    with _BUCKETS_LOCK:
        bucket = _BUCKETS.get(env)
        if bucket is None:
            cfg = get_env_config(env)
            bucket = TokenBucket(rate=cfg.rate_per_sec, capacity=1.0)
            _BUCKETS[env] = bucket
        return bucket


def acquire(env: KisEnvironment, n: float = 1.0) -> None:
    """환경 버킷에서 토큰 n개 획득 (블로킹)."""
    get_bucket(env).acquire(n)
