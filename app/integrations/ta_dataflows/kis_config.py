"""KIS dataflow 어댑터 설정.

본 모듈은 `app.integrations.ta_dataflows.kis_api`가 사용. TradingAgents 코어를
수정하지 않고 import-time 패치로 dataflows에 등록된다 (ta_kis_patch.py 참고).
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_KIS_ENV_NAME: str = os.getenv("KIS_TA_ENV", "mock_domestic")

# CSV 캐시 디렉토리 (gitignored)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # app/integrations/ta_dataflows/ → project root
_DEFAULT_CACHE = _PROJECT_ROOT / ".kis_cache" / "ta_csv"
KIS_CSV_CACHE_DIR: Path = Path(os.getenv("KIS_TA_CACHE_DIR", str(_DEFAULT_CACHE)))


def ensure_cache_dir() -> Path:
    KIS_CSV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return KIS_CSV_CACHE_DIR
