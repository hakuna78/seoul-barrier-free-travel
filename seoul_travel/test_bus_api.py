"""
서울시 버스 노선별 정류소 정보 분석
- 저상버스 노선 확인
- 관광지 좌표 기준 반경 내 정류장 탐색 준비
"""
import pandas as pd
import sys
sys.stdout.reconfigure(encoding="utf-8")

# 엑셀 파일 경로 (Colab이면 업로드 후 경로 수정)
EXCEL_FILE = r"C:\Users\user\Desktop\seoul_travel\서울시버스노선별정류소정보(20260108).xlsx"

try:
    df = pd.read_excel(EXCEL_FILE, nrows=5)
    print("=== 컬럼 목록 ===")
    for i, col in enumerate(df.columns):
        print(f"  [{i}] {col}")
    print("\n=== 첫 3행 미리보기 ===")
    print(df.head(3).to_string())
    print(f"\n전체 행 수: {pd.read_excel(EXCEL_FILE).shape[0]}행")
except FileNotFoundError:
    print("파일을 찾을 수 없습니다. 경로를 확인해주세요.")
except Exception as e:
    print(f"에러: {e}")
