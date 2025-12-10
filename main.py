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
from src.writer.ai_copywriter import AICopywriter
import config
import json
from src.scraper.product_fetcher import ProductDataFetcher


async def main():
    print("=== J-Ops SEO Sniper ===")
    print("1. 검색 키워드 직접 입력")
    print("2. 내 상품 URL 입력 (자동 키워드 추출)")
    
    mode = input("모드를 선택하세요 (1/2): ").strip()
    keyword = ""
    product_image_paths = []

    if mode == "1":
        keyword = input("분석할 키워드를 입력하세요: ").strip()
    elif mode == "2":
        url = input("상품 URL을 입력하세요: ").strip()
        if not url.startswith("http"):
            print("올바른 URL을 입력해주세요.")
            return
        fetcher = ProductDataFetcher()
        info = await fetcher.fetch_product_info(url)
        keyword = info["title"]
        product_image_paths = info["image_paths"]
        
        # Select the first image for AI analysis
        product_image_path = product_image_paths[0] if product_image_paths else None
        
        if info['title']:
            print(f"[성공] 상품명: {keyword}", end="")
            if product_image_paths:
                print(f", 이미지 {len(product_image_paths)}장 저장 완료 (대표: {os.path.basename(product_image_path)})")
            else:
                print()
                
            # Mode 2 Refinement: Ask for "Target Keyword" separate from Product Title
            print("-" * 30)
            suggested_keyword = " ".join(keyword.split()[:2])
            target_keyword = input(f"경쟁사를 분석할 '메인 키워드'를 입력하세요 (엔터 시 '{suggested_keyword}' 사용): ").strip()
            
            if not target_keyword:
                target_keyword = suggested_keyword
            
            # Switch the 'keyword' variable to be the 'target_keyword' for the scraper
            product_title = keyword # Backup original title
            keyword = target_keyword # Use target keyword for scraping
            print(f"👉 '{keyword}' 키워드로 경쟁사 분석을 시작합니다.")
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

            # -------------------------------------------------------------
            # Step 4: AI Copywriting
            # -------------------------------------------------------------
            print("\n[Step 4 시작] AI 상품 원고 생성 중...")
            try:
                # Prepare data for AI
                top_10 = report_df.head(10)
                extracted_keywords = top_10['키워드'].tolist()
                
                extracted_tags = []
                if tag_report_path and os.path.exists(tag_report_path):
                    tag_df = pd.read_csv(tag_report_path)
                    extracted_tags = tag_df.head(10)['태그명'].tolist()
                
                # Initialize Writer
                writer = AICopywriter()
                
                # Determine what to pass as 'product_name'
                # If mode 2, we have 'product_title' (my product) and 'keyword' (target keyword)
                # If mode 1, we just have 'keyword'
                
                my_product_name = locals().get('product_title', keyword)
                #print(f"※ 이미지 갯수: {len(product_image_paths)}")
                copy_result = writer.generate_copy(
                    product_name=my_product_name, # My actual product name
                    keywords=extracted_keywords,
                    tags=extracted_tags,
                    image_paths=product_image_paths, # Pass the full list of downloaded images
                    target_keyword=keyword # The keyword I want to rank for
                )
                
                if copy_result:
                    print("\n" + "="*40)
                    print("✨ J-Ops AI 팀장 (6인의 전문가) 제안")
                    print("="*40)
                    print(f"🔹 [SEO] 최적화 상품명: {copy_result.get('optimized_title')}")
                    print(f"🔹 [Keyword] 핵심 키워드: {', '.join(copy_result.get('main_keywords', []))}")
                    print("-" * 20)
                    print(f"🔹 [Ogilvy] 헤드라인: {copy_result.get('catch_phrase')}")
                    print(f"🔹 [Planner] 상세 본문: \n{copy_result.get('detail_body')}")
                    print("-" * 20)
                    print(f"🔹 [Marketing] 인스타 캡션: \n{copy_result.get('insta_caption')}")
                    print(f"🔹 [Algo] 추천 태그: {', '.join(copy_result.get('tags', []))}")
                    print("="*40)
                    
                    # Save AI Result to File
                    ai_report_base = f"ai_report_{timestamp}.json"
                    ai_report_filename = config.REPORTS_DIR / ai_report_base
                    
                    with open(ai_report_filename, 'w', encoding='utf-8') as f:
                        json.dump(copy_result, f, ensure_ascii=False, indent=2)
                    
                    print(f"※ AI 원고 저장 완료: {ai_report_filename}")
                else:
                    print("AI 원고 생성에 실패했습니다 (설정 또는 키 확인 필요).")
                    
            except Exception as e:
                print(f"AI 카피라이터 실행 에러: {e}")
                
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

