"""청크 결과를 사람이 눈으로 보기 좋은 Markdown으로 덤프.

rag/chunks/{table}.jsonl → rag/chunks_preview/{table}.md
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IN = _REPO_ROOT / "rag" / "chunks"
_OUT = _REPO_ROOT / "rag" / "chunks_preview"

_TABLES = ["cms_board", "cms_menu_contents", "ry_info_loca"]


def _body(chunk_text: str) -> str:
    """chunk_text에서 [본문] 이후만 추출(미리보기용)."""
    marker = "[본문]\n"
    i = chunk_text.find(marker)
    return chunk_text[i + len(marker) :] if i >= 0 else chunk_text


def render(table: str) -> str:
    rows = [json.loads(ln) for ln in open(_IN / f"{table}.jsonl", encoding="utf-8")]
    lines = [f"# {table} — chunk 미리보기 ({len(rows)}개)\n"]
    cur_parent = None
    for c in rows:
        if c["parent_id"] != cur_parent:
            cur_parent = c["parent_id"]
            lines.append(f"\n---\n\n## 📄 {c.get('title') or c['source_id']}")
            lines.append(f"`{c['parent_id']}`  ·  {c.get('menu_path') or ''}\n")
        tag = "📊표" if c["is_table"] else "📝"
        hp = f"  ·  헤더: {c['header_path']}" if c.get("header_path") else ""
        sec = f"  ·  섹션: {c['section_title']}" if c.get("section_title") else ""
        lines.append(
            f"\n### {tag} `{c['chunk_id'].split(':')[-1]}` "
            f"[{c['content_type']}]{sec}{hp}"
        )
        body = _body(c["chunk_text"]).strip()
        if c["is_table"]:
            lines.append("\n" + body + "\n")
        else:
            lines.append("\n> " + body.replace("\n", "\n> ") + "\n")
    return "\n".join(lines)


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    for t in _TABLES:
        md = render(t)
        (_OUT / f"{t}.md").write_text(md, encoding="utf-8")
        print(f"  {_OUT / f'{t}.md'}  ({len(md):,} chars)")


if __name__ == "__main__":
    main()
