"""KIS 자격증명 분리(CANO + ACNT_PRDT_CD) 회귀 테스트 (collab.md High 2)."""

from __future__ import annotations

import pytest

from app.kis.config import KisEnvironment, get_env_config
from app.kis.credentials import KisCredentials, load_credentials
from app.kis.exceptions import KisAuthError


def test_credentials_dataclass_has_product_code() -> None:
    """KisCredentials는 account_product_code 필드를 가져야 함."""
    cr = KisCredentials(
        env=KisEnvironment.MOCK_DOMESTIC,
        app_key="k",
        app_secret="s",
        account_no="50187113",
        account_product_code="01",
    )
    # 회귀: account_no[:8]/[-2:] 분리는 더 이상 사용하지 않음
    assert cr.account_prefix == "50187113"
    assert cr.account_product_code == "01"
    assert cr.account_suffix == "01"  # alias 호환


def test_env_config_has_product_code_var() -> None:
    """모든 환경의 EnvConfig가 product_code_var와 default를 가져야 함."""
    for env in KisEnvironment:
        cfg = get_env_config(env)
        assert cfg.account_product_code_var.endswith("ACCOUNT_PRODUCT_CODE")
        assert cfg.account_product_code_default in {"01", "03"}


def test_futures_default_product_code_03() -> None:
    cfg = get_env_config(KisEnvironment.MOCK_FUTURES)
    assert cfg.account_product_code_default == "03"


def test_load_credentials_reads_product_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """env에서 PRODUCT_CODE를 명시적으로 읽어야 함."""
    monkeypatch.setenv("KIS_MOCK_DOMESTIC_APP_KEY", "key")
    monkeypatch.setenv("KIS_MOCK_DOMESTIC_APP_SECRET", "sec")
    monkeypatch.setenv("KIS_MOCK_DOMESTIC_ACCOUNT_NO", "50187113")
    monkeypatch.setenv("KIS_MOCK_DOMESTIC_ACCOUNT_PRODUCT_CODE", "07")

    # _ensure_dotenv 캐시 우회를 위해 직접 호출
    from app.kis import credentials as cm
    cm._DOTENV_LOADED = True  # .env 자동 로드 차단
    cr = load_credentials(KisEnvironment.MOCK_DOMESTIC)
    assert cr.account_no == "50187113"
    assert cr.account_product_code == "07"


def test_load_credentials_uses_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIS_MOCK_FUTURES_APP_KEY", "key")
    monkeypatch.setenv("KIS_MOCK_FUTURES_APP_SECRET", "sec")
    monkeypatch.setenv("KIS_MOCK_FUTURES_ACCOUNT_NO", "60042662")
    monkeypatch.delenv("KIS_MOCK_FUTURES_ACCOUNT_PRODUCT_CODE", raising=False)

    from app.kis import credentials as cm
    cm._DOTENV_LOADED = True
    cr = load_credentials(KisEnvironment.MOCK_FUTURES)
    assert cr.account_product_code == "03"  # 선물옵션 기본값


def test_missing_credentials_raises() -> None:
    """필수 자격증명이 없으면 KisAuthError raise — 회귀."""
    from app.kis import credentials as cm
    cm._DOTENV_LOADED = True
    import os
    # MOCK_FUTURES 키 모두 제거
    for k in [
        "KIS_MOCK_FUTURES_APP_KEY",
        "KIS_MOCK_FUTURES_APP_SECRET",
        "KIS_MOCK_FUTURES_ACCOUNT_NO",
    ]:
        os.environ.pop(k, None)
    with pytest.raises(KisAuthError):
        load_credentials(KisEnvironment.MOCK_FUTURES)
