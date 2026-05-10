"""KIS 클라이언트 예외 계층."""

from __future__ import annotations


class KisError(Exception):
    """모든 KIS 관련 오류의 베이스."""


class KisAuthError(KisError):
    """OAuth 토큰 발급 실패 또는 401 응답 후 재시도 실패."""


class KisRateLimitError(KisError):
    """레이트 리미터 초과 또는 EGW00201 응답."""


class KisHttpError(KisError):
    """HTTP 4xx/5xx (인증/레이트 제외)."""

    def __init__(self, status: int, body: str, message: str | None = None) -> None:
        self.status = status
        self.body = body
        super().__init__(message or f"HTTP {status}: {body[:200]}")


class KisOrderRejected(KisError):
    """주문이 KIS에 의해 거부됨 (rt_cd != '0')."""

    def __init__(self, msg_cd: str, msg: str) -> None:
        self.msg_cd = msg_cd
        self.msg = msg
        super().__init__(f"[{msg_cd}] {msg}")
