"""
접근성 평가 모듈
- 장애 유형별 접근성 점수 산출
- 카테고리 매칭
- 이동 부담도 계산
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from config import DISABILITY_PROFILES, STYLE_CATEGORY_MAP


def compute_accessibility_score(spot_data: dict, disability_type: str) -> float:
    """
    장소의 접근성 점수를 장애 유형에 맞게 계산.
    spot_data: 원본 JSON의 spot (accessibility dict 포함)
    disability_type: "보행", "시각", "청각", "지적", "유아동반", "노인"
    반환: 0.0 ~ 10.0 접근성 점수
    """
    profile = DISABILITY_PROFILES.get(disability_type)
    if not profile:
        return 5.0  # 기본 점수

    accessibility = spot_data.get("accessibility", {})
    if not accessibility:
        return 0.0  # 편의시설 정보 없음

    score = 0.0
    max_possible = 0.0
    weights = profile.get("weight", {})

    for keyword, weight in weights.items():
        max_possible += weight
        # 키워드가 accessibility 딕셔너리의 키에 있는지 확인
        for acc_key, acc_val in accessibility.items():
            if keyword in acc_key or keyword in str(acc_val):
                score += weight
                break

    # must_keywords 체크: 하나라도 없으면 감점
    must_keywords = profile.get("must_keywords", [])
    for must_kw in must_keywords:
        found = False
        for acc_key, acc_val in accessibility.items():
            if must_kw in acc_key or must_kw in str(acc_val):
                found = True
                break
        if not found:
            score *= 0.5  # 필수 키워드 없으면 50% 감점

    # 정규화: 0~10 스케일
    if max_possible > 0:
        return min(10.0, (score / max_possible) * 10.0)
    return 5.0


def compute_accessibility_score_from_metadata(metadata: dict, disability_type: str) -> float:
    """
    FAISS 검색 결과의 metadata를 이용해 접근성 점수 간이 계산.
    metadata에 has_elevator, has_ramp 등의 0/1 플래그가 있음.
    """
    profile = DISABILITY_PROFILES.get(disability_type)
    if not profile:
        return 5.0

    # 메타데이터 플래그 → 키워드 매핑
    flag_keyword_map = {
        "has_elevator": "엘리베이터",
        "has_ramp": "경사로",
        "has_braille": "점자블록",
        "has_audio_guide": "음성안내",
        "has_sign_language": "수어안내",
        "has_wheelchair_rental": "휠체어대여",
        "has_stroller_rental": "유모차대여",
        "has_nursing_room": "수유실",
        "has_disabled_toilet": "장애인화장실",
        "has_guide_dog": "보조견동반",
        "has_parking": "주차장",
        "has_baby_facility": "영유아가족기타",
    }

    weights = profile.get("weight", {})
    score = 0.0
    max_possible = sum(weights.values())

    for flag_name, keyword in flag_keyword_map.items():
        if metadata.get(flag_name, 0) == 1:
            # 이 키워드의 가중치 적용
            for w_kw, w_val in weights.items():
                if w_kw in keyword or keyword in w_kw:
                    score += w_val
                    break

    # 주출입구/대중교통은 acc_keys 문자열에서 확인
    acc_keys = metadata.get("accessibility_keys", "")
    for w_kw, w_val in weights.items():
        if w_kw in acc_keys and w_kw not in flag_keyword_map.values():
            score += w_val

    if max_possible > 0:
        return min(10.0, (score / max_possible) * 10.0)
    return 5.0


def match_travel_style(category: str, travel_style: str) -> float:
    """여행 스타일과 카테고리의 매칭 점수 (0.0~1.0)"""
    target_categories = STYLE_CATEGORY_MAP.get(travel_style, [])
    if not target_categories:
        return 0.5  # 기본 매칭
    if category in target_categories:
        return 1.0
    return 0.3  # 미스매치지만 완전 배제하지 않음


def build_rag_query(onboarding: dict) -> str:
    """온보딩 태그를 기반으로 RAG 검색 쿼리를 생성"""
    parts = []

    # 장애 유형에 따른 검색어
    disability = onboarding.get("disability_type", "")
    profile = DISABILITY_PROFILES.get(disability)
    if profile:
        parts.append(profile["description"])
        # 주요 키워드 포함
        all_keywords = profile.get("must_keywords", []) + profile.get("prefer_keywords", [])[:3]
        parts.append(" ".join(all_keywords))

    # 여행 스타일
    style = onboarding.get("travel_style", "")
    if style:
        style_cats = STYLE_CATEGORY_MAP.get(style, [])
        if style_cats:
            parts.append(f"카테고리: {', '.join(style_cats)}")
        parts.append(f"{style} 여행")

    # 동반자 정보
    companion = onboarding.get("companion", "")
    if companion:
        parts.append(f"{companion} 여행")

    # 기본 쿼리
    if not parts:
        parts.append("서울 무장애 관광지 추천")

    return " ".join(parts)
