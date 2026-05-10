"""MTS_API.txt → .env 1회 마이그레이션 헬퍼.

원본 텍스트(`MTS_API.txt`)는 다음 블록을 포함한다:
    실물거래
    APP KEY: ...
    APP SECRET: ...

    모의거래(국내주식,해외주식//계좌번호: NNNNNNNN)
    APP KEY: ...
    APP SECRET: ...

    모의거래(선물옵션//계좌번호: NNNNNNNN)
    APP KEY: ...
    APP SECRET: ...

이 모듈은 위 패턴을 정규식으로 파싱해 .env 파일에 채워 넣는다.
원본은 별도 위치에 보관하고, 마이그레이션 후에는 삭제 권장.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import typer

from app.kis.exceptions import KisError

app = typer.Typer(no_args_is_help=True, add_completion=False)


@dataclass
class _Block:
    label: str  # 'real' | 'mock_domestic' | 'mock_futures'
    app_key: str
    app_secret: str
    account_no: str | None  # 실전은 None일 수 있음


_HEADER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # 라벨, 헤더 매처(계좌번호 캡처)
    ("real", re.compile(r"^\s*실물\s*거래\s*$", re.MULTILINE)),
    (
        "mock_domestic",
        re.compile(
            r"^\s*모의\s*거래\s*\(\s*국내주식\s*,?\s*해외주식\s*//?\s*계좌번호\s*[:：]\s*(?P<acct>\d+)\s*\)\s*$",
            re.MULTILINE,
        ),
    ),
    (
        "mock_futures",
        re.compile(
            r"^\s*모의\s*거래\s*\(\s*선물\s*옵션\s*//?\s*계좌번호\s*[:：]\s*(?P<acct>\d+)\s*\)\s*$",
            re.MULTILINE,
        ),
    ),
]

_KEY_RE = re.compile(r"^\s*APP\s*KEY\s*[:：]\s*(?P<v>\S+)\s*$", re.MULTILINE)
_SECRET_RE = re.compile(r"^\s*APP\s*SECRET\s*[:：]\s*(?P<v>\S+)\s*$", re.MULTILINE)


def parse_mts_text(text: str) -> dict[str, _Block]:
    """MTS_API.txt 본문 텍스트를 파싱해 라벨별 Block 반환."""
    # 헤더 위치 수집
    positions: list[tuple[int, str, str | None]] = []
    for label, pat in _HEADER_PATTERNS:
        for m in pat.finditer(text):
            acct = m.groupdict().get("acct") if m.groupdict() else None
            positions.append((m.start(), label, acct))
    if not positions:
        raise KisError("MTS_API.txt: 어떤 블록 헤더도 찾지 못함 (실물거래/모의거래)")
    positions.sort()

    blocks: dict[str, _Block] = {}
    for idx, (start, label, acct) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        section = text[start:end]
        key_m = _KEY_RE.search(section)
        sec_m = _SECRET_RE.search(section)
        if not key_m or not sec_m:
            raise KisError(f"MTS_API.txt: '{label}' 블록에서 APP KEY 또는 APP SECRET 누락")
        blocks[label] = _Block(
            label=label,
            app_key=key_m.group("v"),
            app_secret=sec_m.group("v"),
            account_no=acct,
        )
    return blocks


# label → (key_var, secret_var, account_var, product_code_var, default_product_code)
_ENV_KEYS_BY_LABEL: dict[str, tuple[str, str, str, str, str]] = {
    "real": (
        "KIS_REAL_APP_KEY",
        "KIS_REAL_APP_SECRET",
        "KIS_REAL_ACCOUNT_NO",
        "KIS_REAL_ACCOUNT_PRODUCT_CODE",
        "01",
    ),
    "mock_domestic": (
        "KIS_MOCK_DOMESTIC_APP_KEY",
        "KIS_MOCK_DOMESTIC_APP_SECRET",
        "KIS_MOCK_DOMESTIC_ACCOUNT_NO",
        "KIS_MOCK_DOMESTIC_ACCOUNT_PRODUCT_CODE",
        "01",
    ),
    "mock_futures": (
        "KIS_MOCK_FUTURES_APP_KEY",
        "KIS_MOCK_FUTURES_APP_SECRET",
        "KIS_MOCK_FUTURES_ACCOUNT_NO",
        "KIS_MOCK_FUTURES_ACCOUNT_PRODUCT_CODE",
        "03",
    ),
}


def render_env(blocks: dict[str, _Block], existing: dict[str, str] | None = None) -> str:
    """블록 + 기존 env 값을 합쳐 .env 본문 문자열 생성."""
    existing = dict(existing or {})
    # 자동 채움
    for label, blk in blocks.items():
        key_var, sec_var, acct_var, pcode_var, pcode_default = _ENV_KEYS_BY_LABEL[label]
        existing[key_var] = blk.app_key
        existing[sec_var] = blk.app_secret
        if acct_var and blk.account_no:
            existing[acct_var] = blk.account_no
        # 계좌상품코드는 기존값 보존, 없으면 기본값
        existing.setdefault(pcode_var, pcode_default)
    # LLM/UI 기본값 보존
    existing.setdefault("LLM_PROVIDER", "anthropic")
    existing.setdefault("ANTHROPIC_API_KEY", "")
    existing.setdefault("OPENAI_API_KEY", "")
    existing.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    existing.setdefault("REAL_MODE_PIN", "0000")
    existing.setdefault("MOBILE_API_TOKEN", "")
    existing.setdefault("API_PORT", "8765")

    order = [
        "KIS_REAL_APP_KEY",
        "KIS_REAL_APP_SECRET",
        "KIS_REAL_ACCOUNT_NO",
        "KIS_REAL_ACCOUNT_PRODUCT_CODE",
        "KIS_MOCK_DOMESTIC_APP_KEY",
        "KIS_MOCK_DOMESTIC_APP_SECRET",
        "KIS_MOCK_DOMESTIC_ACCOUNT_NO",
        "KIS_MOCK_DOMESTIC_ACCOUNT_PRODUCT_CODE",
        "KIS_MOCK_FUTURES_APP_KEY",
        "KIS_MOCK_FUTURES_APP_SECRET",
        "KIS_MOCK_FUTURES_ACCOUNT_NO",
        "KIS_MOCK_FUTURES_ACCOUNT_PRODUCT_CODE",
        "LLM_PROVIDER",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "OLLAMA_BASE_URL",
        "REAL_MODE_PIN",
        "MOBILE_API_TOKEN",
        "API_PORT",
    ]
    lines: list[str] = []
    for k in order:
        v = existing.get(k, "")
        lines.append(f"{k}={v}")
    # 순서에 없는 잔여 키
    for k, v in existing.items():
        if k not in order:
            lines.append(f"{k}={v}")
    return "\n".join(lines) + "\n"


def parse_existing_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


@app.command()
def migrate(
    src: Path = typer.Option(..., "--src", help="MTS_API.txt 경로", exists=True, readable=True),
    dest: Path = typer.Option(Path(".env"), "--dest", help=".env 출력 경로"),
) -> None:
    """MTS_API.txt 자격증명을 .env에 1회 마이그레이션."""
    text = src.read_text(encoding="utf-8")
    blocks = parse_mts_text(text)
    existing = parse_existing_env(dest)
    rendered = render_env(blocks, existing)
    dest.write_text(rendered, encoding="utf-8")
    typer.echo(f"[migrate] {len(blocks)}개 블록을 {dest}에 기록.")
    for label, blk in blocks.items():
        typer.echo(f"  - {label}: app_key={blk.app_key[:6]}... account_no={blk.account_no}")


if __name__ == "__main__":
    app()
