"""TR_ID 라우팅 단위 테스트."""

from __future__ import annotations

import pytest

from app.kis.config import KisEnvironment
from app.kis.exceptions import KisError
from app.kis.tr_id_table import get_tr_id, list_operations


def test_domestic_buy_real_vs_mock() -> None:
    assert get_tr_id("domestic-buy", KisEnvironment.REAL_DOMESTIC) == "TTTC0802U"
    assert get_tr_id("domestic-buy", KisEnvironment.MOCK_DOMESTIC) == "VTTC0802U"


def test_domestic_quote_same_in_both() -> None:
    real = get_tr_id("domestic-quote", KisEnvironment.REAL_DOMESTIC)
    mock = get_tr_id("domestic-quote", KisEnvironment.MOCK_DOMESTIC)
    assert real == mock == "FHKST01010100"


def test_overseas_sell_distinct() -> None:
    assert get_tr_id("overseas-sell", KisEnvironment.REAL_OVERSEAS) == "TTTT1006U"
    assert get_tr_id("overseas-sell", KisEnvironment.MOCK_OVERSEAS) == "VTTT1006U"


def test_futures_only_in_mock_env() -> None:
    # 모의 선물옵션은 OK
    assert get_tr_id("futures-buy", KisEnvironment.MOCK_FUTURES).startswith("V")
    # 실전 선물옵션은 명시적으로 거부
    with pytest.raises(KisError, match="futures only supported in mock"):
        get_tr_id("futures-buy", KisEnvironment.REAL_DOMESTIC)


def test_unknown_operation_raises() -> None:
    with pytest.raises(KisError, match="no TR_ID mapping"):
        get_tr_id("nonsense-op", KisEnvironment.MOCK_DOMESTIC)


def test_list_operations_contains_core() -> None:
    ops = set(list_operations())
    for must in [
        "domestic-quote",
        "domestic-buy",
        "domestic-sell",
        "balance-domestic",
        "overseas-quote",
        "futures-buy",
    ]:
        assert must in ops
