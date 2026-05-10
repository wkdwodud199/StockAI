"""KIS 환경 정의 — 실전/모의/선물옵션 라우팅."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KisEnvironment(str, Enum):
    """지원하는 KIS API 환경."""

    REAL_DOMESTIC = "real_domestic"
    REAL_OVERSEAS = "real_overseas"
    MOCK_DOMESTIC = "mock_domestic"
    MOCK_OVERSEAS = "mock_overseas"
    MOCK_FUTURES = "mock_futures"

    @property
    def is_mock(self) -> bool:
        return self.value.startswith("mock_")

    @property
    def is_real(self) -> bool:
        return self.value.startswith("real_")

    @property
    def is_overseas(self) -> bool:
        return self.value.endswith("_overseas")

    @property
    def is_futures(self) -> bool:
        return self.value.endswith("_futures")


_REAL_HOST = "https://openapi.koreainvestment.com:9443"
_MOCK_HOST = "https://openapivts.koreainvestment.com:29443"
_REAL_WS = "ws://ops.koreainvestment.com:21000"
_MOCK_WS = "ws://ops.koreainvestment.com:31000"


@dataclass(frozen=True)
class EnvConfig:
    """환경별 라우팅 정보."""

    env: KisEnvironment
    base_url: str
    websocket_url: str
    rate_per_sec: float
    app_key_var: str
    app_secret_var: str
    account_no_var: str
    # KIS 계좌상품코드 (CANO + ACNT_PRDT_CD 분리). 종합매매=01, 선물옵션=03 등.
    account_product_code_var: str
    account_product_code_default: str

    @property
    def cred_group(self) -> str:
        """실전 1쌍, 모의 국내/해외 1쌍, 모의 선물옵션 1쌍 — 자격증명 키쌍 그룹."""
        if self.env is KisEnvironment.REAL_DOMESTIC or self.env is KisEnvironment.REAL_OVERSEAS:
            return "real"
        if self.env is KisEnvironment.MOCK_FUTURES:
            return "mock_futures"
        return "mock_domestic"


_CONFIGS: dict[KisEnvironment, EnvConfig] = {
    KisEnvironment.REAL_DOMESTIC: EnvConfig(
        env=KisEnvironment.REAL_DOMESTIC,
        base_url=_REAL_HOST,
        websocket_url=_REAL_WS,
        rate_per_sec=15.0,
        app_key_var="KIS_REAL_APP_KEY",
        app_secret_var="KIS_REAL_APP_SECRET",
        account_no_var="KIS_REAL_ACCOUNT_NO",
        account_product_code_var="KIS_REAL_ACCOUNT_PRODUCT_CODE",
        account_product_code_default="01",
    ),
    KisEnvironment.REAL_OVERSEAS: EnvConfig(
        env=KisEnvironment.REAL_OVERSEAS,
        base_url=_REAL_HOST,
        websocket_url=_REAL_WS,
        rate_per_sec=15.0,
        app_key_var="KIS_REAL_APP_KEY",
        app_secret_var="KIS_REAL_APP_SECRET",
        account_no_var="KIS_REAL_ACCOUNT_NO",
        account_product_code_var="KIS_REAL_ACCOUNT_PRODUCT_CODE",
        account_product_code_default="01",
    ),
    KisEnvironment.MOCK_DOMESTIC: EnvConfig(
        env=KisEnvironment.MOCK_DOMESTIC,
        base_url=_MOCK_HOST,
        websocket_url=_MOCK_WS,
        rate_per_sec=4.0,
        app_key_var="KIS_MOCK_DOMESTIC_APP_KEY",
        app_secret_var="KIS_MOCK_DOMESTIC_APP_SECRET",
        account_no_var="KIS_MOCK_DOMESTIC_ACCOUNT_NO",
        account_product_code_var="KIS_MOCK_DOMESTIC_ACCOUNT_PRODUCT_CODE",
        account_product_code_default="01",
    ),
    KisEnvironment.MOCK_OVERSEAS: EnvConfig(
        env=KisEnvironment.MOCK_OVERSEAS,
        base_url=_MOCK_HOST,
        websocket_url=_MOCK_WS,
        rate_per_sec=4.0,
        # 모의 해외주식은 모의 국내와 동일 자격 사용 (KIS 정책)
        app_key_var="KIS_MOCK_DOMESTIC_APP_KEY",
        app_secret_var="KIS_MOCK_DOMESTIC_APP_SECRET",
        account_no_var="KIS_MOCK_DOMESTIC_ACCOUNT_NO",
        account_product_code_var="KIS_MOCK_DOMESTIC_ACCOUNT_PRODUCT_CODE",
        account_product_code_default="01",
    ),
    KisEnvironment.MOCK_FUTURES: EnvConfig(
        env=KisEnvironment.MOCK_FUTURES,
        base_url=_MOCK_HOST,
        websocket_url=_MOCK_WS,
        rate_per_sec=4.0,
        app_key_var="KIS_MOCK_FUTURES_APP_KEY",
        app_secret_var="KIS_MOCK_FUTURES_APP_SECRET",
        account_no_var="KIS_MOCK_FUTURES_ACCOUNT_NO",
        account_product_code_var="KIS_MOCK_FUTURES_ACCOUNT_PRODUCT_CODE",
        account_product_code_default="03",
    ),
}


def get_env_config(env: KisEnvironment) -> EnvConfig:
    return _CONFIGS[env]


def parse_env(value: str) -> KisEnvironment:
    """문자열 → KisEnvironment 변환 (CLI 인자용)."""
    normalized = value.lower().replace("-", "_")
    try:
        return KisEnvironment(normalized)
    except ValueError as exc:
        valid = ", ".join(e.value for e in KisEnvironment)
        raise ValueError(f"unknown env '{value}'. valid: {valid}") from exc
