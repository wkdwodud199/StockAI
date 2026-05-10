"""콘솔 + 파일 로거. .kis_cache/logs/kis-YYYYMMDD.log."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[2] / ".kis_cache" / "logs"


def get_logger(name: str = "kis") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            _LOG_DIR / f"{name}-{date.today():%Y%m%d}.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        # 캐시 디렉토리 생성 실패 시 콘솔만 사용
        pass

    logger.propagate = False
    return logger
