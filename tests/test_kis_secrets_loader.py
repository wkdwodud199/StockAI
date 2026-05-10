"""MTS_API.txt 파서 단위 테스트."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.kis.secrets_loader import parse_existing_env, parse_mts_text, render_env


SAMPLE = textwrap.dedent(
    """
    한국투자 계정
    ID: @abcdef
    PW: dummy

    실물거래
    APP KEY: REAL-APPKEY-XXXXXXXXXXXXXXXXXXXXXXXX
    APP SECRET: REAL-APPSECRET-YYYYYYYYYYYYYYYYYYYYYYYY

    모의거래(국내주식,해외주식//계좌번호: 50187113)
    APP KEY: MOCKD-APPKEY-AAAAAAAAAAAAAAAAAAAAAAAA
    APP SECRET: MOCKD-APPSECRET-BBBBBBBBBBBBBBBBBBBBBBBB

    모의거래(선물옵션//계좌번호: 60042662)
    APP KEY: MOCKF-APPKEY-CCCCCCCCCCCCCCCCCCCCCCCC
    APP SECRET: MOCKF-APPSECRET-DDDDDDDDDDDDDDDDDDDDDDDD
    """
).strip()


def test_parse_three_blocks() -> None:
    blocks = parse_mts_text(SAMPLE)
    assert set(blocks.keys()) == {"real", "mock_domestic", "mock_futures"}

    assert blocks["real"].app_key.startswith("REAL-APPKEY")
    assert blocks["real"].app_secret.startswith("REAL-APPSECRET")
    assert blocks["real"].account_no is None

    assert blocks["mock_domestic"].account_no == "50187113"
    assert blocks["mock_domestic"].app_key.startswith("MOCKD")

    assert blocks["mock_futures"].account_no == "60042662"
    assert blocks["mock_futures"].app_key.startswith("MOCKF")


def test_render_env_contains_all_keys(tmp_path: Path) -> None:
    blocks = parse_mts_text(SAMPLE)
    rendered = render_env(blocks, existing={})
    expected_keys = [
        "KIS_REAL_APP_KEY",
        "KIS_REAL_APP_SECRET",
        "KIS_MOCK_DOMESTIC_APP_KEY",
        "KIS_MOCK_DOMESTIC_APP_SECRET",
        "KIS_MOCK_DOMESTIC_ACCOUNT_NO",
        "KIS_MOCK_FUTURES_APP_KEY",
        "KIS_MOCK_FUTURES_APP_SECRET",
        "KIS_MOCK_FUTURES_ACCOUNT_NO",
        "LLM_PROVIDER",
        "REAL_MODE_PIN",
    ]
    for k in expected_keys:
        assert f"{k}=" in rendered, f"missing key {k}"

    # round-trip: write → parse_existing_env
    p = tmp_path / ".env"
    p.write_text(rendered, encoding="utf-8")
    parsed = parse_existing_env(p)
    assert parsed["KIS_MOCK_DOMESTIC_ACCOUNT_NO"] == "50187113"
    assert parsed["LLM_PROVIDER"] == "anthropic"


def test_parse_missing_section_raises() -> None:
    bad = "그냥 메모입니다. APP KEY 같은 것은 없음.\n"
    with pytest.raises(Exception):
        parse_mts_text(bad)
