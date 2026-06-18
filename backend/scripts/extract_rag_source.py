"""RAG 하이브리드 소스 추출 스크립트 (2단계).

현재 `rag/*.json`(strip 텍스트 추출본)의 id 범위를 그대로 유지하면서,
ROYAL DB 원본에서 **HTML 본문 + 누락 메타(bc_id/group_code/주소 등)** 를 보강한다.

- 범위: rag/cms_board.json(150) / cms_menu_contents.json(49) / ry_info_loca.json(25)
- 매칭: JSON id → PK
    - cms_board.id        == bd_idx
    - cms_menu_contents.id == mc_idx
      (단, `_tNN` 접미사는 탭 분할분 → 베이스 mc_idx로 조회)
    - ry_info_loca.id     == il_idx
- 출력: rag/extracted/{table}.jsonl  (파서 입력용 보강 레코드)
- DB 조작 없음 (읽기 전용 SELECT).

실행:
    cd backend && python -m scripts.extract_rag_source
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pycubrid
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# 경로
# ──────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[2]
_RAG_DIR = _REPO_ROOT / "rag"
_OUT_DIR = _RAG_DIR / "extracted"

_TAB_SUFFIX = re.compile(r"_t\d+$")


# ──────────────────────────────────────────────
# DB 연결 (ROYAL, 읽기 전용)
# ──────────────────────────────────────────────
def _connect():
    # 무관한 Settings 필수 필드에 의존하지 않도록 .env를 직접 로드
    load_dotenv(_REPO_ROOT / "backend" / ".env")
    load_dotenv(_REPO_ROOT / ".env")
    return pycubrid.connect(
        host=os.getenv("ROYAL_HOST", "192.168.12.55"),
        port=int(os.getenv("ROYAL_PORT", "33000")),
        database=os.getenv("ROYAL_DB", "royal"),
        user=os.getenv("ROYAL_USER", "royal"),
        password=os.environ["ROYAL_PASSWORD"],
    )


def _jsonable(value: Any) -> Any:
    """datetime/date → ISO 문자열."""
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _select_by_ids(
    cur, table: str, id_col: str, columns: list[str], ids: list[str]
) -> dict[str, dict]:
    """id_col IN (...) 조회 → {id_value: {col: val}}. IN 절은 50개씩 분할."""
    result: dict[str, dict] = {}
    col_sql = ", ".join(columns)
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        placeholders = ",".join(["?"] * len(batch))
        cur.execute(
            f"SELECT {id_col}, {col_sql} FROM {table} "
            f"WHERE {id_col} IN ({placeholders})",
            batch,
        )
        for row in cur.fetchall():
            key = row[0]
            result[key] = {col: _jsonable(val) for col, val in zip(columns, row[1:])}
    return result


# ──────────────────────────────────────────────
# 테이블별 추출
# ──────────────────────────────────────────────
def _load_json(name: str) -> list[dict]:
    with open(_RAG_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def extract_cms_board(cur) -> list[dict]:
    docs = _load_json("cms_board.json")
    ids = [d["id"] for d in docs]
    cols = [
        "bc_id",
        "bd_title",
        "bd_content",
        "bd_content_text",
        "bd_htmlyn",
        "bd_notice",
        "group_code",
        "bd_writer",
        "bd_thumb1",
        "bd_thumb2",
        "bd_thumb3",
        "regdt",
        "upddt",
    ]
    db = _select_by_ids(cur, "cms_board", "bd_idx", cols, ids)

    out: list[dict] = []
    for d in docs:
        row = db.get(d["id"])
        if row is None:
            out.append({**_base(d), "_missing": True})
            continue
        out.append(
            {
                **_base(d),
                "source_id": d["id"],
                "tab_key": None,
                "content_text": d.get("content") or row.get("bd_content_text") or "",
                "content_html": row.get("bd_content") or "",
                "db": {
                    "bc_id": row.get("bc_id"),
                    "bd_htmlyn": row.get("bd_htmlyn"),
                    "bd_notice": row.get("bd_notice"),
                    "group_code": row.get("group_code"),
                    "bd_writer": row.get("bd_writer"),
                    "bd_title": row.get("bd_title"),
                    "thumbs": [
                        row.get("bd_thumb1"),
                        row.get("bd_thumb2"),
                        row.get("bd_thumb3"),
                    ],
                    "regdt": row.get("regdt"),
                    "upddt": row.get("upddt"),
                },
            }
        )
    return out


def extract_cms_menu_contents(cur) -> list[dict]:
    docs = _load_json("cms_menu_contents.json")
    # _tNN 접미사 제거 → 베이스 mc_idx
    base_of = {d["id"]: _TAB_SUFFIX.sub("", d["id"]) for d in docs}
    base_ids = sorted(set(base_of.values()))
    cols = ["mc_content", "menu_code", "regdt", "upddt"]
    db = _select_by_ids(cur, "cms_menu_contents", "mc_idx", cols, base_ids)

    out: list[dict] = []
    for d in docs:
        base = base_of[d["id"]]
        row = db.get(base)
        suffix = _TAB_SUFFIX.search(d["id"])
        tab_key = suffix.group(0).lstrip("_") if suffix else None
        if row is None:
            out.append({**_base(d), "_missing": True})
            continue
        out.append(
            {
                **_base(d),
                "source_id": base,  # 베이스 행 PK
                "tab_key": tab_key,  # 't01' 등 (탭 분할분), 없으면 None
                "tab_label": d["metadata"].get("menu_path", "").split(">")[-1] or None,
                "content_text": d.get("content") or "",
                "content_html": row.get("mc_content") or "",
                "db": {
                    "menu_code": row.get("menu_code"),
                    "regdt": row.get("regdt"),
                    "upddt": row.get("upddt"),
                },
            }
        )
    return out


def extract_ry_info_loca(cur) -> list[dict]:
    docs = _load_json("ry_info_loca.json")
    ids = [d["id"] for d in docs]
    cols = [
        "title",
        "group_code",
        "regwriter",
        "addrs",
        "tel_no",
        "tel_fax",
        "loca_url",
        "content",
        "disp_yn",
        "disp_sdt",
        "disp_edt",
    ]
    db = _select_by_ids(cur, "ry_info_loca", "il_idx", cols, ids)

    out: list[dict] = []
    for d in docs:
        row = db.get(d["id"])
        if row is None:
            out.append({**_base(d), "_missing": True})
            continue
        out.append(
            {
                **_base(d),
                "source_id": d["id"],
                "tab_key": None,
                "content_text": d.get("content") or row.get("content") or "",
                "content_html": row.get("content") or "",  # ry는 대체로 평문
                "db": {
                    "title": row.get("title"),
                    "group_code": row.get("group_code"),
                    "addrs": row.get("addrs"),
                    "tel_no": row.get("tel_no"),
                    "tel_fax": row.get("tel_fax"),
                    "loca_url": row.get("loca_url"),
                    "regwriter": row.get("regwriter"),
                    "disp_yn": row.get("disp_yn"),
                    "disp_sdt": row.get("disp_sdt"),
                    "disp_edt": row.get("disp_edt"),
                },
            }
        )
    return out


def _base(d: dict) -> dict:
    """JSON 원본 식별/메타 보존."""
    return {
        "id": d["id"],
        "source_table": d["source_table"],
        "site_code": d["metadata"].get("site_code", "ROYAL"),
        "metadata": d["metadata"],
    }


# ──────────────────────────────────────────────
# 출력 + 통계
# ──────────────────────────────────────────────
def _write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _stats(name: str, records: list[dict]) -> None:
    total = len(records)
    missing = sum(1 for r in records if r.get("_missing"))
    has_html = sum(1 for r in records if r.get("content_html", "").strip())
    has_table = sum(1 for r in records if "<table" in r.get("content_html", "").lower())
    tab_split = sum(1 for r in records if r.get("tab_key"))
    print(f"\n[{name}] {total} records")
    print(f"  matched={total - missing}  missing={missing}")
    print(
        f"  content_html 보유={has_html}  <table> 포함={has_table}  "
        f"탭분할(_tNN)={tab_split}"
    )
    if name == "cms_board":
        from collections import Counter

        bc = Counter(r["db"]["bc_id"] for r in records if not r.get("_missing"))
        hy = Counter(r["db"]["bd_htmlyn"] for r in records if not r.get("_missing"))
        print(f"  bc_id={dict(bc)}  bd_htmlyn={dict(hy)}")
    if missing:
        print("  MISSING ids:", [r["id"] for r in records if r.get("_missing")][:20])


def main() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        try:
            extractors = [
                ("cms_board", extract_cms_board),
                ("cms_menu_contents", extract_cms_menu_contents),
                ("ry_info_loca", extract_ry_info_loca),
            ]
            for name, fn in extractors:
                records = fn(cur)
                _write_jsonl(records, _OUT_DIR / f"{name}.jsonl")
                _stats(name, records)
            print(f"\n출력 위치: {_OUT_DIR}")
        finally:
            cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
