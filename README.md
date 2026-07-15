# ♿ 여행누리 freePATH — 서울 무장애 여행 추천 시스템
RAG 기반 접근성 맞춤형 무장애 관광 코스 추천 플랫폼입니다.

사용자의 장애 유형·여행 스타일·동반자 정보를 온보딩으로 수집한 뒤, FAISS 벡터 검색과 접근성 가중치 스코어링을 결합하여 서울시 무장애 관광지를 탐색하고, 동선 최적화·교통 안내·혼잡도 반영까지 포함한 1일 맞춤 코스를 자동 생성합니다.

---

## 📌 Project Summary
본 프로젝트는 교통약자(장애인, 고령자, 영유아 동반 가족 등)를 위한 맞춤형 무장애 여행 코스 추천 시스템을 구현합니다. 한국관광공사 무장애 관광지 API와 서울 열린데이터광장의 교통·혼잡도 데이터를 기반으로, 사용자별 접근성 요구사항에 최적화된 여행 코스를 RAG 파이프라인으로 생성합니다.

---

## 🧭 Background
장애인·고령자·영유아 동반 가족 등 교통약자의 여행 수요는 꾸준히 증가하고 있지만, 실시간 접근성 정보(엘리베이터, 경사로, 저상버스 등)와 혼잡도를 종합적으로 반영한 여행 코스 추천 서비스는 부재합니다.

기존 관광 추천 서비스는 다음과 같은 한계를 가집니다:

1. 접근성 정보 미반영: 일반 관광 추천은 장애 유형별 편의시설 유무를 고려하지 않음
2. 단순 키워드 검색의 한계: 단순 키워드 매칭으로는 사용자 맥락에 맞는 장소를 정확히 검색하기 어려움
3. 동선·교통 미고려: 장소를 추천하더라도 이동 경로, 저상버스·엘리베이터 접근성, 실시간 혼잡도를 반영하지 않음

본 프로젝트는 이러한 문제를 해결하기 위해, RAG(Retrieval-Augmented Generation) 파이프라인에 장애 유형별 접근성 가중치 스코어링과 Nearest Neighbor 동선 최적화를 결합한 종합 추천 시스템을 설계했습니다.

---

## 🔁 Pipeline

프로젝트의 전체 흐름은 다음과 같습니다.

**STEP 1 — 온보딩 → 검색 쿼리 생성**

사용자의 장애 유형, 여행 스타일, 동반자 정보를 입력받습니다. 이용자 유형별 프로필을 조합하여 RAG 검색 쿼리를 자동 생성합니다.

**STEP 2 — FAISS 벡터 검색 (Top-50)**

paraphrase-multilingual-MiniLM-L12-v2 다국어 임베딩 모델로 관광지 문서를 벡터화한 FAISS 인덱스에서 상위 50건을 검색합니다. 관광지·음식점·문화시설·쇼핑 등의 무장애 관광지 데이터를 대상으로 유사도 기반 검색을 수행합니다.

**STEP 3 — 접근성 스코어링 + 필터링**

6가지 이용자 유형(보행, 시각, 청각, 지적, 유아동반, 노인)별로 접근성 키워드에 대해 가중치를 부여하여 접근성 점수를 산출합니다. 필수 키워드 미충족 시 감점, 최소 접근성 임계값 미달 시 필터링합니다.

**STEP 4 — 코스 장소 선정**

여행 스타일별 카테고리 비율을 적용하여 장소를 선정합니다. 구간 최대 이동 거리와 1일 총 이동 거리 제한을 적용합니다.

**STEP 5 — 동선 최적화 (Nearest Neighbor)**

Haversine 거리 기반 Nearest Neighbor 알고리즘으로 방문 순서를 최적화하여 총 이동 거리를 최소화합니다.

**STEP 6 — 일정표 + 교통 안내 생성**

식사 시간대를 고려하여 일정표를 구성합니다. 구간별 교통 수단(도보/버스/지하철)을 거리 기반으로 추천하며, 저상버스 노선·지하철역 편의시설·실시간 혼잡도 정보를 포함합니다.

---

## 📁 Folder Structure


```
.
├── app.py                    # FastAPI 메인 서버 (웹 UI + API)
├── config.py                 # 장애 유형별 프로필, 추천 설정, 경로 설정
├── build_index.py            # FAISS 벡터 인덱스 빌드 스크립트
├── build_bus_mapping.py      # 관광지 ↔ 저상버스 정류장 매핑 스크립트
├── collect.py                # 서울시 실시간 인구 혼잡도 수집 (1시간 주기)
├── collect_barrierfree.py    # 한국관광공사 무장애 관광지 수집
├── collect_restaurants.py    # 한국관광공사 무장애 음식점 수집
├── evaluate_rag.py           # RAG 추천 시스템 성능 평가
├── interactive_rag.py        # 대화형 RAG 테스트 인터페이스
├── requirements.txt          # Python 의존성
├── src/
│   ├── rag/
│   │   └── vector_store.py   # FAISS 벡터 스토어 (빌드/로드/검색)
│   └── recommender/
│       ├── engine.py         # 통합 추천 파이프라인 (6단계)
│       ├── accessibility.py  # 접근성 점수 산출 + 스타일 매칭
│       └── transit.py        # 교통 안내 (지하철/버스/도보) + 혼잡도
└── data/
    ├── seoul_barrierfree.json           # 무장애 관광지 원본
    ├── seoul_barrierfree_with_bus.json   # 관광지 + 저상버스 매핑
    ├── 서울_무장애_음식점.json            # 무장애 음식점
    ├── 서울교통공사_지하철혼잡도정보.json  # 지하철 혼잡도
    ├── 교통약자이용정보.json              # 지하철 편의시설
    ├── 서울시 보행자 출입구 정보.json      # 보행자 출입구
    ├── 서울시 저상버스 도입 노선*.xlsx     # 저상버스 노선 정보
    ├── 서울시버스노선별정류소정보*.xlsx     # 버스 정류소 좌표
    ├── faiss_barrierfree_index/          # FAISS 벡터 인덱스
    ├── main.csv                          # 실시간 인구 데이터
    └── fcst.csv                          # 인구 예측 데이터
```

---

## 🛠️ Installation

```bash
pip install -r requirements.txt
```
추가로 RAG 및 웹 서버 실행에 필요한 패키지를 설치합니다.
```bash
pip install fastapi uvicorn langchain langchain-community faiss-cpu sentence-transformers
```
---
## 🔧 Configuration
`config.py`에서 주요 설정을 관리합니다.
```python
# 임베딩 모델
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# 추천 설정
MAX_SPOTS_PER_DAY = 5          # 1일 최대 추천 장소 수
MAX_TRAVEL_DISTANCE_KM = 10    # 장소 간 최대 이동 거리 (km)
MAX_DAILY_DISTANCE_KM = 30     # 1일 최대 이동 거리 (km)
MAX_DAILY_DISTANCE_ELDERLY_KM = 15  # 노인/휠체어 사용자 제한
```

---

## 🔨 Build
### 1. 데이터 수집 (선택)
무장애 관광지 데이터를 직접 수집하려면 한국관광공사 API 키가 필요합니다.
```bash
# 무장애 관광지 수집
python collect_barrierfree.py
# 무장애 음식점 수집
python collect_restaurants.py
# 저상버스 정류장 매핑
python build_bus_mapping.py
```
### 2. FAISS 벡터 인덱스 빌드
```bash
python build_index.py
```
빌드 시 약 645건의 관광지·음식점 데이터를 벡터화하고 검색 테스트를 수행합니다.

---
## ▶️ Run
FastAPI 서버를 실행합니다.
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
브라우저에서 `http://localhost:8000`에 접속하면 온보딩 UI가 표시됩니다.
### Colab에서 실행
```python
from app import show_in_colab
result = show_in_colab("보행", "2인", "가족과", "역사/문화", "종로구")
```
---
## 🔌 API
### `GET /recommend`
온보딩 파라미터를 받아 추천 코스를 HTML로 반환합니다.
```
GET /recommend?disability_type=보행&group_size=2인&companion=가족과&travel_style=역사/문화
```
### `GET /api/recommend`
동일한 파라미터로 JSON 응답을 반환합니다.
**Response**
```json
{
  "onboarding": {
    "disability_type": "보행",
    "group_size": "2인",
    "companion": "가족과",
    "travel_style": "역사/문화"
  },
  "total_spots": 3,
  "total_distance_km": 4.2,
  "total_time_min": 385,
  "schedule": [
    {
      "order": 1,
      "title": "경복궁",
      "category": "관광지",
      "arrival": "10:00",
      "departure": "11:40",
      "accessibility_score": 8.5,
      "nearest_station": "경복궁",
      "nearest_station_congestion": "보통",
      "transit_to_next": {
        "recommended_transit": "도보",
        "estimated_time_min": 10,
        "accessibility_note": "휠체어 사용 시 엘리베이터가 있는 출입구를 이용하세요."
      }
    }
  ]
}
```
---
## 🏗️ Architecture
```
사용자 온보딩 입력
        │
        ▼
┌─────────────────────┐
│  쿼리 생성           │  장애 유형별 프로필 → 검색 쿼리
│  (build_rag_query)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  FAISS 벡터 검색     │  multilingual MiniLM 임베딩
│  (search_spots)     │  Top-50 유사도 검색
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  접근성 스코어링      │  24개 시설 × 가중치 → 0~10점
│  + 스타일 매칭       │  최소 임계값 필터링
│  (rank_and_filter)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  코스 장소 선정       │  카테고리 비율 + 거리 제한
│  (select_spots)     │  3~4곳 최종 선정
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  동선 최적화         │  Nearest Neighbor (Haversine)
│  (optimize_route)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  일정표 + 교통 안내   │  지하철/버스/도보 + 혼잡도
│  (generate_schedule)│  저상버스 · 역 편의시설 포함
└─────────────────────┘
```
---
## 💡 Why RAG-based Barrier-Free Travel Recommendation?
무장애 여행 추천은 단순히 접근성 높은 장소를 나열하는 것이 아니라, **사용자의 장애 유형에 맞는 편의시설을 갖춘 장소**를 찾고, **이동 가능한 동선으로 연결**하며, **교통 수단의 접근성까지 안내**하는 종합적인 문제입니다.
따라서 본 프로젝트는:
- **RAG**를 통해 645건의 관광지 데이터에서 사용자 맥락에 맞는 장소를 의미 기반으로 검색하고,
- **장애 유형별 접근성 가중치 스코어링**으로 실제 이용 가능한 장소만 필터링하며,
- **Nearest Neighbor 동선 최적화**와 **교통 안내**를 결합하여 실용적인 1일 여행 코스를 자동 생성합니다.
---
## 🙏 Acknowledgement
- 무장애 관광지 데이터: [한국관광공사 무장애 여행 API (KorWithService2)](https://www.data.go.kr)
- 교통 데이터: [서울 열린데이터광장](https://data.seoul.go.kr)
- 임베딩 모델: [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- 벡터 검색: [FAISS (Facebook AI Similarity Search)](https://github.com/facebookresearch/faiss)



