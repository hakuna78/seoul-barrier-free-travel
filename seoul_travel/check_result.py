import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\user\Desktop\seoul_travel\data\seoul_barrierfree_with_bus.json', encoding='utf-8') as f:
    data = json.load(f)

has_bus = [d for d in data if d.get('nearby_lowbus_stops')]
no_bus  = [d for d in data if not d.get('nearby_lowbus_stops')]
print(f"전체: {len(data)}건")
print(f"저상버스 정류장 있는 관광지: {len(has_bus)}건")
print(f"저상버스 정류장 없는 관광지: {len(no_bus)}건")
print()

if has_bus:
    s = has_bus[0]
    print("=== 샘플 ===")
    print("관광지:", s["title"])
    print("주소:", s["address"])
    print("저상버스 안내:")
    print(s["lowbus_text"])
    print()
    print("구조화 데이터 (nearby_lowbus_stops):")
    for stop in s["nearby_lowbus_stops"]:
        print(f"  - {stop['name']} ({stop['distance_m']}m) : {', '.join(stop['low_bus_routes'])}")
