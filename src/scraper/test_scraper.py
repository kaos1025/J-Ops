import asyncio
import logging
from src.scraper.naver_shopping_scraper import NaverShoppingScraper

# 로깅 설정 (스크래퍼 로그 활성화)
logging.basicConfig(level=logging.INFO)

async def test_scraper():
    print("=== NaverShoppingScraper 테스트 시작 ===")
    
    # 1. 인스턴스 생성 (Headless=False로 설정하여 브라우저 동작 확인 권장)
    scraper = NaverShoppingScraper(headless=False)
    
    # 2. 검색 키워드 설정
    keyword = "기모 부츠컷 슬랙스"
    print(f"검색어: {keyword}")
    
    # 3. 크롤링 실행
    try:
        products = await scraper.search(keyword)
        
        print(f"\n=== 테스트 결과: {len(products)}개 상품 발견 ===")
        
        if not products:
            print("❌ 상품을 찾지 못했습니다. 파싱 로직이나 셀렉터를 점검하세요.")
            return

        # 4. 결과 검증
        for i, p in enumerate(products, 1):
            print(f"[{i}] {p.title}")
            print(f"    - 가격: {p.price}원")
            print(f"    - 링크: {p.url}")
            print(f"    - 광고여부: {p.is_ad}")
            
            # 필수 데이터 검증
            if p.price == 0:
                print("    ⚠️ 가격이 0원입니다. (파싱 실패 가능성)")
            if not p.title:
                print("    ❌ 상품명이 비어있습니다.")
                
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"❌ 테스트 중 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
