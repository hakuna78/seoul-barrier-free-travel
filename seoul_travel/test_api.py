import requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")

ENC_KEY = "***"

# 서울 무장애 관광지 총 건수 확인
url = f"http://apis.data.go.kr/B551011/KorWithService2/areaBasedList2?serviceKey={ENC_KEY}&areaCode=1&numOfRows=1&pageNo=1&MobileOS=ETC&MobileApp=test&_type=json"
r = requests.get(url, timeout=10)
data = r.json()
total = data["response"]["body"]["totalCount"]
print(f"서울 무장애 관광지 총 건수: {total}건")

# 첫 번째 관광지의 무장애 상세정보 테스트
item = data["response"]["body"]["items"]["item"][0]
cid = item["contentid"]
print(f"\n첫 번째 관광지: {item['title']} (contentId: {cid})")

# detailWithTour2 호출
url2 = f"http://apis.data.go.kr/B551011/KorWithService2/detailWithTour2?serviceKey={ENC_KEY}&contentId={cid}&MobileOS=ETC&MobileApp=test&_type=json"
r2 = requests.get(url2, timeout=10)
data2 = r2.json()
print(f"\n=== 무장애 편의시설 상세 ===")
print(json.dumps(data2, ensure_ascii=False, indent=2)[:3000])
