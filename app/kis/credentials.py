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
    # 프로젝트 루트의 .env 자동 로드 (이미 셋된 환경변수는 덮어쓰지 않음)
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)
    _DOTENV_LOADED = True


@dataclass(frozen=True)
class KisCredentials:
    env: KisEnvironment
    app_key: str
    app_secret: str
    account_no: str

    @property
    def account_prefix(self) -> str:
        """KIS 주문 API의 CANO (계좌 앞 8자리)."""
        return self.account_no[:8] if len(self.account_no) >= 8 else self.account_no

    @property
    def account_suffix(self) -> str:
        """KIS 주문 API의 ACNT_PRDT_CD (계좌 뒤 2자리)."""
        return self.account_no[-2:] if len(self.account_no) >= 2 else "01"


def load_credentials(env: KisEnvironment) -> KisCredentials:
    """환경에 해당하는 KIS 자격증명을 .env에서 로드."""
    _ensure_dotenv()
    cfg: EnvConfig = get_env_config(env)
    app_key = os.getenv(cfg.app_key_var, "").strip()
    app_secret = os.getenv(cfg.app_secret_var, "").strip()
    account_no = os.getenv(cfg.account_no_var, "").strip()

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
    )
