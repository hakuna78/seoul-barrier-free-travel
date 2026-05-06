"""
무장애 여행 맞춤 코스 추천 엔진
- 온보딩 태그 기반 검색
- 장애 유형별 접근성 필터링 + 스코어링
- 동선 최적화 (Nearest Neighbor)
- 일정표 생성
"""
import json
import math
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from config import (
    DISABILITY_PROFILES, STYLE_CATEGORY_MAP,
    MAX_SPOTS_PER_DAY, MAX_TRAVEL_DISTANCE_KM,
    MAX_DAILY_DISTANCE_KM, MAX_DAILY_DISTANCE_ELDERLY_KM,
    SEOUL_TRAVEL_DIR,
)
from src.rag.vector_store import load_vector_store, search_spots, load_barrierfree_data
from src.recommender.accessibility import (
    compute_accessibility_score,
    compute_accessibility_score_from_metadata,
    match_travel_style,
    build_rag_query,
)
from src.recommender.transit import generate_transit_guide, find_nearest_station, get_station_accessibility_text


def haversine(lat1, lng1, lat2, lng2):
    """두 좌표 간 거리(km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _load_raw_spots_dict():
    """원본 spot 데이터를 id→spot dict로 로드"""
    spots = load_barrierfree_data()
    return {s.get("id", ""): s for s in spots}


def rank_and_filter(
    rag_results: list,
    onboarding: dict,
    raw_spots_dict: dict,
    min_accessibility_score: float = None,
) -> list:
    """
    RAG 검색 결과에 대해:
    1. 장애 유형별 접근성 점수 계산
    2. 여행 스타일 매칭 점수 계산
    3. 종합 점수로 정렬
    4. 최소 접근성 점수 미달 제거
    """
    from config import STYLE_RATIO

    disability = onboarding.get("disability_type", "")
    style = onboarding.get("travel_style", "")
    companion = onboarding.get("companion", "")

    # 장애 유형별 접근성 최소 임계값
    # 청각/지적: 편의시설 키워드 자체가 드물어 임계값을 낮춤
    if min_accessibility_score is None:
        min_accessibility_score = {
            "보행": 2.0,
            "시각": 1.5,
            "청각": 0.5,
            "지적": 0.5,
            "유아동반": 1.5,
            "노인": 1.5,
        }.get(disability, 1.0)

    # 스타일별 카테고리 허용 수 조정
    ratio_cfg = STYLE_RATIO.get(style, {})
    primary_cats = ratio_cfg.get("primary_cats", [])
    sub_cats = ratio_cfg.get("sub_cats", [])
    max_per_primary = 10   # 주요 카테고리는 넉넉히
    max_per_sub = 3        # 보조 카테고리
    max_per_other = 2      # 관련 없는 카테고리

    scored = []
    seen_categories = {}  # 카테고리별 중복 제한

    for doc in rag_results:
        meta = doc.metadata
        spot_id = meta.get("id", "")
        category = meta.get("category", "")

        # 원본 데이터에서 접근성 정보 가져와 정밀 점수 계산
        raw_spot = raw_spots_dict.get(spot_id, {})
        if raw_spot:
            acc_score = compute_accessibility_score(raw_spot, disability)
        else:
            acc_score = compute_accessibility_score_from_metadata(meta, disability)

        # 최소 접근성 점수 필터
        if acc_score < min_accessibility_score:
            continue

        # 여행 스타일 매칭
        style_score = match_travel_style(category, style) if style else 0.5

        # 동반자 관련 보너스
        companion_bonus = 0.0
        if companion in ["가족과", "혼자"] and disability in ["유아동반", "노인", "보행"]:
            if meta.get("has_disabled_toilet", 0) == 1:
                companion_bonus += 0.5
            if meta.get("has_parking", 0) == 1:
                companion_bonus += 0.3

        # 종합 점수: 접근성(60%) + 스타일(30%) + 보너스(10%)
        total_score = acc_score * 0.6 + style_score * 10 * 0.3 + companion_bonus * 0.1

        # 카테고리 중복 제한 (스타일 기반)
        cat_count = seen_categories.get(category, 0)
        if primary_cats and category in primary_cats:
            if cat_count >= max_per_primary:
                continue
        elif sub_cats and category in sub_cats:
            if cat_count >= max_per_sub:
                continue
        else:
            if cat_count >= max_per_other:
                continue
        seen_categories[category] = cat_count + 1

        scored.append({
            "doc": doc,
            "metadata": meta,
            "raw_spot": raw_spot,
            "accessibility_score": acc_score,
            "style_score": style_score,
            "total_score": total_score,
            "category": category,
        })

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def optimize_route(spots: list) -> list:
    """Nearest Neighbor로 동선 최적화"""
    if not spots:
        return []

    route = [spots[0]]
    remaining = list(spots[1:])

    while remaining:
        last = route[-1]
        lat1 = last["metadata"].get("lat", 0)
        lng1 = last["metadata"].get("lng", 0)
        nearest = min(remaining, key=lambda s: haversine(
            lat1, lng1,
            s["metadata"].get("lat", 0),
            s["metadata"].get("lng", 0),
        ))
        route.append(nearest)
        remaining.remove(nearest)

    return route


def _round5(hour: int, minute: int) -> tuple:
    """시간을 5분 단위로 반올림"""
    total = hour * 60 + minute
    total = round(total / 5) * 5
    return total // 60, total % 60


def _skip_meal_time(hour: int, minute: int, visit_min: int) -> tuple:
    """
    12:00~13:00, 18:00~19:00 식사 시간대를 건너뜀.
    해당 시간대에 걸리면 식사 시간 이후로 시작 시간을 밀어냄.
    """
    # 도착 시간 기준으로 끝나는 시간 계산
    end_total = hour * 60 + minute + visit_min

    # 12시 식사 시간대 (720~780분)
    if (hour * 60 + minute) < 720 and end_total > 720:
        # 방문이 점심에 걸침 → 13시 이후 시작
        hour, minute = 13, 0
    elif 720 <= hour * 60 + minute < 780:
        # 이미 점심 시간대 → 13시 이후
        hour, minute = 13, 0

    # 18시 식사 시간대 (1080~1140분)
    cur = hour * 60 + minute
    end_total = cur + visit_min
    if cur < 1080 and end_total > 1080:
        hour, minute = 19, 0
    elif 1080 <= cur < 1140:
        hour, minute = 19, 0

    return hour, minute


def select_spots_for_course(
    scored_spots: list,
    onboarding: dict,
    max_spots: int = None,
) -> list:
    """
    스코어링된 장소 중에서 코스에 포함할 장소 선정.
    - 여행 스타일별 주요/보조 카테고리 비율 강제
    - 구간당 최대 3km (단계적 완화 3→4→5km)
    - 장애인 기준 최대 3~4곳
    """
    from config import STYLE_RATIO

    disability = onboarding.get("disability_type", "")
    style = onboarding.get("travel_style", "")

    # 장애인 여행 기준 최대 방문 수
    if max_spots is None:
        max_spots = 4
    if disability in ["보행", "노인"]:
        max_spots = 3

    # 구간 최대 이동 거리
    MAX_LEG_KM = 3.0
    max_daily_km = MAX_DAILY_DISTANCE_KM
    if disability in ["보행", "노인"]:
        max_daily_km = MAX_DAILY_DISTANCE_ELDERLY_KM

    # ── 스타일별 비율 계산 ──
    ratio_cfg = STYLE_RATIO.get(style, {})
    primary_cats = ratio_cfg.get("primary_cats", [])
    sub_cats = ratio_cfg.get("sub_cats", [])
    sub_max = ratio_cfg.get("sub_max", 1)

    if primary_cats:
        primary_ratio = ratio_cfg.get("primary_ratio", 0.6)
        target_primary = max(1, int(round(max_spots * primary_ratio)))
        target_sub = min(sub_max, max_spots - target_primary)
    else:
        # 스타일 미지정 시 제한 없음
        target_primary = max_spots
        target_sub = max_spots

    # ── 카테고리 분류 함수 ──
    def _cat_type(cat):
        if primary_cats and cat in primary_cats:
            return "primary"
        if sub_cats and cat in sub_cats:
            return "sub"
        return "other"

    # ── 장소 선정 루프 (공용) ──
    def _try_select(spots, selected, total_distance, primary_count, sub_count, max_leg):
        selected_ids = {s["metadata"].get("id") for s in selected}
        for spot in spots:
            if len(selected) >= max_spots:
                break
            sid = spot["metadata"].get("id")
            if sid in selected_ids:
                continue

            cat = spot["metadata"].get("category", "")
            ct = _cat_type(cat)

            # 주요/보조/기타 카테고리별 제한
            if ct == "primary":
                if primary_count >= target_primary:
                    continue
            elif ct == "sub":
                if sub_count >= target_sub:
                    continue
            else:
                # 주요/보조 어디에도 해당 안 되면 스킵 (스타일 지정된 경우)
                if primary_cats:
                    continue

            # 거리 제한
            if len(selected) > 0:
                last = selected[-1]
                dist = haversine(
                    last["metadata"].get("lat", 0), last["metadata"].get("lng", 0),
                    spot["metadata"].get("lat", 0), spot["metadata"].get("lng", 0),
                )
                if dist > max_leg:
                    continue
                if total_distance + dist > max_daily_km:
                    break
                total_distance += dist

            selected.append(spot)
            selected_ids.add(sid)
            if ct == "primary":
                primary_count += 1
            elif ct == "sub":
                sub_count += 1

        return selected, total_distance, primary_count, sub_count

    selected = []
    total_distance = 0.0
    primary_count = 0
    sub_count = 0

    # 1차: 3km 제한
    selected, total_distance, primary_count, sub_count = _try_select(
        scored_spots, selected, total_distance, primary_count, sub_count, MAX_LEG_KM
    )

    # 2차: 부족하면 거리 단계적 완화 (4→5km)
    for relaxed_km in [4.0, 5.0]:
        if len(selected) >= max_spots:
            break
        selected, total_distance, primary_count, sub_count = _try_select(
            scored_spots, selected, total_distance, primary_count, sub_count, relaxed_km
        )

    return selected


def generate_schedule(route: list, start_hour: int = 10, disability_type: str = "") -> list:
    """일정표 + 구간별 교통 안내 생성 (5분 단위, 식사 시간 스킵)"""
    schedule = []
    current_hour = start_hour
    current_min = 0

    for i, spot in enumerate(route):
        meta = spot["metadata"]
        raw = spot.get("raw_spot", {})
        acc = raw.get("accessibility", {})

        # 방문 시간 (장애인 기준 넉넉하게)
        visit_min = {
            "관광지": 100, "문화시설": 80, "쇼핑": 70, "음식점": 70,
            "레포츠": 100, "숙박": 40,
        }.get(meta.get("category", ""), 80)

        # 식사 시간대 스킵 (12~13시, 18~19시)
        current_hour, current_min = _skip_meal_time(current_hour, current_min, visit_min)
        # 5분 단위 정렬
        current_hour, current_min = _round5(current_hour, current_min)

        arrival = f"{current_hour:02d}:{current_min:02d}"
        raw_end = current_min + visit_min
        end_hour = current_hour + raw_end // 60
        end_min = raw_end % 60
        # 5분 단위 정렬
        end_hour, end_min = _round5(end_hour, end_min)
        departure = f"{end_hour:02d}:{end_min:02d}"

        # 구간 교통 안내 생성
        transit_info = {}
        travel_min = 0
        travel_km = 0.0
        if i < len(route) - 1:
            next_spot = route[i + 1]
            next_meta = next_spot["metadata"]
            next_raw = next_spot.get("raw_spot", {})

            # transit 모듈로 교통 안내 생성
            from_data = {
                "lat": meta.get("lat", 0),
                "lng": meta.get("lng", 0),
                "latitude": meta.get("lat", 0),
                "longitude": meta.get("lng", 0),
                "title": meta.get("title", ""),
                "nearby_lowbus_stops": raw.get("nearby_lowbus_stops", []),
            }
            to_data = {
                "lat": next_meta.get("lat", 0),
                "lng": next_meta.get("lng", 0),
                "latitude": next_meta.get("lat", 0),
                "longitude": next_meta.get("lng", 0),
                "title": next_meta.get("title", ""),
                "nearby_lowbus_stops": next_raw.get("nearby_lowbus_stops", []),
            }
            transit_info = generate_transit_guide(
                from_data, to_data, disability_type,
                start_hour=current_hour, start_min=current_min
            )
            travel_km = transit_info.get("distance_km", 0)
            travel_min = transit_info.get("estimated_time_min", int(max(15, travel_km * 8)))

        # 접근성 요약 생성
        acc_summary = []
        for k, v in acc.items():
            acc_summary.append(f"{k}: {v[:50]}")

        # 저상버스 정보
        lowbus_info = raw.get("lowbus_text", "")

        # 가까운 지하철역
        spot_lat = float(meta.get("lat", 0))
        spot_lng = float(meta.get("lng", 0))
        nearest_stns = find_nearest_station(spot_lat, spot_lng, top_n=1)
        nearest_stn_name = nearest_stns[0][0] if nearest_stns else ""
        nearest_stn_dist = round(nearest_stns[0][1] * 1000) if nearest_stns else 0
        nearest_stn_lines = nearest_stns[0][2] if nearest_stns else []
        nearest_stn_acc = get_station_accessibility_text(nearest_stn_name) if nearest_stn_name else ""

        schedule.append({
            "order": i + 1,
            "title": meta.get("title", ""),
            "category": meta.get("category", ""),
            "address": meta.get("address", ""),
            "arrival": arrival,
            "departure": departure,
            "visit_duration_min": visit_min,
            "travel_to_next_min": travel_min,
            "travel_to_next_km": round(travel_km, 1),
            "accessibility_score": round(spot.get("accessibility_score", 0), 1),
            "style_match": round(spot.get("style_score", 0), 2),
            "total_score": round(spot.get("total_score", 0), 2),
            "accessibility_summary": acc_summary[:5],
            "lowbus_info": lowbus_info[:200] if lowbus_info else "",
            # 교통 안내
            "nearest_station": nearest_stn_name,
            "nearest_station_distance_m": nearest_stn_dist,
            "nearest_station_lines": nearest_stn_lines,
            "nearest_station_accessibility": nearest_stn_acc,
            "transit_to_next": transit_info,
            "lat": meta.get("lat", 0),
            "lng": meta.get("lng", 0),
            "image_url": meta.get("image_url", ""),
        })

        next_total = end_hour * 60 + end_min + travel_min
        current_hour = next_total // 60
        current_min = next_total % 60
        current_hour, current_min = _round5(current_hour, current_min)

    return schedule


def recommend(onboarding: dict) -> dict:
    """
    통합 추천 파이프라인

    onboarding = {
        "disability_type": "보행",    # 시각|청각|보행|지적|유아동반|노인
        "group_size": "2인",          # 1인|2인|3인|4인이상
        "companion": "가족과",        # 친구와|가족과|커플|혼자
        "travel_style": "역사/문화",  # 쇼핑|미식|힐링|역사/문화
    }
    """
    print(f"\n{'='*60}")
    print(f"[STEP 1] 온보딩 → 검색 쿼리 생성")
    query = build_rag_query(onboarding)
    print(f"  쿼리: {query}")

    print(f"\n[STEP 2] FAISS 벡터 검색 (top-50)")
    vs = load_vector_store()
    rag_results = search_spots(vs, query, k=50)
    print(f"  검색 결과: {len(rag_results)}개")
    for i, r in enumerate(rag_results[:5]):
        print(f"  {i+1}. {r.metadata['title']} [{r.metadata['category']}]")

    print(f"\n[STEP 3] 접근성 스코어링 + 필터링")
    raw_dict = _load_raw_spots_dict()
    scored = rank_and_filter(rag_results, onboarding, raw_dict)
    print(f"  접근성 필터 통과: {len(scored)}개")
    for i, s in enumerate(scored[:5]):
        print(f"  {i+1}. {s['metadata']['title']} "
              f"[접근성:{s['accessibility_score']:.1f} | 스타일:{s['style_score']:.2f} | 총점:{s['total_score']:.2f}]")

    print(f"\n[STEP 4] 코스 장소 선정 (구간 최대 5km, 최대 {4 if onboarding.get('disability_type') not in ['보행','노인'] else 3}곳)")

    # 최고 점수 장소 기준으로 반경 8km 이내 후보를 raw_dict 전체에서 확보
    from config import STYLE_RATIO
    ratio_cfg = STYLE_RATIO.get(onboarding.get("travel_style", ""), {})
    step4_primary_cats = ratio_cfg.get("primary_cats", [])
    step4_sub_cats = ratio_cfg.get("sub_cats", [])
    # 청각/지적 등 접근성 점수가 낮은 유형은 임계값을 내림
    step4_min_acc = {
        "보행": 1.0, "시각": 0.5, "청각": 0.0,
        "지적": 0.0, "유아동반": 0.5, "노인": 0.5,
    }.get(onboarding.get("disability_type", ""), 0.5)

    if scored:
        anchor_lat = scored[0]["metadata"].get("lat", 0)
        anchor_lng = scored[0]["metadata"].get("lng", 0)
        extra_candidates = []
        for sid, raw in raw_dict.items():
            # 이미 scored에 있으면 skip
            if any(s["metadata"].get("id") == sid for s in scored):
                continue
            rlat = float(raw.get("latitude", 0))
            rlng = float(raw.get("longitude", 0))
            if not rlat or not rlng:
                continue
            dist = haversine(anchor_lat, anchor_lng, rlat, rlng)
            if dist <= 8.0:
                acc_score = compute_accessibility_score(raw, onboarding.get("disability_type", ""))
                if acc_score < step4_min_acc:
                    continue
                category = raw.get("category", "")
                # 주요/보조 카테고리가 아니면 스킵 (스타일에 맞는 장소만)
                if step4_primary_cats:
                    if category not in step4_primary_cats and category not in step4_sub_cats:
                        continue
                style = onboarding.get("travel_style", "")
                style_score = match_travel_style(category, style) if style else 0.3
                total_score = acc_score * 0.5 + style_score * 10 * 0.3
                # 가짜 doc 구조로 변환
                from langchain_core.documents import Document
                fake_meta = {
                    "id": sid,
                    "title": raw.get("title", ""),
                    "category": category,
                    "address": raw.get("address", ""),
                    "lat": rlat,
                    "lng": rlng,
                    "image_url": raw.get("image_url", ""),
                }
                extra_candidates.append({
                    "doc": Document(page_content="", metadata=fake_meta),
                    "metadata": fake_meta,
                    "raw_spot": raw,
                    "accessibility_score": acc_score,
                    "style_score": style_score,
                    "total_score": total_score,
                    "category": category,
                })
        # scored 뒤에 추가 후보 병합 (중복 없이)
        print(f"  반경 8km 추가 후보: {len(extra_candidates)}개")
        scored_extended = scored + sorted(extra_candidates, key=lambda x: x["total_score"], reverse=True)
    else:
        scored_extended = scored

    selected = select_spots_for_course(scored_extended, onboarding)
    print(f"  선정: {len(selected)}개")

    print(f"\n[STEP 5] 동선 최적화")
    route = optimize_route(selected)
    for i, s in enumerate(route):
        print(f"  {i+1}. {s['metadata']['title']}")

    print(f"\n[STEP 6] 일정표 + 교통 안내 생성")
    disability = onboarding.get("disability_type", "")
    schedule = generate_schedule(route, disability_type=disability)

    # 총 이동 거리
    total_distance = sum(s["travel_to_next_km"] for s in schedule)
    total_time = sum(s["visit_duration_min"] + s["travel_to_next_min"] for s in schedule)

    result = {
        "onboarding": onboarding,
        "query": query,
        "disability_profile": DISABILITY_PROFILES.get(onboarding.get("disability_type", ""), {}),
        "total_spots": len(schedule),
        "total_distance_km": round(total_distance, 1),
        "total_time_min": total_time,
        "schedule": schedule,
    }

    print(f"\n{'='*60}")
    print(f"[결과 요약]")
    print(f"  장애 유형: {onboarding.get('disability_type', '-')}")
    print(f"  여행 스타일: {onboarding.get('travel_style', '-')}")
    print(f"  동반자: {onboarding.get('companion', '-')} ({onboarding.get('group_size', '-')})")
    print(f"  추천 장소: {len(schedule)}개")
    print(f"  총 이동 거리: {total_distance:.1f}km")
    print(f"  총 소요 시간: {total_time}분 ({total_time//60}시간 {total_time%60}분)")
    print(f"{'='*60}")

    for s in schedule:
        print(f"\n  [{s['order']}] {s['title']} ({s['category']})")
        print(f"      📍 {s.get('address', '')}")
        print(f"      시간: {s['arrival']} ~ {s['departure']} ({s['visit_duration_min']}분)")
        print(f"      접근성 점수: {s['accessibility_score']}/10")
        # 가까운 지하철역
        if s.get('nearest_station'):
            stn = s['nearest_station']
            lines = ', '.join(s.get('nearest_station_lines', []))
            dist_m = s.get('nearest_station_distance_m', 0)
            print(f"      🚇 가까운 역: {stn}역 ({lines}) - 도보 {dist_m}m")
            if s.get('nearest_station_accessibility'):
                print(f"         ♿ {s['nearest_station_accessibility']}")
        if s['accessibility_summary']:
            for line in s['accessibility_summary'][:3]:
                print(f"      ✓ {line}")
        if s['lowbus_info']:
            print(f"      🚌 {s['lowbus_info'][:120]}")
        # 다음 장소 교통 안내
        transit = s.get('transit_to_next', {})
        if transit:
            print(f"\n      {transit.get('guide_text', '')}")
            if transit.get('accessibility_note'):
                print(f"      💡 {transit['accessibility_note']}")

    return result
