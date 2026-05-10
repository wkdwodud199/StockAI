"""KIS WebSocket 메시지 파서 단위 테스트."""

from __future__ import annotations

from app.kis.websocket import parse_tick_payload


# 실제 KIS 실시간 체결 응답 샘플 (암호화 0, TR_ID H0STCNT0, 1건)
# 필드 순서 (일부): MKSC_SHRN_ISCD, STCK_CNTG_HOUR, STCK_PRPR, PRDY_VRSS_SIGN,
#                   PRDY_VRSS, PRDY_CTRT, ..., (12) CNTG_VOL
_SAMPLE_TICK = (
    "0|H0STCNT0|001|005930^091500^268500^5^-3000^-1.10^268000^268500^"
    "270000^260000^268500^^^123456^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
)


def test_parse_valid_tick() -> None:
    msg = parse_tick_payload(_SAMPLE_TICK)
    assert msg is not None
    assert msg.ticker == "005930"
    assert msg.price == 268500.0
    assert msg.change == -3000.0
    assert msg.change_pct == -1.10


def test_parse_wrong_tr_id() -> None:
    msg = parse_tick_payload(_SAMPLE_TICK, tr_id="H0STASP0")
    assert msg is None


def test_parse_empty_payload() -> None:
    assert parse_tick_payload("") is None
    assert parse_tick_payload("{") is None  # JSON ack 메시지
    assert parse_tick_payload("{\"header\":\"PINGPONG\"}") is None


def test_parse_truncated_body() -> None:
    truncated = "0|H0STCNT0|001|005930^091500"
    assert parse_tick_payload(truncated) is None
