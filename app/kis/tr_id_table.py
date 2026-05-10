"""TR_ID 룩업 테이블 — KIS API는 엔드포인트 × 환경 × 매수/매도 별로 다른 TR_ID 사용.

핵심 패턴:
- 실전 prefix `T` (주식: TTTC...), 모의 prefix `V` (주식: VTTC...)
- 시세조회는 실전·모의 동일한 경우 多 (예: FHKST01010100)
- 해외/선물옵션은 별도 코드 체계
"""

from __future__ import annotations

from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError


# (operation, env) -> tr_id
_TABLE: dict[tuple[str, KisEnvironment], str] = {
    # ----- 국내 시세 (실전·모의 동일) -----
    ("domestic-quote", KisEnvironment.REAL_DOMESTIC): "FHKST01010100",
    ("domestic-quote", KisEnvironment.MOCK_DOMESTIC): "FHKST01010100",
    ("domestic-orderbook", KisEnvironment.REAL_DOMESTIC): "FHKST01010200",
    ("domestic-orderbook", KisEnvironment.MOCK_DOMESTIC): "FHKST01010200",
    ("domestic-daily", KisEnvironment.REAL_DOMESTIC): "FHKST03010100",
    ("domestic-daily", KisEnvironment.MOCK_DOMESTIC): "FHKST03010100",
    # ----- 국내 주문 -----
    ("domestic-buy", KisEnvironment.REAL_DOMESTIC): "TTTC0802U",
    ("domestic-buy", KisEnvironment.MOCK_DOMESTIC): "VTTC0802U",
    ("domestic-sell", KisEnvironment.REAL_DOMESTIC): "TTTC0801U",
    ("domestic-sell", KisEnvironment.MOCK_DOMESTIC): "VTTC0801U",
    ("domestic-cancel", KisEnvironment.REAL_DOMESTIC): "TTTC0803U",
    ("domestic-cancel", KisEnvironment.MOCK_DOMESTIC): "VTTC0803U",
    ("domestic-amend", KisEnvironment.REAL_DOMESTIC): "TTTC0803U",
    ("domestic-amend", KisEnvironment.MOCK_DOMESTIC): "VTTC0803U",
    # ----- 국내 잔고 -----
    ("balance-domestic", KisEnvironment.REAL_DOMESTIC): "TTTC8434R",
    ("balance-domestic", KisEnvironment.MOCK_DOMESTIC): "VTTC8434R",
    # ----- 해외 시세 (실전·모의 동일) -----
    ("overseas-quote", KisEnvironment.REAL_OVERSEAS): "HHDFS00000300",
    ("overseas-quote", KisEnvironment.MOCK_OVERSEAS): "HHDFS00000300",
    # ----- 해외 주문 -----
    ("overseas-buy", KisEnvironment.REAL_OVERSEAS): "TTTT1002U",
    ("overseas-buy", KisEnvironment.MOCK_OVERSEAS): "VTTT1002U",
    ("overseas-sell", KisEnvironment.REAL_OVERSEAS): "TTTT1006U",
    ("overseas-sell", KisEnvironment.MOCK_OVERSEAS): "VTTT1006U",
    # ----- 해외 잔고 -----
    ("balance-overseas", KisEnvironment.REAL_OVERSEAS): "TTTS3012R",
    ("balance-overseas", KisEnvironment.MOCK_OVERSEAS): "VTTS3012R",
    # ----- 선물옵션 (모의 전용) -----
    ("futures-quote", KisEnvironment.MOCK_FUTURES): "FHMIF10000000",
    ("futures-buy", KisEnvironment.MOCK_FUTURES): "VTTO1101U",
    ("futures-sell", KisEnvironment.MOCK_FUTURES): "VTTO1101U",
    ("balance-futures", KisEnvironment.MOCK_FUTURES): "VTFO6118R",
}


def get_tr_id(operation: str, env: KisEnvironment) -> str:
    """operation × env → TR_ID. 매핑 부재 시 KisError."""
    key = (operation, env)
    tr_id = _TABLE.get(key)
    if tr_id is None:
        # 선물옵션 실전 시도 차단
        if operation.startswith("futures-") and env is not KisEnvironment.MOCK_FUTURES:
            raise KisError(f"futures only supported in mock (got env={env.value})")
        raise KisError(f"no TR_ID mapping for operation={operation!r} env={env.value!r}")
    return tr_id


def list_operations() -> list[str]:
    """등록된 operation 이름 (중복 제거, 정렬)."""
    return sorted({op for op, _ in _TABLE.keys()})
