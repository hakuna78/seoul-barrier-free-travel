"""
서울 무장애 관광지 ↔ 저상버스 정류장 연결 스크립트

[Input]
- seoul_barrierfree.json : 관광지 (위경도 포함)
- 서울시버스노선별정류소정보.xlsx : 버스 정류장별 위경도 + 노선명
- 서울시 저상버스 도입 노선 및 노선별 보유율.xlsx : 저상버스 노선 목록

[Output]
- seoul_barrierfree_with_bus.json : 관광지 + 가까운 저상버스 정류장 정보 통합
"""

import json
import math
import sys
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ── 파일 경로 ──
BASE_DIR   = r"C:\Users\user\Desktop\seoul_travel"
TOUR_JSON   = BASE_DIR + r"\data\seoul_barrierfree.json"
BUS_STOP_XL = BASE_DIR + r"\서울시버스노선별정류소정보(20260108).xlsx"
LOW_BUS_XL  = BASE_DIR + r"\data\서울시 저상버스 도입 노선 및 노선별 보유율(25.4.25).xlsx"
OUTPUT_JSON = BASE_DIR + r"\data\seoul_barrierfree_with_bus.json"

SEARCH_RADIUS_M = 500  # 정류장 탐색 반경 (미터)


# ── 거리 계산 (Haversine) ──
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_data():
    print("📂 데이터 로딩 중...")

    # 1. 관광지 JSON
    with open(TOUR_JSON, encoding="utf-8") as f:
        spots = json.load(f)
    print(f"  ✅ 관광지: {len(spots)}건")

    # 2. 저상버스 노선 목록 (노선번호 set)
    df_low = pd.read_excel(LOW_BUS_XL)
    df_low.columns = [c.replace("\n", "") for c in df_low.columns]
    # 저상버스가 1대라도 있는 노선만 포함
    df_low = df_low[df_low["저상버스 대수"] > 0]
    low_routes = set(df_low["노선번호"].astype(str).str.strip())
    print(f"  ✅ 저상버스 운행 노선: {len(low_routes)}개")

    # 3. 버스 정류소 정보 (저상버스 노선 정류장만 필터)
    print("  📊 버스 정류소 로딩 중 (시간이 걸릴 수 있습니다)...")
    df_stop = pd.read_excel(BUS_STOP_XL)
    df_stop["노선명_str"] = df_stop["노선명"].astype(str).str.strip()

    # 저상버스 노선인 정류장만 남기기
    df_low_stop = df_stop[df_stop["노선명_str"].isin(low_routes)].copy()
    print(f"  ✅ 저상버스 정류장 행 수: {len(df_low_stop)}건")

    # 정류장별로 그룹화 (ARS_ID 기준) - 중복 정류장 합치기
    stop_groups = {}
    for _, row in df_low_stop.iterrows():
        ars = str(row["ARS_ID"])
        if ars not in stop_groups:
            stop_groups[ars] = {
                "ars_id": ars,
                "name": row["정류소명"],
                "latitude": float(row["Y좌표"]),
                "longitude": float(row["X좌표"]),
                "low_bus_routes": set(),
            }
        stop_groups[ars]["low_bus_routes"].add(row["노선명_str"])

    # set → 정렬된 list로 변환
    stops = []
    for s in stop_groups.values():
        s["low_bus_routes"] = sorted(list(s["low_bus_routes"]))
        stops.append(s)
    print(f"  ✅ 고유 저상버스 정류장 수: {len(stops)}개\n")

    return spots, stops


def find_nearby_stops(spot_lat, spot_lon, stops, radius_m=SEARCH_RADIUS_M):
    """관광지 좌표에서 반경 내 저상버스 정류장 탐색"""
    nearby = []
    for stop in stops:
        dist = haversine_m(spot_lat, spot_lon, stop["latitude"], stop["longitude"])
        if dist <= radius_m:
            nearby.append({
                "ars_id": stop["ars_id"],
                "name": stop["name"],
                "distance_m": round(dist),
                "low_bus_routes": stop["low_bus_routes"],
            })
    # 가까운 순 정렬, 최대 5개
    nearby.sort(key=lambda x: x["distance_m"])
    return nearby[:5]


def build_bus_text(nearby_stops):
    """RAG용 저상버스 안내 텍스트 생성"""
    if not nearby_stops:
        return "근처 저상버스 정류장 없음"

    lines = []
    for s in nearby_stops:
        routes_str = ", ".join(s["low_bus_routes"])
        lines.append(
            f"- {s['name']} 정류장 ({s['distance_m']}m): 저상버스 {routes_str}번 운행"
        )
    return "\n".join(lines)


def main():
    spots, stops = load_data()

    print("🔗 관광지 ↔ 저상버스 정류장 매핑 중...")
    results = []
    no_stop_count = 0

    for i, spot in enumerate(spots):
        lat = spot.get("latitude")
        lon = spot.get("longitude")

        # 위경도 없는 경우 스킵
        if not lat or not lon:
            spot["nearby_lowbus_stops"] = []
            spot["lowbus_text"] = "위치 정보 없음"
            results.append(spot)
            continue

        try:
            nearby = find_nearby_stops(float(lat), float(lon), stops)
        except (ValueError, TypeError):
            nearby = []

        bus_text = build_bus_text(nearby)
        spot["nearby_lowbus_stops"] = nearby
        spot["lowbus_text"] = bus_text

        # text 필드에 저상버스 정보 추가
        spot["text"] = spot.get("text", "") + f"\n\n[인근 저상버스 정류장]\n{bus_text}"

        if not nearby:
            no_stop_count += 1

        results.append(spot)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(spots)}] 처리 중...")

    print(f"\n✅ 매핑 완료!")
    print(f"  저상버스 정류장 있는 관광지: {len(results) - no_stop_count}건")
    print(f"  저상버스 정류장 없는 관광지: {no_stop_count}건")

    # 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 저장 완료: {OUTPUT_JSON}")

    # Colab 자동 다운로드
    try:
        from google.colab import files
        print("\n[Colab] 파일 다운로드 시작...")
        files.download(OUTPUT_JSON)
    except ImportError:
        pass

    # 샘플 출력
    print("\n=== 샘플 결과 (저상버스 있는 첫 번째 관광지) ===")
    for r in results:
        if r["nearby_lowbus_stops"]:
            print(f"관광지: {r['title']}")
            print(f"위치: {r['address']}")
            print(f"저상버스 정류장:\n{r['lowbus_text']}")
            break


if __name__ == "__main__":
    main()
