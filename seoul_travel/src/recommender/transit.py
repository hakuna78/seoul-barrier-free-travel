"""
교통 안내 모듈
- 관광지 간 교통 수단 추천
- 지하철역 접근성 정보 (엘리베이터/에스컬레이터)
- 저상버스 노선 안내
"""
import json
import math
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from config import SEOUL_TRAVEL_DIR

# ── 서울 지하철 주요역 좌표 (교통 경로 추정용) ──
# 실제 운영 시 별도 DB 사용. 여기서는 주요역 100개 좌표를 하드코딩
SUBWAY_STATIONS = {
    "서울역": (37.5547, 126.9707, ["1호선","4호선","경의중앙선"]),
    "시청": (37.5641, 126.9773, ["1호선","2호선"]),
    "종각": (37.5700, 126.9826, ["1호선"]),
    "종로3가": (37.5710, 126.9916, ["1호선","3호선","5호선"]),
    "종로5가": (37.5710, 126.9984, ["1호선"]),
    "동대문": (37.5710, 127.0094, ["1호선","4호선"]),
    "동묘앞": (37.5714, 127.0158, ["1호선","6호선"]),
    "신설동": (37.5752, 127.0250, ["1호선","2호선"]),
    "제기동": (37.5804, 127.0362, ["1호선"]),
    "청량리": (37.5808, 127.0467, ["1호선","경의중앙선"]),
    "을지로입구": (37.5660, 126.9824, ["2호선"]),
    "을지로3가": (37.5665, 126.9916, ["2호선","3호선"]),
    "을지로4가": (37.5665, 126.9980, ["2호선","5호선"]),
    "동대문역사문화공원": (37.5653, 127.0074, ["2호선","4호선","5호선"]),
    "신당": (37.5658, 127.0180, ["2호선","6호선"]),
    "상왕십리": (37.5651, 127.0291, ["2호선"]),
    "왕십리": (37.5614, 127.0370, ["2호선","5호선","경의중앙선"]),
    "한양대": (37.5565, 127.0440, ["2호선"]),
    "뚝섬": (37.5473, 127.0471, ["2호선"]),
    "성수": (37.5445, 127.0558, ["2호선"]),
    "건대입구": (37.5406, 127.0698, ["2호선","7호선"]),
    "구의": (37.5386, 127.0844, ["2호선"]),
    "강변": (37.5348, 127.0937, ["2호선"]),
    "잠실나루": (37.5213, 127.1002, ["2호선"]),
    "잠실": (37.5134, 127.1001, ["2호선","8호선"]),
    "잠실새내": (37.5117, 127.0862, ["2호선"]),
    "종합운동장": (37.5108, 127.0733, ["2호선","9호선"]),
    "삼성": (37.5087, 127.0630, ["2호선"]),
    "선릉": (37.5046, 127.0490, ["2호선","분당선"]),
    "역삼": (37.5006, 127.0367, ["2호선"]),
    "강남": (37.4979, 127.0276, ["2호선"]),
    "교대": (37.4935, 127.0145, ["2호선","3호선"]),
    "서초": (37.4918, 127.0076, ["2호선"]),
    "방배": (37.4813, 126.9976, ["2호선"]),
    "사당": (37.4764, 126.9816, ["2호선","4호선"]),
    "낙성대": (37.4768, 126.9636, ["2호선"]),
    "서울대입구": (37.4816, 126.9530, ["2호선"]),
    "봉천": (37.4823, 126.9419, ["2호선"]),
    "신림": (37.4841, 126.9296, ["2호선"]),
    "신대방": (37.4875, 126.9133, ["2호선"]),
    "구로디지털단지": (37.4851, 126.9013, ["2호선"]),
    "대림": (37.4933, 126.8963, ["2호선","7호선"]),
    "신도림": (37.5089, 126.8912, ["1호선","2호선"]),
    "문래": (37.5178, 126.8957, ["2호선"]),
    "영등포구청": (37.5242, 126.8964, ["2호선","5호선"]),
    "당산": (37.5340, 126.9023, ["2호선","9호선"]),
    "합정": (37.5494, 126.9137, ["2호선","6호선"]),
    "홍대입구": (37.5569, 126.9237, ["2호선","경의중앙선"]),
    "신촌": (37.5554, 126.9368, ["2호선"]),
    "이대": (37.5567, 126.9466, ["2호선"]),
    "아현": (37.5577, 126.9561, ["2호선"]),
    "충정로": (37.5600, 126.9636, ["2호선","5호선"]),
    "경복궁": (37.5759, 126.9735, ["3호선"]),
    "안국": (37.5764, 126.9853, ["3호선"]),
    "충무로": (37.5612, 126.9943, ["3호선","4호선"]),
    "동국대입구": (37.5582, 127.0005, ["3호선"]),
    "약수": (37.5543, 127.0101, ["3호선","6호선"]),
    "금호": (37.5476, 127.0186, ["3호선"]),
    "옥수": (37.5402, 127.0176, ["3호선","경의중앙선"]),
    "압구정": (37.5270, 127.0284, ["3호선"]),
    "신사": (37.5164, 127.0199, ["3호선"]),
    "잠원": (37.5121, 127.0117, ["3호선"]),
    "고속터미널": (37.5047, 127.0049, ["3호선","7호선","9호선"]),
    "남부터미널": (37.4845, 127.0147, ["3호선"]),
    "양재": (37.4841, 127.0343, ["3호선","신분당선"]),
    "혜화": (37.5822, 127.0017, ["4호선"]),
    "한성대입구": (37.5887, 127.0066, ["4호선"]),
    "성신여대입구": (37.5926, 127.0162, ["4호선"]),
    "길음": (37.6030, 127.0249, ["4호선"]),
    "미아사거리": (37.6131, 127.0300, ["4호선"]),
    "미아": (37.6215, 127.0287, ["4호선"]),
    "수유": (37.6380, 127.0254, ["4호선"]),
    "삼각지": (37.5349, 126.9729, ["4호선","6호선"]),
    "숙대입구": (37.5450, 126.9720, ["4호선"]),
    "회현": (37.5587, 126.9780, ["4호선"]),
    "명동": (37.5610, 126.9862, ["4호선"]),
    "이촌": (37.5215, 126.9705, ["4호선","경의중앙선"]),
    "동작": (37.5071, 126.9578, ["4호선","9호선"]),
    "광화문": (37.5713, 126.9768, ["5호선"]),
    "서대문": (37.5653, 126.9666, ["5호선"]),
    "마포": (37.5395, 126.9460, ["5호선"]),
    "여의도": (37.5218, 126.9246, ["5호선","9호선"]),
    "여의나루": (37.5270, 126.9327, ["5호선"]),
    "공덕": (37.5440, 126.9514, ["5호선","6호선","경의중앙선"]),
    "이태원": (37.5345, 126.9946, ["6호선"]),
    "녹사평": (37.5340, 126.9874, ["6호선"]),
    "효창공원앞": (37.5392, 126.9621, ["6호선","경의중앙선"]),
    "디지털미디어시티": (37.5763, 126.8996, ["6호선","경의중앙선"]),
    "용산": (37.5298, 126.9646, ["1호선","경의중앙선"]),
    "노량진": (37.5131, 126.9426, ["1호선","9호선"]),
    "천호": (37.5390, 127.1237, ["5호선","8호선"]),
    "올림픽공원": (37.5164, 127.1316, ["5호선","9호선"]),
    "총신대입구(이수)": (37.4861, 126.9823, ["4호선","7호선"]),
    "고덕": (37.5548, 127.1541, ["5호선"]),
    "상봉": (37.5967, 127.0855, ["7호선","경의중앙선"]),
    "어린이대공원": (37.5481, 127.0740, ["7호선"]),
    "뚝섬유원지": (37.5311, 127.0660, ["7호선"]),
    "논현": (37.5114, 127.0215, ["7호선"]),
    "반포": (37.5083, 127.0113, ["7호선"]),
    "가산디지털단지": (37.4810, 126.8825, ["1호선","7호선"]),
    "신풍": (37.5089, 126.9091, ["7호선"]),
}

_congestion_cache = None

def _load_congestion_data():
    """지하철 혼잡도 데이터 로드 (역별 평균)"""
    path = os.path.join(SEOUL_TRAVEL_DIR, "subway_congestion.json")
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 역별/시간대별 평균 혼잡도 계산
    congestion = {}
    for row in data:
        stn = row.get("출발역", "")
        if not stn:
            continue
        stn = stn.replace("역", "")
        if stn not in congestion:
            congestion[stn] = {}

        # 시간대별 데이터 취합 (평일 기준)
        if row.get("요일구분") == "평일":
            for k, v in row.items():
                if "시" in k and "분" in k and isinstance(v, (int, float)):
                    if k not in congestion[stn]:
                        congestion[stn][k] = []
                    congestion[stn][k].append(v)

    # 평균 내기
    for stn, times in congestion.items():
        for t, vals in times.items():
            congestion[stn][t] = sum(vals) / len(vals) if vals else 0

    return congestion

def _congestion_to_label(value):
    """혼잡도 수치를 여유/보통/혼잡 텍스트로 변환"""
    if value is None:
        return None
    if value < 40:
        return "여유"
    elif value < 70:
        return "보통"
    else:
        return "혼잡"


def get_congestion_level(station_name, hour, minute):
    """해당 시간대의 역 혼잡도 수치 반환"""
    global _congestion_cache
    if _congestion_cache is None:
        _congestion_cache = _load_congestion_data()

    stn = station_name.replace("역", "")
    if stn not in _congestion_cache:
        return None

    # 시간 매칭 (30분 단위)
    m = "00" if minute < 30 else "30"
    time_key = f"{hour}시{m}분"
    
    # 0시 표기
    if hour == 0:
        time_key = f"00시{m}분"

    return _congestion_cache[stn].get(time_key, None)


def get_congestion_label(station_name, hour, minute):
    """해당 시간대의 역 혼잡도를 여유/보통/혼잡 텍스트로 반환"""
    value = get_congestion_level(station_name, hour, minute)
    return _congestion_to_label(value)


def haversine(lat1, lng1, lat2, lng2):
    """두 좌표 간 거리(km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_station(lat, lng, top_n=2):
    """좌표에서 가장 가까운 지하철역 반환"""
    distances = []
    for name, (slat, slng, lines) in SUBWAY_STATIONS.items():
        dist = haversine(lat, lng, slat, slng)
        distances.append((name, dist, lines))
    distances.sort(key=lambda x: x[1])
    return distances[:top_n]


def _load_subway_accessibility():
    """교통약자이용정보.json에서 역별 엘리베이터/에스컬레이터 정보 로드"""
    path = os.path.join(SEOUL_TRAVEL_DIR, "station_accessibility.json")
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 역별 엘리베이터 수/위치 집계
    station_info = {}
    for elv in data.get("엘리베이터", []):
        stn = elv.get("stnNm", "")
        line = elv.get("lineNm", "")
        key = f"{stn}"
        if key not in station_info:
            station_info[key] = {
                "lines": set(),
                "elevator_count": 0,
                "elevator_locations": [],
                "escalator_count": 0,
                "wheelchair_lift": 0,
            }
        station_info[key]["lines"].add(line)
        station_info[key]["elevator_count"] += 1
        pos = elv.get("dtlPstn", "")
        if pos:
            station_info[key]["elevator_locations"].append(pos)

    for esc in data.get("에스컬레이터", []):
        stn = esc.get("stnNm", "")
        key = f"{stn}"
        if key in station_info:
            station_info[key]["escalator_count"] += 1

    for wl in data.get("휠체어리프트", []):
        stn = wl.get("stnNm", "")
        key = f"{stn}"
        if key in station_info:
            station_info[key]["wheelchair_lift"] += 1

    # set → list
    for k in station_info:
        station_info[k]["lines"] = sorted(station_info[k]["lines"])

    return station_info


# 모듈 로드 시 한 번만 캐싱
_subway_acc_cache = None


def get_subway_accessibility():
    global _subway_acc_cache
    if _subway_acc_cache is None:
        _subway_acc_cache = _load_subway_accessibility()
    return _subway_acc_cache


def get_station_accessibility_text(station_name):
    """역 접근성 정보 텍스트 생성"""
    acc = get_subway_accessibility()
    # 역 이름에서 '역' 제거하고 검색
    search_names = [station_name, station_name.replace("역", ""), station_name + "역"]

    info = None
    for name in search_names:
        if name in acc:
            info = acc[name]
            break

    if not info:
        return ""

    parts = []
    parts.append(f"엘리베이터 {info['elevator_count']}대")
    if info["escalator_count"]:
        parts.append(f"에스컬레이터 {info['escalator_count']}대")
    if info["wheelchair_lift"]:
        parts.append(f"휠체어리프트 {info['wheelchair_lift']}대")

    return ", ".join(parts)


def generate_transit_guide(
    from_spot: dict,
    to_spot: dict,
    disability_type: str = "",
    start_hour: int = 10,
    start_min: int = 0,
) -> dict:
    """
    두 관광지 사이의 교통 안내를 생성.

    반환:
    {
        "distance_km": 3.2,
        "estimated_time_min": 25,
        "recommended_transit": "지하철",
        "guide_text": "...",
        "from_station": {...},
        "to_station": {...},
        "from_lowbus": [...],
        "accessibility_note": "...",
    }
    """
    from_lat = float(from_spot.get("lat", from_spot.get("latitude", 0)))
    from_lng = float(from_spot.get("lng", from_spot.get("longitude", 0)))
    to_lat = float(to_spot.get("lat", to_spot.get("latitude", 0)))
    to_lng = float(to_spot.get("lng", to_spot.get("longitude", 0)))

    dist = haversine(from_lat, from_lng, to_lat, to_lng)

    # 가까운 역 찾기
    from_stations = find_nearest_station(from_lat, from_lng)
    to_stations = find_nearest_station(to_lat, to_lng)

    from_stn_name, from_stn_dist, from_stn_lines = from_stations[0]
    to_stn_name, to_stn_dist, to_stn_lines = to_stations[0]

    # 역 접근성 정보
    from_stn_acc = get_station_accessibility_text(from_stn_name)
    to_stn_acc = get_station_accessibility_text(to_stn_name)

    # 저상버스 정보
    from_lowbus = from_spot.get("nearby_lowbus_stops", [])
    to_lowbus = to_spot.get("nearby_lowbus_stops", [])

    # 교통 수단 추천 및 가이드 텍스트 생성
    from_title = from_spot.get('title','')
    to_title = to_spot.get('title','')

    # 모든 경로에 출발역 혼잡도 포함
    from_cong = get_congestion_label(from_stn_name, start_hour, start_min)
    from_cong_str = f" (혼잡도: {from_cong})" if from_cong else ""

    if dist < 0.8:
        # 도보
        est_time = int(dist * 15)
        if disability_type in ["보행", "노인"]:
            est_time = int(dist * 20)
        recommended = "도보"
        guide_text = (
            f"<{from_title} → {to_title}: 도보 약 {max(est_time, 3)}분>\n"
            f"[{from_stn_name}역] 인근{from_cong_str}"
        )

    elif dist < 3.0:
        # 버스
        est_time = int(max(10, dist * 6))
        recommended = "버스"
        if from_lowbus:
            closest_stop = from_lowbus[0]
            routes = closest_stop.get("low_bus_routes", [])
            bus_str = f"저상버스 {routes[0]}번" if routes else "저상버스"
            guide_text = (
                f"<{from_title} → {to_title}: 버스 약 {est_time}분>\n"
                f"[{closest_stop.get('name','')} 정류장]에서 {bus_str} 탑승\n"
                f"[{from_stn_name}역] 인근{from_cong_str}"
            )
        else:
            guide_text = (
                f"<{from_title} → {to_title}: 버스 약 {est_time}분>\n"
                f"[{from_stn_name}역] 인근{from_cong_str}"
            )
            
    else:
        # 지하철
        est_time = int(max(15, dist * 5))
        recommended = "지하철"
        
        common_lines = set(from_stn_lines) & set(to_stn_lines)
        line_str = f"{list(common_lines)[0]}" if common_lines else f"{from_stn_lines[0]}"
        
        guide_text = (
            f"<{from_title} → {to_title}: 지하철 약 {est_time}분>\n"
            f"[{from_stn_name}역]에서 {line_str} 탑승{from_cong_str}"
        )

        if not common_lines:
            est_time += 10
            
    # 접근성 참고 사항 추가
    acc_note = ""
    if disability_type == "보행":
        acc_note = "휠체어 사용 시 엘리베이터가 있는 출입구를 이용하세요. 저상버스를 우선 이용하시기 바랍니다."
    elif disability_type == "시각":
        acc_note = "점자블록을 따라 이동하세요. 역 내 안내요원에게 도움을 요청할 수 있습니다."
    elif disability_type == "노인":
        acc_note = "엘리베이터와 에스컬레이터를 이용하세요. 무리한 도보 이동을 피하시기 바랍니다."
    elif disability_type == "유아동반":
        acc_note = "유모차 이용 시 엘리베이터를 이용하세요. 저상버스를 우선 이용하시기 바랍니다."

    if from_stn_acc and recommended == "지하철":
        guide_text += f"\n  편의시설: {from_stn_acc}"

    return {
        "distance_km": round(dist, 1),
        "estimated_time_min": est_time,
        "recommended_transit": recommended,
        "guide_text": guide_text,
        "congestion_label": from_cong,
        "from_station": {
            "name": from_stn_name,
            "distance_m": round(from_stn_dist * 1000),
            "lines": from_stn_lines,
            "accessibility": from_stn_acc,
        },
        "to_station": {
            "name": to_stn_name,
            "distance_m": round(to_stn_dist * 1000),
            "lines": to_stn_lines,
            "accessibility": to_stn_acc,
        },
        "from_lowbus": [
            {
                "name": s.get("name", ""),
                "distance_m": s.get("distance_m", 0),
                "routes": s.get("low_bus_routes", []),
            }
            for s in from_lowbus[:3]
        ],
        "accessibility_note": acc_note,
    }

