"""무장애 여행 RAG - FAISS 벡터 인덱스 빌드"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from src.rag.vector_store import load_barrierfree_data, create_documents, build_vector_store, search_spots

print("=" * 60)
print("무장애 여행 RAG 벡터 인덱스 빌드")
print("=" * 60)

spots = load_barrierfree_data()
print(f"로드된 관광지: {len(spots)}개")

# 카테고리 분포
from collections import Counter
cats = Counter(s.get("category", "?") for s in spots)
print(f"카테고리 분포: {dict(cats)}")

# 접근성 키 분포
acc_keys = Counter()
for s in spots:
    for k in s.get("accessibility", {}).keys():
        acc_keys[k] += 1
print(f"\n접근성 시설 현황 (상위 15개):")
for k, v in acc_keys.most_common(15):
    print(f"  {k}: {v}곳")

# Document 생성
docs = create_documents(spots)
print(f"\n총 {len(docs)}개 Document 생성")

# 벡터 스토어 빌드
vs = build_vector_store(docs)

# 검색 테스트
test_queries = [
    "휠체어 접근 가능한 궁궐 관광지",
    "점자블록 음성안내 시각장애",
    "유모차 수유실 영유아",
    "엘리베이터 노인 편의시설",
]

for q in test_queries:
    results = search_spots(vs, q, k=3)
    print(f"\n검색: '{q}'")
    for r in results:
        print(f"  - {r.metadata['title']} [{r.metadata['category']}] "
              f"(E/V:{r.metadata.get('has_elevator',0)} 점자:{r.metadata.get('has_braille',0)} "
              f"유모차:{r.metadata.get('has_stroller_rental',0)})")

print("\n✅ 벡터 인덱스 빌드 완료!")
