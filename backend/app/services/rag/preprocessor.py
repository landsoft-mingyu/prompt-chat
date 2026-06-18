"""RAG 파이프라인 텍스트 전처리."""

import html
import re


def clean_content(text: str) -> str:
    """
    RAG 색인 전 텍스트 정제.

    1. HTML 엔티티 디코딩  (&middot; &ldquo; 등)
    2. \r\n → \n 정규화
    3. 연속 빈줄 → 최대 1줄로 압축
    4. 앞뒤 공백 제거
    """
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
