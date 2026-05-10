"""토큰 버킷 throttle 테스트."""

from __future__ import annotations

import time

import pytest

from app.kis.rate_limiter import TokenBucket


def test_capacity_allows_burst() -> None:
    # 명시적 capacity 설정 시 burst 허용 (테스트용)
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    start = time.monotonic()
    for _ in range(10):
        bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.2, f"first 10 calls within capacity should be near-instant, took {elapsed:.3f}s"


def test_throttle_when_exceeding_rate() -> None:
    # rate 4/sec, capacity 4 → 10회 호출은 첫 4회 즉시 + 6회 throttle
    # 6 / 4 = 1.5초 이상 소요되어야 함
    bucket = TokenBucket(rate=4.0, capacity=4.0)
    start = time.monotonic()
    for _ in range(10):
        bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 1.4, f"expected ≥1.4s for 10 calls @4/sec, took {elapsed:.3f}s"
    # 너무 오래 걸리면 의심 (5초 이상)
    assert elapsed < 5.0, f"too slow: {elapsed:.3f}s"


def test_acquire_more_than_capacity_raises() -> None:
    bucket = TokenBucket(rate=1.0, capacity=1.0)
    with pytest.raises(ValueError):
        bucket.acquire(2.0)
