"""content_type 분류 (분석 문서 5장).

bc_id(게시판) / menu_path(메뉴) / 섹션 키워드 / 표 여부를 근거로 분류.
실데이터 라벨 우선, 추측 금지.
"""

from __future__ import annotations

# cms_board: bc_id → content_type
BC_ID_MAP = {
    "storyBoard": "story",
    "notice01": "notice",
    "magazine": "magazine",
    "video02": "video",
    "videoVr": "video",
    "qna": "qna",
    "normal1": "generic_content",
    "normal2": "generic_content",
}


def classify_board(bc_id: str | None) -> str:
    return BC_ID_MAP.get(bc_id or "", "generic_content")


def _segments(menu_path: str) -> list[str]:
    return [s for s in (menu_path or "").split(">") if s]


def classify_menu(menu_path: str | None, *, is_table: bool) -> str:
    """메뉴 페이지 content_type. 카테고리(2번째 세그먼트)+leaf+표 여부."""
    segs = _segments(menu_path)
    seg2 = segs[1] if len(segs) > 1 else ""
    leaf = segs[-1] if segs else ""
    path = menu_path or ""

    if "해설안내" in path:
        return "commentary_schedule" if is_table else "commentary_guide"
    if leaf == "관람시간":
        return "visit_hours"
    if leaf == "관람요금":
        return "visit_fee"
    if leaf == "관람규칙":
        return "visit_rules"
    if seg2 == "통합예약":
        return "reservation_guide"
    if seg2 == "행사마당":
        return "event_schedule"
    if seg2 == "기관소개":
        return "org_intro"
    if seg2 == "자료마당":
        return "culture_story"
    if seg2 == "궁능소개":
        return "palace_intro"
    return "generic_content"


# ry_info_loca: 섹션 라벨 → content_type
_RY_TRANSPORT = ("지하철", "버스", "도보", "대중교통")
_RY_PARKING = ("자가용", "주차", "내비게이션", "주차장")


def classify_ry(section_label: str | None) -> str:
    s = section_label or ""
    if s == "__overview__":
        return "location_overview"
    if any(k in s for k in _RY_PARKING):
        return "parking"
    if any(k in s for k in _RY_TRANSPORT):
        return "transportation"
    if "문의" in s or "연락" in s:
        return "contact"
    return "transportation"
