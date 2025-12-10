import asyncio
import sys
import pandas as pd
import glob
import os
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup 
from src.scraper.naver_shopping_scraper import NaverShoppingScraper
from src.analyzer.keyword_analyzer import KeywordAnalyzer
import config

from playwright.async_api import async_playwright

class ProductTitleFetcher:
    """
    URL에서 상품명을 추출하고 정제하는 클래스 (Mobile Playwright + iPhone 13 Pro)
    """
    @staticmethod
    async def fetch_and_clean(url: str) -> str:
        # 1. PC URL -> Mobile URL 변환 (속도 및 구조 단순화)
        if "smartstore.naver.com" in url and "m.smartstore.naver.com" not in url:
            url = url.replace("smartstore.naver.com", "m.smartstore.naver.com")
            
        print(f"URL에서 상품명 추출 중 (Mobile Playwright)... {url}")
        title = ""
        
        try:
            async with async_playwright() as p:
                # 2. Device Emulation (Step 1 스크래퍼와 동일한 환경 구성)
                iphone_13 = p.devices['iPhone 13 Pro']
                
                browser = await p.chromium.launch(
                    headless=False, # 보안 우회를 위해 Headless=False 유지
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                context = await browser.new_context(
                    **iphone_13,
                    locale='ko-KR',
                    timezone_id='Asia/Seoul'
                )
                
                # Stealth: navigator.webdriver 숨기기
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = await context.new_page()

                # 3. Resource Optimization (이미지, 폰트 차단으로 속도 향상)
                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "media", "font"] 
                    else route.continue_()
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # 4. Title Extraction
                    # 우선순위 1: Open Graph Meta Tag (가장 깔끔함)
                    og_title_loc = page.locator('meta[property="og:title"]')
                    if await og_title_loc.count() > 0:
                        title = await og_title_loc.first.get_attribute("content")
                    
                    # 우선순위 2: Page Title (Fallback)
                    if not title:
                        title = await page.title()

                except Exception as e:
                    print(f"페이지 로딩 실패 (제목만 가져옵니다): {e}")
                finally:
                    await browser.close()
        except Exception as e:
            print(f"브라우저 실행 실패: {e}")
            return ""

        if not title:
            return ""

        print(f"원천 상품명: {title}")
        return ProductTitleFetcher.clean_title(title)

    @staticmethod
    def clean_title(title: str) -> str:
        # 0. 접미사 정리 (타이틀 태그 등에서 붙는 잡다한 문구 제거)
        # 예: "상품명 : 네이버 쇼핑", "상품명 : 쥴리씨"
        title = re.sub(r' : 네이버.*', '', title)
        title = re.sub(r' : \S+', '', title) # " : 쇼핑몰명" 패턴 제거 시도

        # 1. 괄호 안의 내용 제거 (대괄호 [], 소괄호 ())
        title = re.sub(r'\[.*?\]', '', title)
        title = re.sub(r'\(.*?\)', '', title)
        
        # 2. 스마트스토어 등에서 붙는 접두사/접미사 추가 처리
        title = title.replace("네이버쇼핑", "")

        # 3. 불필요한 공백 정리
        title = " ".join(title.split())
        
        print(f"정제된 키워드: {title}")
        return title

async def main():
    print("=== J-Ops SEO Sniper ===")
    print("1. 검색 키워드 직접 입력")
    print("2. 내 상품 URL 입력 (자동 키워드 추출)")
    
    mode = input("모드를 선택하세요 (1/2): ").strip()
    keyword = ""

    if mode == "1":
        keyword = input("분석할 키워드를 입력하세요: ").strip()
    elif mode == "2":
        url = input("상품 URL을 입력하세요: ").strip()
        if not url.startswith("http"):
            print("올바른 URL을 입력해주세요.")
            return
        keyword = await ProductTitleFetcher.fetch_and_clean(url)
    else:
        print("잘못된 입력입니다.")
        return

    if not keyword:
        print("키워드가 유효하지 않습니다.")
        return

    print(f"\n>>> '{keyword}' 키워드로 분석을 시작합니다...")
    
    # -------------------------------------------------------------
    # Step 1: Scraper Execution
    # -------------------------------------------------------------
    scraper = NaverShoppingScraper(headless=False) # Headless False to avoid blocking
    products = await scraper.search(keyword)
    
    result_filename = ""
    
    if products:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = config.RAW_DATA_DIR / f"results_{timestamp}.csv"
        
        # 상품 리스트 데이터 구성
        data = []
        for idx, product in enumerate(products, 1):
            data.append({
                '순위': idx,
                '상품명': product.title,
                '가격': product.price,
                '쇼핑몰명': product.store_name,
                'URL': product.url,
                'is_ad': product.is_ad,
                '판매자_설정_태그': product.tags
            })
        
        df = pd.DataFrame(data)
        columns = ['순위', '상품명', '가격', '쇼핑몰명', '판매자_설정_태그', 'URL', 'is_ad']
        df = df[columns]
        df.to_csv(result_filename, index=False, encoding="utf-8-sig")
        print(f"\n[Step 1 완료] 수집된 데이터: {len(products)}건 -> {result_filename}")
    else:
        print("상품을 찾을 수 없습니다.")
        return

    # -------------------------------------------------------------
    # Step 2: Keyword Analysis
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # Step 2: Keyword Analysis
    # -------------------------------------------------------------
    print("\n[Step 2 시작] 키워드 분석 중...")
    
    analyzer = KeywordAnalyzer()
    
    # Generate timestamped report filename to avoid Permission denied errors
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Re-generate or reuse? 
    # Better to match the result filename if possible, but simpler to just generate new one or extract from filename
    # Let's extract from result_filename to keep them paired: results_2025... -> keyword_report_2025...
    
    
    report_filename = "keyword_report.csv" # default fallback
    
    # We work with Path objects now
    result_path_obj = result_filename if isinstance(result_filename, Path) else Path(result_filename)
    base_name = result_path_obj.name
    
    if base_name.startswith("results_"):
        report_base = base_name.replace("results_", "keyword_report_")
    else:
        report_base = f"keyword_report_{timestamp}.csv"
        
    report_filename = config.REPORTS_DIR / report_base

    report_path = analyzer.analyze_file(str(result_filename), output_path=str(report_filename))
    
    if report_path:
        print(f"[Step 2 완료] 분석 리포트: {report_path}")
        
        # -------------------------------------------------------------
        # Step 3: Tag Analysis
        # -------------------------------------------------------------
        print("\n[Step 3 시작] 태그 분석 중...")
        tag_report_base = "tag_report.csv"
        if base_name.startswith("results_"):
             tag_report_base = base_name.replace("results_", "tag_report_")
        else:
             tag_report_base = f"tag_report_{timestamp}.csv"
             
        tag_report_filename = config.REPORTS_DIR / tag_report_base
        
        tag_report_path = analyzer.analyze_tags(str(result_filename), output_path=str(tag_report_filename))
        if tag_report_path:
             print(f"[Step 3 완료] 태그 리포트: {tag_report_path}")
        
        # Final Output: Top 10 Keywords + Mention Tags
        try:
            report_df = pd.read_csv(report_path)
            print("\n" + "="*40)
            print(f"📢 '{keyword}' 관련 추천 황금 키워드 TOP 10")
            print("="*40)
            
            top_10 = report_df.head(10)
            for idx, row in top_10.iterrows():
                print(f"{row['순위']}. {row['키워드']} (등장: {row['등장횟수']}회, 관련상품: {row['관련_상품수']}개)")
            print("="*40)
            print(f"※ 상세 데이터: {result_filename}")
            print(f"※ 키워드 보고서: {report_path}")
            print(f"※ 태그 보고서: {tag_report_path}")
            
        except Exception as e:
            print(f"결과 출력 중 오류: {e}")
    else:
        print("키워드 분석에 실패했습니다.")

if __name__ == "__main__":
    try:
        # if sys.platform == 'win32':
        #      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")

