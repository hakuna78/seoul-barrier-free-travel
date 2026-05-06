import pandas as pd
import requests
import json
import urllib.parse

# 1. 엑셀 데이터에서 서울역과 경복궁을 모두 지나는 저상버스 노선 찾기
BUS_STOP_XL = r"C:\Users\user\Desktop\seoul_travel\서울시버스노선별정류소정보(20260108).xlsx"
LOW_BUS_XL  = r"C:\Users\user\Desktop\seoul_travel\data\서울시 저상버스 도입 노선 및 노선별 보유율(25.4.25).xlsx"

df_stop = pd.read_excel(BUS_STOP_XL)
df_low = pd.read_excel(LOW_BUS_XL)
df_low.columns = [c.replace('\n', '') for c in df_low.columns]
low_routes = set(df_low[df_low["저상버스 대수"] > 0]["노선번호"].astype(str).str.strip())

df_stop["노선명_str"] = df_stop["노선명"].astype(str).str.strip()
df_low_stop = df_stop[df_stop["노선명_str"].isin(low_routes)]

# 서울역과 경복궁 정류장을 지나는 노선 찾기
seoul_station_routes = set(df_low_stop[df_low_stop["정류소명"].str.contains("서울역")]["노선명_str"])
gyeongbok_routes = set(df_low_stop[df_low_stop["정류소명"].str.contains("경복궁")]["노선명_str"])

common_routes = seoul_station_routes.intersection(gyeongbok_routes)
print(f"서울역과 경복궁을 모두 지나는 저상버스 노선: {common_routes}")

if not common_routes:
    print("해당하는 노선이 없습니다.")
    exit()

route = list(common_routes)[0]

# 해당 노선의 서울역 정류장 찾기 (승차 정류장)
boarding_stops = df_low_stop[(df_low_stop["노선명_str"] == route) & (df_low_stop["정류소명"].str.contains("서울역"))]
print(f"\n[{route}번 버스] 서울역 승차 정류장:")
print(boarding_stops[["ARS_ID", "정류소명"]].head(1).to_string())

ars_id = str(boarding_stops.iloc[0]["ARS_ID"]).zfill(5)

# 2. 실시간 도착 정보 API 호출 (키가 활성화되었는지 확인)
print("\n--- 실시간 API 호출 ---")
ENC_KEY = "***"
url = f"http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid?ServiceKey={ENC_KEY}&arsId={ars_id}&resultType=json"

try:
    r = requests.get(url, timeout=10)
    data = r.json()
    if data["msgHeader"]["headerCd"] == "0":
        items = data["msgBody"]["itemList"]
        for item in items:
            if item["rtNm"] == route:
                print(f"✅ {route}번 버스 도착 예정 정보:")
                print(f" - 첫 번째 버스: {item['arrmsg1']} (저상 여부: {item['busType1']})") # busType1: 1이면 일반, 2이면 저상
                print(f" - 두 번째 버스: {item['arrmsg2']} (저상 여부: {item['busType2']})")
    else:
        print("API 에러:", data["msgHeader"]["headerMsg"])
except Exception as e:
    print("요청 실패:", e)
