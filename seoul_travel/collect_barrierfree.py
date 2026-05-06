"""
서울시 무장애 관광지 750건 전체 수집
- 관광지 기본정보 (areaBasedList2)
- 무장애 편의시설 상세 (detailWithTour2)
- 소개/개요 (detailCommon2)
→ RAG 주입용 JSON 저장
"""

import os
import sys
import json
import time
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ── 설정 ──
ENC_KEY = "***"
BASE = "http://apis.data.go.kr/B551011/KorWithService2"
AREA_CODE = "1"  # 서울
PAGE_SIZE = 100
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "seoul_barrierfree.json")

# 편의시설 필드 한글 매핑
FACILITY_LABELS = {
    "parking": "주차장",
    "route": "접근경로",
    "publictransport": "대중교통",
    "ticketoffice": "매표소",
    "promotion": "홍보물",
    "wheelchair": "휠체어대여",
    "exit": "주출입구",
    "elevator": "엘리베이터",
    "restroom": "장애인화장실",
    "auditorium": "관람석",
    "room": "장애인객실",
    "handicapetc": "지체장애기타",
    "braileblock": "점자블록",
    "helpdog": "보조견동반",
    "guidehuman": "안내요원",
    "audioguide": "음성안내",
    "bigprint": "큰활자안내",
    "brailepromotion": "점자홍보물",
    "guidesystem": "안내시스템",
    "blindhandicapetc": "시각장애기타",
    "signguide": "수어안내",
    "videoguide": "영상안내",
    "hearingroom": "청각장애객실",
    "hearinghandicapetc": "청각장애기타",
    "stroller": "유모차대여",
    "lactationroom": "수유실",
    "babysparechair": "유아용보조의자",
    "infantsfamilyetc": "영유아가족기타",
}

# 콘텐츠타입 매핑
CONTENT_TYPE = {
    "12": "관광지",
    "14": "문화시설",
    "15": "축제공연행사",
    "25": "여행코스",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
    "39": "음식점",
}


def api_get(operation, extra_params, retries=3):
    """API 호출 (재시도 포함)"""
    url = f"{BASE}/{operation}?serviceKey={ENC_KEY}"
    for k, v in extra_params.items():
        url += f"&{k}={v}"
    url += "&MobileOS=ETC&MobileApp=BarrierFree&_type=json"

    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                print(f"  [WARN] status=429 (요청 폭주 제한), 5초 대기 후 재시도... ({attempt+1}/{retries})")
                time.sleep(5)
                continue
            else:
                print(f"  [WARN] status={r.status_code}, retry {attempt+1}")
        except Exception as e:
            print(f"  [WARN] {e}, retry {attempt+1}")
        time.sleep(1)
    return None


def fetch_all_spots():
    """서울 무장애 관광지 전체 목록 수집"""
    all_items = []
    page = 1

    # 첫 페이지로 총 건수 확인
    data = api_get("areaBasedList2", {
        "areaCode": AREA_CODE,
        "numOfRows": str(PAGE_SIZE),
        "pageNo": "1",
    })
    if not data:
        print("[ERROR] 목록 API 호출 실패")
        return []

    total = data["response"]["body"]["totalCount"]
    print(f"서울 무장애 관광지 총 {total}건 수집 시작...")

    items = data["response"]["body"]["items"].get("item", [])
    if isinstance(items, dict):
        items = [items]
    all_items.extend(items)
    print(f"  페이지 1: {len(items)}건")

    # 나머지 페이지
    total_pages = (total // PAGE_SIZE) + (1 if total % PAGE_SIZE else 0)
    for page in range(2, total_pages + 1):
        time.sleep(0.3)
        data = api_get("areaBasedList2", {
            "areaCode": AREA_CODE,
            "numOfRows": str(PAGE_SIZE),
            "pageNo": str(page),
        })
        if data:
            items = data["response"]["body"]["items"].get("item", [])
            if isinstance(items, dict):
                items = [items]
            all_items.extend(items)
            print(f"  페이지 {page}/{total_pages}: {len(items)}건")

    print(f"목록 수집 완료: 총 {len(all_items)}건\n")
    return all_items


def fetch_detail_common(content_id):
    """관광지 공통 상세정보 (개요, 홈페이지 등)"""
    data = api_get("detailCommon2", {
        "contentId": str(content_id),
        "defaultYN": "Y",
        "overviewYN": "Y",
    })
    if not data:
        return {}
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, list) and items:
        return items[0]
    if isinstance(items, dict):
        return items
    return {}


def fetch_barrierfree(content_id):
    """무장애 편의시설 상세정보"""
    data = api_get("detailWithTour2", {
        "contentId": str(content_id),
    })
    if not data:
        return {}
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, list) and items:
        return items[0]
    if isinstance(items, dict):
        return items
    return {}


def build_rag_document(spot, common, bf):
    """RAG 주입용 문서 구성"""
    content_type = CONTENT_TYPE.get(spot.get("contenttypeid", ""), "기타")

    # 무장애 편의시설 텍스트 생성
    facilities = {}
    facility_text_parts = []
    for field, label in FACILITY_LABELS.items():
        value = bf.get(field, "")
        if value and value.strip():
            facilities[label] = value.strip()
            facility_text_parts.append(f"- {label}: {value.strip()}")

    facility_text = "\n".join(facility_text_parts) if facility_text_parts else "편의시설 정보 없음"

    # 개요 텍스트 (HTML 태그 제거)
    overview = common.get("overview", "")
    import re
    overview = re.sub(r"<[^>]+>", "", overview)
    overview = re.sub(r"&[a-zA-Z]+;", " ", overview)
    overview = overview.strip()

    # RAG 문서
    doc = {
        # 메타데이터 (필터링/검색용)
        "id": spot.get("contentid", ""),
        "title": spot.get("title", ""),
        "category": content_type,
        "address": spot.get("addr1", "") + " " + spot.get("addr2", ""),
        "tel": spot.get("tel", ""),
        "latitude": spot.get("mapy", ""),
        "longitude": spot.get("mapx", ""),
        "image_url": spot.get("firstimage", ""),
        "thumbnail_url": spot.get("firstimage2", ""),

        # 무장애 편의시설 (구조화)
        "accessibility": facilities,

        # RAG용 통합 텍스트
        "text": (
            f"[{content_type}] {spot.get('title', '')}\n"
            f"주소: {spot.get('addr1', '')} {spot.get('addr2', '')}\n"
            f"\n{overview}\n\n"
            f"[무장애 편의시설]\n{facility_text}"
        ),
    }
    return doc


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. 전체 목록 수집
    spots = fetch_all_spots()
    if not spots:
        print("수집된 관광지가 없습니다.")
        return

    # 2. 각 관광지별 상세정보 수집
    documents = []
    total = len(spots)

    for i, spot in enumerate(spots):
        cid = spot.get("contentid", "")
        ctype = spot.get("contenttypeid", "")
        title = spot.get("title", "")
        
        # RAG 추천에 적합한 '진짜 관광지'만 허용
        # 12: 관광지, 14: 문화시설, 28: 레포츠, 38: 쇼핑
        if ctype not in ["12", "14", "28", "38"]:
            print(f"[{i+1}/{total}] {title} (id:{cid}) - [스킵] 추천 부적합 카테고리({CONTENT_TYPE.get(ctype, '기타')})")
            continue
            
        print(f"[{i+1}/{total}] {title} (id:{cid})")

        # 공통 상세정보
        common = fetch_detail_common(cid)
        time.sleep(0.5)

        # 무장애 편의시설
        bf = fetch_barrierfree(cid)
        time.sleep(0.5)

        doc = build_rag_document(spot, common, bf)
        documents.append(doc)

        # 중간 저장 (50건마다)
        if (i + 1) % 50 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            print(f"  >> 중간저장 ({i+1}/{total}건)")

    # 3. 최종 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"수집 완료: {len(documents)}건")
    print(f"저장 위치: {OUTPUT_FILE}")

    # 통계
    has_any = sum(1 for d in documents if d["accessibility"])
    print(f"편의시설 정보 있는 곳: {has_any}건 / {len(documents)}건")

    # Colab 환경일 경우 자동 다운로드
    try:
        from google.colab import files
        print("\n[안내] Colab 환경이 감지되었습니다. 파일 다운로드를 시작합니다...")
        files.download(OUTPUT_FILE)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
