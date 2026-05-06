import sys
import os

# Set proper encoding and disable warnings
sys.stdout.reconfigure(encoding="utf-8")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ONBOARDING_TAGS
from src.recommender.engine import recommend

def get_user_choice(prompt: str, options: list) -> str:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    
    while True:
        try:
            choice = input(f"답변: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            else:
                print("잘못된 입력입니다.")
        except ValueError:
            print("숫자를 입력해주세요.")

def main():
    print("=" * 60)
    print("   무장애 여행 RAG 추천 시스템")
    print("=" * 60)

    print("\n여행 설정을 시작합니다. 원하는 옵션을 선택해주세요.")

    disability_type = get_user_choice("장애 유형을 선택하세요:", ONBOARDING_TAGS["disability_type"])
    group_size = get_user_choice("일행 수를 선택하세요:", ONBOARDING_TAGS["group_size"])
    companion = get_user_choice("누구와 함께 여행하시나요?:", ONBOARDING_TAGS["companion"])
    travel_style = get_user_choice("원하는 여행 스타일을 선택하세요:", ONBOARDING_TAGS["travel_style"])

    onboarding = {
        "disability_type": disability_type,
        "group_size": group_size,
        "companion": companion,
        "travel_style": travel_style,
    }

    print("\n" + "=" * 60)
    print("선택된 온보딩 정보:")
    print(f"  장애 유형: {disability_type}")
    print(f"  총 인원 수: {group_size}")
    print(f"  동반자: {companion}")
    print(f"  여행 스타일: {travel_style}")
    print("=" * 60)
    
    print("\n맞춤형 추천 코스를 생성 중입니다. 잠시만 기다려주세요...\n")
    
    # 추천 로직 실행
    recommend(onboarding)
    
if __name__ == "__main__":
    main()
