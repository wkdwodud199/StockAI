"""공통 경로 상수 (다른 모듈의 import 사이클 회피용)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
KIS_CACHE_DIR: Path = PROJECT_ROOT / ".kis_cache"
