"""
무장애 여행 추천 시각화 API (FastAPI)
- Colab 또는 로컬에서 실행 가능
- 코스, 교통정보, 관광지 이미지, 혼잡도 시각 확인용
"""
import json
import os
import sys
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

app = FastAPI(title="무장애 여행 추천 시스템")


# ── HTML 템플릿 ──
FORM_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>무장애 여행 추천</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Noto Sans KR',sans-serif; background:linear-gradient(135deg,#0f0c29,#302b63,#24243e); min-height:100vh; color:#fff; }
.container { max-width:600px; margin:0 auto; padding:40px 20px; }
h1 { text-align:center; font-size:2rem; margin-bottom:10px; background:linear-gradient(90deg,#00d2ff,#3a7bd5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.subtitle { text-align:center; color:#aaa; margin-bottom:40px; font-size:0.95rem; }
.card { background:rgba(255,255,255,0.08); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.15); border-radius:16px; padding:30px; margin-bottom:20px; }
.card h3 { font-size:1rem; color:#00d2ff; margin-bottom:15px; }
.options { display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:10px; }
.opt { padding:12px 8px; border:2px solid rgba(255,255,255,0.15); border-radius:12px; text-align:center; cursor:pointer; transition:all 0.3s; font-size:0.9rem; }
.opt:hover { border-color:#00d2ff; background:rgba(0,210,255,0.1); }
.opt.selected { border-color:#00d2ff; background:rgba(0,210,255,0.2); box-shadow:0 0 15px rgba(0,210,255,0.3); }
.btn { display:block; width:100%; padding:16px; border:none; border-radius:12px; background:linear-gradient(90deg,#00d2ff,#3a7bd5); color:#fff; font-size:1.1rem; font-weight:700; cursor:pointer; margin-top:30px; transition:transform 0.2s; }
.btn:hover { transform:scale(1.02); }
.btn:disabled { opacity:0.5; cursor:not-allowed; }
.loading { display:none; text-align:center; padding:40px; }
.spinner { width:40px; height:40px; border:4px solid rgba(255,255,255,0.2); border-top-color:#00d2ff; border-radius:50%; animation:spin 0.8s linear infinite; margin:0 auto 15px; }
@keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <h1>♿ 무장애 여행 추천</h1>
  <p class="subtitle">맞춤형 무장애 관광 코스를 추천해드립니다</p>

  <div class="card"><h3>🧑‍🦽 장애 유형</h3>
    <div class="options" data-name="disability_type">
      <div class="opt" data-val="시각">👁️ 시각</div>
      <div class="opt" data-val="청각">👂 청각</div>
      <div class="opt" data-val="보행">🦽 보행</div>
      <div class="opt" data-val="지적">🧠 지적</div>
      <div class="opt" data-val="유아동반">👶 유아동반</div>
      <div class="opt" data-val="노인">👴 노인</div>
    </div>
  </div>

  <div class="card"><h3>👥 일행 수</h3>
    <div class="options" data-name="group_size">
      <div class="opt" data-val="1인">1인</div>
      <div class="opt" data-val="2인">2인</div>
      <div class="opt" data-val="3인">3인</div>
      <div class="opt" data-val="4인이상">4인이상</div>
    </div>
  </div>

  <div class="card"><h3>🤝 동반자</h3>
    <div class="options" data-name="companion">
      <div class="opt" data-val="친구와">👫 친구와</div>
      <div class="opt" data-val="가족과">👨‍👩‍👧 가족과</div>
      <div class="opt" data-val="커플">💑 커플</div>
      <div class="opt" data-val="혼자">🚶 혼자</div>
    </div>
  </div>

  <div class="card"><h3>🎯 여행 스타일</h3>
    <div class="options" data-name="travel_style">
      <div class="opt" data-val="쇼핑">🛍️ 쇼핑</div>
      <div class="opt" data-val="미식">🍽️ 미식</div>
      <div class="opt" data-val="힐링">🌿 힐링</div>
      <div class="opt" data-val="역사/문화">🏛️ 역사/문화</div>
    </div>
  </div>

  <button class="btn" id="submitBtn" disabled onclick="submitForm()">추천 코스 생성하기</button>
  <div class="loading" id="loading">
    <div class="spinner"></div>
    <p>맞춤 코스를 생성 중입니다...</p>
  </div>
</div>

<script>
const selections = {};
document.querySelectorAll('.opt').forEach(el => {
  el.addEventListener('click', () => {
    const group = el.parentElement.dataset.name;
    el.parentElement.querySelectorAll('.opt').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    selections[group] = el.dataset.val;
    document.getElementById('submitBtn').disabled = Object.keys(selections).length < 4;
  });
});
function submitForm() {
  document.getElementById('submitBtn').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  const params = new URLSearchParams(selections);
  window.location.href = '/recommend?' + params.toString();
}
</script>
</body>
</html>
"""


def build_result_html(result: dict) -> str:
    ob = result["onboarding"]
    schedule = result["schedule"]
    total_km = result["total_distance_km"]
    total_min = result["total_time_min"]

    spots_html = ""
    for s in schedule:
        # 혼잡도 배지 색상
        cong = s.get("nearest_station_congestion", "")
        cong_color = {"여유": "#00c853", "보통": "#ff9800", "혼잡": "#f44336"}.get(cong, "#888")
        cong_badge = f'<span style="background:{cong_color};color:#fff;padding:3px 10px;border-radius:20px;font-size:0.8rem;font-weight:500">{cong}</span>' if cong else ""

        # 이미지
        img_html = ""
        img_url = s.get("image_url", "")
        if img_url:
            img_html = f'<img src="{img_url}" style="width:100%;height:220px;object-fit:cover;border-radius:12px;margin-bottom:15px" onerror="this.style.display=\'none\'">'

        # 접근성 요약
        acc_html = ""
        for a in s.get("accessibility_summary", [])[:4]:
            acc_html += f'<div style="padding:6px 12px;background:rgba(0,210,255,0.1);border-radius:8px;font-size:0.82rem;margin:3px 0">✓ {a}</div>'

        # 저상버스
        bus_html = ""
        bus_info = s.get("lowbus_info", "")
        if bus_info:
            bus_lines = bus_info.replace("\n", "<br>")
            bus_html = f'<div style="margin-top:10px;padding:10px;background:rgba(76,175,80,0.1);border-radius:8px;font-size:0.82rem">🚌 <b>저상버스</b><br>{bus_lines[:250]}</div>'

        # 지하철
        stn_html = ""
        if s.get("nearest_station"):
            lines = ", ".join(s.get("nearest_station_lines", []))
            stn_acc = s.get("nearest_station_accessibility", "")
            stn_acc_html = f'<br><span style="font-size:0.8rem;color:#aaa">♿ {stn_acc}</span>' if stn_acc else ""
            stn_html = f'''
            <div style="margin-top:10px;padding:10px;background:rgba(33,150,243,0.1);border-radius:8px;font-size:0.85rem">
              🚇 <b>{s["nearest_station"]}역</b> ({lines}) · 도보 {s.get("nearest_station_distance_m",0)}m {cong_badge}
              {stn_acc_html}
            </div>'''

        # 교통 안내 (다음 장소)
        transit_html = ""
        transit = s.get("transit_to_next", {})
        if transit:
            guide = transit.get("guide_text", "").replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;").replace("&lt;", "<span style='color:#00d2ff'>").replace("&gt;", "</span>")
            note = transit.get("accessibility_note", "")
            note_html = f'<div style="margin-top:5px;font-size:0.82rem;color:#ffab40">💡 {note}</div>' if note else ""
            transit_html = f'''
            <div style="margin:15px 0;padding:15px;background:rgba(255,255,255,0.05);border-left:3px solid #00d2ff;border-radius:0 8px 8px 0;font-size:0.88rem">
              {guide}{note_html}
            </div>'''

        # overview
        overview_html = ""
        ov = s.get("overview", "")
        if ov:
            overview_html = f'<p style="color:#bbb;font-size:0.85rem;margin:8px 0;line-height:1.5">📝 {ov}</p>'

        # 접근성 점수 바
        score = s.get("accessibility_score", 0)
        score_pct = min(score * 10, 100)
        score_color = "#f44336" if score < 3 else "#ff9800" if score < 6 else "#4caf50"

        spots_html += f'''
        <div style="background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:20px;margin-bottom:20px">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <div style="width:36px;height:36px;background:linear-gradient(135deg,#00d2ff,#3a7bd5);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem;flex-shrink:0">{s["order"]}</div>
            <div>
              <h3 style="font-size:1.1rem;margin:0">{s["title"]}</h3>
              <span style="font-size:0.82rem;color:#aaa">{s["category"]}</span>
            </div>
          </div>
          {img_html}
          {overview_html}
          <div style="font-size:0.85rem;color:#ccc;margin-bottom:8px">📍 {s.get("address","")}</div>
          <div style="font-size:0.9rem;margin-bottom:8px">🕐 {s["arrival"]} ~ {s["departure"]} ({s["visit_duration_min"]}분)</div>
          <div style="margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:8px;font-size:0.85rem;margin-bottom:4px">
              <span>접근성</span>
              <div style="flex:1;height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden">
                <div style="width:{score_pct}%;height:100%;background:{score_color};border-radius:4px"></div>
              </div>
              <span style="color:{score_color};font-weight:700">{score}/10</span>
            </div>
          </div>
          {stn_html}
          {acc_html}
          {bus_html}
        </div>
        {transit_html}
        '''

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>추천 코스 결과</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Noto Sans KR',sans-serif; background:linear-gradient(135deg,#0f0c29,#302b63,#24243e); min-height:100vh; color:#fff; }}
.container {{ max-width:650px; margin:0 auto; padding:30px 16px; }}
.header {{ text-align:center; margin-bottom:30px; }}
h1 {{ font-size:1.6rem; background:linear-gradient(90deg,#00d2ff,#3a7bd5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.summary {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:20px 0 30px; }}
.stat {{ background:rgba(255,255,255,0.08); border-radius:12px; padding:15px; text-align:center; }}
.stat-val {{ font-size:1.4rem; font-weight:700; color:#00d2ff; }}
.stat-label {{ font-size:0.8rem; color:#aaa; margin-top:4px; }}
.tags {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin:15px 0; }}
.tag {{ background:rgba(0,210,255,0.15); border:1px solid rgba(0,210,255,0.3); padding:6px 14px; border-radius:20px; font-size:0.82rem; }}
.back {{ display:inline-block; color:#00d2ff; text-decoration:none; font-size:0.9rem; margin-top:20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>♿ 맞춤 추천 코스</h1>
    <div class="tags">
      <span class="tag">🧑‍🦽 {ob.get("disability_type","")}</span>
      <span class="tag">👥 {ob.get("group_size","")}</span>
      <span class="tag">🤝 {ob.get("companion","")}</span>
      <span class="tag">🎯 {ob.get("travel_style","")}</span>
    </div>
  </div>

  <div class="summary">
    <div class="stat"><div class="stat-val">{len(schedule)}곳</div><div class="stat-label">추천 장소</div></div>
    <div class="stat"><div class="stat-val">{total_km}km</div><div class="stat-label">총 이동거리</div></div>
    <div class="stat"><div class="stat-val">{total_min}분</div><div class="stat-label">총 소요시간</div></div>
    <div class="stat"><div class="stat-val">{total_min//60}시간 {total_min%60}분</div><div class="stat-label">예상 시간</div></div>
  </div>

  {spots_html}

  <div style="text-align:center;margin-top:30px">
    <a href="/" class="back">← 다시 추천받기</a>
  </div>
</div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return FORM_HTML


@app.get("/recommend", response_class=HTMLResponse)
async def get_recommendation(
    disability_type: str = Query(...),
    group_size: str = Query(...),
    companion: str = Query(...),
    travel_style: str = Query(...),
):
    from src.recommender.engine import recommend

    onboarding = {
        "disability_type": disability_type,
        "group_size": group_size,
        "companion": companion,
        "travel_style": travel_style,
    }

    result = recommend(onboarding)
    return HTMLResponse(build_result_html(result))


@app.get("/api/recommend")
async def api_recommend(
    disability_type: str = Query(...),
    group_size: str = Query(...),
    companion: str = Query(...),
    travel_style: str = Query(...),
):
    from src.recommender.engine import recommend

    onboarding = {
        "disability_type": disability_type,
        "group_size": group_size,
        "companion": companion,
        "travel_style": travel_style,
    }
    return recommend(onboarding)


def show_in_colab(disability_type="유아동반", group_size="3인", companion="가족과", travel_style="쇼핑", district=""):
    """
    Colab에서 서버 없이 바로 결과 확인용.
    사용법:
        from app import show_in_colab
        show_in_colab("청각", "2인", "가족과", "힐링", "종로구")
    """
    from IPython.display import display, HTML as IPHTML
    from src.recommender.engine import recommend

    onboarding = {
        "disability_type": disability_type,
        "group_size": group_size,
        "companion": companion,
        "travel_style": travel_style,
        "district": district,
    }
    result = recommend(onboarding)
    html = build_result_html(result)
    display(IPHTML(html))
    return result


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  무장애 여행 추천 시스템")
    print("  http://localhost:8000 에서 확인하세요")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

