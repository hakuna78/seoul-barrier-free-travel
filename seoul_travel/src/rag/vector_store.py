"""
무장애 여행 RAG 벡터 스토어
- FAISS 기반 벡터 저장소
- 접근성 메타데이터 필터링 지원
- 한국어 다국어 임베딩
"""
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL, FAISS_INDEX_PATH, SEOUL_TRAVEL_DIR


def load_barrierfree_data():
    """무장애 관광지 JSON 로드 (저상버스 매핑 포함 우선)"""
    bus_path = os.path.join(SEOUL_TRAVEL_DIR, "seoul_barrierfree_with_bus.json")
    plain_path = os.path.join(SEOUL_TRAVEL_DIR, "seoul_barrierfree.json")

    path = bus_path if os.path.exists(bus_path) else plain_path
    if not os.path.exists(path):
        # fallback: data 폴더
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "data", "seoul_barrierfree.json")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_subway_accessibility():
    """지하철 역사 노약자/장애인 편의시설 현황 로드"""
    path = os.path.join(SEOUL_TRAVEL_DIR, "서울시 지하철 역사 노약자 장애인 편의시설 현황.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # {역명: {elvt: N, esclt: N, ...}} 형태로 변환
    result = {}
    for item in data.get("DATA", []):
        name = item.get("sbwy_stns_nm", "")
        result[name] = {
            "line": item.get("sbwy_rout_ln", ""),
            "elevator": item.get("elvt", 0),
            "escalator": item.get("esclt", 0),
            "wheelchair_lift": item.get("whelchr_lift", 0),
        }
    return result


def create_documents(spots: list) -> list:
    """관광지 데이터를 LangChain Document로 변환"""
    documents = []
    for spot in spots:
        accessibility = spot.get("accessibility", {})

        # 접근성 정보 텍스트 생성
        acc_lines = []
        for key, val in accessibility.items():
            acc_lines.append(f"- {key}: {val}")
        acc_text = "\n".join(acc_lines) if acc_lines else "편의시설 정보 없음"

        # 인근 저상버스 정보
        lowbus_text = spot.get("lowbus_text", "")

        # 접근성 키워드 목록 (필터링용)
        acc_keys = ",".join(sorted(accessibility.keys()))

        content = (
            f"[{spot.get('category', '')}] {spot.get('title', '')}\n"
            f"주소: {spot.get('address', '')}\n"
            f"\n[무장애 편의시설]\n{acc_text}\n"
        )
        if lowbus_text:
            content += f"\n[인근 저상버스]\n{lowbus_text}\n"

        doc = Document(
            page_content=content,
            metadata={
                "id": spot.get("id", ""),
                "title": spot.get("title", ""),
                "category": spot.get("category", ""),
                "address": spot.get("address", ""),
                "lat": float(spot.get("latitude", 0)),
                "lng": float(spot.get("longitude", 0)),
                "tel": spot.get("tel", ""),
                "image_url": spot.get("image_url", ""),
                "thumbnail_url": spot.get("thumbnail_url", ""),
                "accessibility_keys": acc_keys,
                "has_elevator": 1 if "엘리베이터" in accessibility else 0,
                "has_ramp": 1 if any("경사로" in str(v) for v in accessibility.values()) else 0,
                "has_braille": 1 if "점자블록" in accessibility else 0,
                "has_audio_guide": 1 if "음성안내" in accessibility else 0,
                "has_sign_language": 1 if "수어안내" in accessibility else 0,
                "has_wheelchair_rental": 1 if "휠체어대여" in accessibility else 0,
                "has_stroller_rental": 1 if "유모차대여" in accessibility else 0,
                "has_nursing_room": 1 if "수유실" in accessibility else 0,
                "has_disabled_toilet": 1 if "장애인화장실" in accessibility else 0,
                "has_guide_dog": 1 if "보조견동반" in accessibility else 0,
                "has_parking": 1 if "주차장" in accessibility else 0,
                "has_baby_facility": 1 if "영유아가족기타" in accessibility else 0,
                "has_lowbus": 1 if spot.get("nearby_lowbus_stops") else 0,
            }
        )
        documents.append(doc)
    return documents


def build_vector_store(documents: list, save: bool = True):
    """FAISS 벡터 스토어 생성"""
    print(f"[INFO] 임베딩 모델 로딩: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    print(f"[INFO] {len(documents)}개 문서 벡터화 중...")
    vectorstore = FAISS.from_documents(documents, embeddings)
    if save:
        os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"[INFO] 벡터 스토어 저장: {FAISS_INDEX_PATH}")
    return vectorstore


def load_vector_store():
    """저장된 벡터 스토어 로드"""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    return FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)


def search_spots(vectorstore, query: str, k: int = 20, filter_dict: dict = None):
    """벡터 유사도 + 메타데이터 필터 검색"""
    search_kwargs = {"k": k}
    if filter_dict:
        search_kwargs["filter"] = filter_dict
    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    return retriever.invoke(query)


if __name__ == "__main__":
    print("=" * 50)
    print("무장애 여행 RAG 벡터 스토어 구축")
    print("=" * 50)
    spots = load_barrierfree_data()
    docs = create_documents(spots)
    print(f"총 {len(docs)}개 Document 생성")
    vs = build_vector_store(docs)
    results = search_spots(vs, "휠체어 접근 가능한 궁궐 관광지")
    print(f"\n검색 결과 (휠체어 접근 가능한 궁궐 관광지):")
    for r in results[:5]:
        print(f"  - {r.metadata['title']} ({r.metadata['category']}) [acc: {r.metadata['accessibility_keys'][:50]}]")
