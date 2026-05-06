"""
무장애 여행 RAG 성능 평가
- 6가지 장애 유형 × 4가지 여행 스타일 시나리오
- 접근성 점수, 동선, 카테고리 매칭 검증
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from src.recommender.engine import recommend

# ============================================================
# 테스트 시나리오
# ============================================================
SCENARIOS = [
    {
        "name": "시나리오 A: 휠체어 사용자 + 역사문화 탐방",
        "onboarding": {
            "disability_type": "보행",
            "group_size": "2인",
            "companion": "가족과",
            "travel_style": "역사/문화",
        },
    },
    {
        "name": "시나리오 B: 시각장애인 + 힐링 여행",
        "onboarding": {
            "disability_type": "시각",
            "group_size": "2인",
            "companion": "혼자",
            "travel_style": "힐링",
        },
    },
    {
        "name": "시나리오 C: 영유아 동반 가족 + 쇼핑",
        "onboarding": {
            "disability_type": "유아동반",
            "group_size": "4인이상",
            "companion": "가족과",
            "travel_style": "쇼핑",
        },
    },
    {
        "name": "시나리오 D: 고령자 부부 + 미식 투어",
        "onboarding": {
            "disability_type": "노인",
            "group_size": "2인",
            "companion": "커플",
            "travel_style": "미식",
        },
    },
    {
        "name": "시나리오 E: 청각장애 친구 그룹 + 역사/문화",
        "onboarding": {
            "disability_type": "청각",
            "group_size": "3인",
            "companion": "친구와",
            "travel_style": "역사/문화",
        },
    },
    {
        "name": "시나리오 F: 지적장애 + 힐링",
        "onboarding": {
            "disability_type": "지적",
            "group_size": "2인",
            "companion": "가족과",
            "travel_style": "힐링",
        },
    },
]


def run_evaluation():
    print("=" * 70)
    print("   무장애 여행 RAG 추천 시스템 - 성능 평가")
    print("=" * 70)

    results_summary = []

    for scenario in SCENARIOS:
        print(f"\n\n{'#'*70}")
        print(f"  {scenario['name']}")
        print(f"{'#'*70}")

        result = recommend(scenario["onboarding"])

        # 품질 지표 계산
        avg_acc = 0
        if result["schedule"]:
            avg_acc = sum(s["accessibility_score"] for s in result["schedule"]) / len(result["schedule"])

        style_cats = []
        from config import STYLE_CATEGORY_MAP
        target_cats = STYLE_CATEGORY_MAP.get(scenario["onboarding"]["travel_style"], [])
        cat_match = 0
        for s in result["schedule"]:
            if s["category"] in target_cats:
                cat_match += 1
        cat_match_rate = cat_match / len(result["schedule"]) * 100 if result["schedule"] else 0

        summary = {
            "scenario": scenario["name"],
            "disability": scenario["onboarding"]["disability_type"],
            "style": scenario["onboarding"]["travel_style"],
            "spots": result["total_spots"],
            "avg_accessibility": round(avg_acc, 1),
            "category_match_rate": round(cat_match_rate, 1),
            "total_distance_km": result["total_distance_km"],
            "total_time_min": result["total_time_min"],
        }
        results_summary.append(summary)

    # ============================================================
    # 종합 요약
    # ============================================================
    print(f"\n\n{'='*70}")
    print(f"   종합 평가 결과")
    print(f"{'='*70}")
    print(f"\n{'시나리오':<40} {'장소':>4} {'접근성':>6} {'스타일%':>7} {'거리km':>7} {'시간':>6}")
    print("-" * 70)
    for s in results_summary:
        print(f"{s['scenario']:<38} {s['spots']:>4} "
              f"{s['avg_accessibility']:>6.1f} {s['category_match_rate']:>6.1f}% "
              f"{s['total_distance_km']:>6.1f} {s['total_time_min']:>5}분")

    # 평균
    if results_summary:
        avg_spots = sum(s["spots"] for s in results_summary) / len(results_summary)
        avg_acc = sum(s["avg_accessibility"] for s in results_summary) / len(results_summary)
        avg_cat = sum(s["category_match_rate"] for s in results_summary) / len(results_summary)
        avg_dist = sum(s["total_distance_km"] for s in results_summary) / len(results_summary)
        print("-" * 70)
        print(f"{'평균':<38} {avg_spots:>4.0f} "
              f"{avg_acc:>6.1f} {avg_cat:>6.1f}% "
              f"{avg_dist:>6.1f}")

    return results_summary


if __name__ == "__main__":
    run_evaluation()
