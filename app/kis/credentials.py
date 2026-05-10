"""KIS 자격증명 로더 — .env 기반."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.kis.config import EnvConfig, KisEnvironment, get_env_config
from app.kis.exceptions import KisAuthError

_DOTENV_LOADED = False


def _ensure_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)
    _DOTENV_LOADED = True


@dataclass(frozen=True)
class KisCredentials:
    env: KisEnvironment
    app_key: str
    app_secret: str
    account_no: str
    account_product_code: str  # ACNT_PRDT_CD (예: "01" 종합매매, "03" 선물옵션)

    @property
    def account_prefix(self) -> str:
        """KIS 주문 API의 CANO. 8자리 계좌번호 그대로."""
        return self.account_no.strip()

    @property
    def account_suffix(self) -> str:
        """ACNT_PRDT_CD. credentials.account_product_code 와 동일 (호환용 alias)."""
        return self.account_product_code


def load_credentials(env: KisEnvironment) -> KisCredentials:
    """환경에 해당하는 KIS 자격증명을 .env에서 로드."""
    _ensure_dotenv()
    cfg: EnvConfig = get_env_config(env)
    app_key = os.getenv(cfg.app_key_var, "").strip()
    app_secret = os.getenv(cfg.app_secret_var, "").strip()
    account_no = os.getenv(cfg.account_no_var, "").strip()
    product_code = os.getenv(cfg.account_product_code_var, "").strip() or cfg.account_product_code_default

    missing = [
        name
        for name, val in [
            (cfg.app_key_var, app_key),
            (cfg.app_secret_var, app_secret),
            (cfg.account_no_var, account_no),
        ]
        if not val
    ]
    if missing:
        raise KisAuthError(
            f"missing credential env vars for {env.value}: {missing}. "
            "Run scripts/migrate_secrets.ps1 or fill .env manually."
        )

    return KisCredentials(
        env=env,
        app_key=app_key,
        app_secret=app_secret,
        account_no=account_no,
        account_product_code=product_code,
    )
