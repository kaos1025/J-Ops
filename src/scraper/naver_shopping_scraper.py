import asyncio
import logging
import json
import random
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from src.models.product import Product

from kiwipiepy import Kiwi

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import config

class NaverShoppingScraper:
    """
    네이버 쇼핑 검색 결과를 크롤링하는 클래스
    __NEXT_DATA__ JSON 직접 추출 방식 (Direct JSON Extraction)
    """
    BASE_URL = config.URLS["NAVER_SHOPPING_MOBILE"]

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.kiwi = Kiwi() # Initialize Kiwi for NLP fallback

    async def search(self, keyword: str) -> List[Product]:
        """
        키워드로 상품을 검색하고 상위 10개 결과를 반환함 (JSON Extraction)
        """
        logger.info(f"검색 시작: {keyword}")
        results: List[Product] = []

        async with async_playwright() as p:
            # 1. Device Emulation
            iphone_13 = p.devices[config.BROWSER_CONFIG["DEVICE"]]
            
            browser = await p.chromium.launch(
                headless=self.headless, 
                slow_mo=1000,
                args=config.BROWSER_CONFIG["ARGS"]
            )
            
            context = await browser.new_context(
                **iphone_13,
                locale=config.BROWSER_CONFIG["LOCALE"],
                timezone_id=config.BROWSER_CONFIG["TIMEZONE"]
            )
            
            # Stealth: navigator.webdriver 숨기기
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()

            try:
                # Random Delay
                delay = random.uniform(config.DELAYS["MIN_REQUEST"], config.DELAYS["MAX_REQUEST"])
                logger.info(f"요청 전 {delay:.2f}초 대기...")
                await asyncio.sleep(delay)

                # URL Load
                url = f"{self.BASE_URL}?query={keyword}&productSet=total"
                await page.set_extra_http_headers(config.HEADERS)
                
                await page.goto(url, wait_until='domcontentloaded')
                
                logger.info("페이지 로딩 확인을 위해 5초 대기...")
                await page.wait_for_timeout(5000)
                
                # Check Captcha
                page_content_str = await page.content()
                if "captcha" in await page.title() or "wtm_captcha.js" in page_content_str or 'class="captcha_form"' in page_content_str:
                    logger.warning("캡차 감지. 해결 대기.")
                    if not self.headless:
                        await asyncio.sleep(20)
                    else:
                        return []

                # Scroll for lazy loading (though __NEXT_DATA__ usually has initial batch)
                logger.info("스크롤 다운 실행...")
                scroll_count = config.SETTINGS.get("SCROLL_COUNT", 3)
                for _ in range(scroll_count):
                    await page.keyboard.press("End")
                    await asyncio.sleep(2)

                # ---------------------------------------------------------
                # Direct JSON Extraction Strategy
                # ---------------------------------------------------------
                logger.info("JSON 데이터 추출 시작 (__NEXT_DATA__)...")
                
                # 1. Get Full HTML & Parse with BeautifulSoup
                html_source = await page.content()
                soup = BeautifulSoup(html_source, 'html.parser')

                # 2. Find __NEXT_DATA__ script
                script_conf = config.SELECTORS["NEXT_DATA_SCRIPT"]
                script_tag = soup.find("script", {"id": script_conf["id"], "type": script_conf["type"]})
                
                if script_tag:
                    try:
                        # 3. Parse JSON
                        json_str = script_tag.string
                        data = json.loads(json_str)
                        
                        # 4. Traverse Data Path (Based on deep scan)
                        product_list = []
                        page_props = data.get("props", {}).get("pageProps", {})

                        # Priority 1: Main Search Results (compositeProducts)
                        composite_products = page_props.get("compositeProducts", {})
                        if composite_products.get("list"):
                            product_list = composite_products.get("list")
                            logger.info(f"compositeProducts에서 상품 리스트 발견! ({len(product_list)}개)")

                        # Priority 2: Super Saving Products (Fallback)
                        if not product_list and page_props.get("superSavingProducts"):
                            product_list = page_props.get("superSavingProducts")
                            logger.info(f"superSavingProducts에서 상품 리스트 발견! ({len(product_list)}개)")

                        # Priority 3: Old Logic/Dehydrated State (Just in case)
                        if not product_list:
                            # ... (Keep or discard? Discard for cleanliness as per 'discard legacy' instruction)
                            pass

                        logger.info(f"JSON 데이터 확인: {len(product_list)}개 아이템 발견")

                        count = 0
                        max_items = config.SETTINGS.get("MAX_ITEMS", 20)
                        for item in product_list:
                            if count >= max_items:
                                break
                            
                            # 'item' key inside the list element usually holds the core data
                            # Structure might be: { "item": { ... }, ... }
                            core_item = item.get("item", item) # Fallback to self if 'item' key missing

                            # Extract Fields
                            title = core_item.get("productTitle") or core_item.get("productName") or core_item.get("title", "")
                            price_raw = core_item.get("lowPrice") or core_item.get("price", 0)
                            price = int(price_raw)
                            
                            store_name = core_item.get("mallName", "Unknown")
                            
                            # URL & Ad Logic
                            # URL & Ad Logic
                            ad_id = core_item.get("adId")
                            ad_url = core_item.get("adcrUrl")
                            is_ad = bool(ad_id or ad_url)
                            
                            # Organic Only Filter: Skip valid ads
                            if is_ad:
                                # logger.info(f"광고 상품 제외: {title}")
                                continue

                            pid = core_item.get("id")
                            mall_url = core_item.get("mallProductUrl")

                            # Determine Final URL
                            final_url = ""
                            if ad_url:
                                final_url = ad_url if ad_url.startswith("http") else f"https://m.shopping.naver.com{ad_url}"
                            elif mall_url:
                                final_url = mall_url
                            else:
                                final_url = f"https://m.shopping.naver.com/product/{pid}"

                            if title:
                                # -------------------------------------------------
                                # Tag Extraction & NLP Fallback Logic
                                # -------------------------------------------------
                                extracted_tags = []
                                
                                # Debug: Log keys for the very first item (organic)
                                if count == 0:
                                    logger.info(f"First Organic Item Keys: {list(core_item.keys())}")

                                # 1. Try to extract from known JSON fields
                                # Candidate keys based on common Naver patterns
                                tag_candidates = []
                                
                                # 'tags' might be a list of strings or list of dicts
                                if core_item.get("tags"):
                                    tag_val = core_item.get("tags")
                                    if isinstance(tag_val, list):
                                        if tag_val and isinstance(tag_val[0], str):
                                             tag_candidates.extend(tag_val)
                                        elif tag_val and isinstance(tag_val[0], dict):
                                             # Sometimes tags are [{'tagName': '...'}, ...]
                                             tag_candidates.extend([t.get('tagName') for t in tag_val if t.get('tagName')])

                                if core_item.get("keywords"):
                                    tag_candidates.extend(core_item.get("keywords", []))
                                
                                if core_item.get("hashTags"):
                                    tag_candidates.extend(core_item.get("hashTags", []))

                                if core_item.get("openTags"):
                                    tag_candidates.extend(core_item.get("openTags", []))
                                
                                # 'attribute' or 'spec' often contains "기모", "밴딩" etc.
                                if core_item.get("attribute"): # e.g. "기모|밴딩"
                                    attrs = core_item.get("attribute")
                                    if isinstance(attrs, str):
                                        tag_candidates.extend(attrs.split('|'))
                                    elif isinstance(attrs, list):
                                        tag_candidates.extend(attrs)

                                # Clean and deduplicate tags
                                clean_tags = []
                                for t in tag_candidates:
                                    if t and isinstance(t, str):
                                        clean_tags.append(t.strip())
                                
                                # 2. Fallback: NLP (Kiwi) if no tags found
                                if not clean_tags:
                                    # Use Kiwi to extract nouns from title
                                    # Initialize Kiwi locally ensuring it doesn't block too much or reuse usage if possible
                                    # For performance, maybe we initialize it once in __init__ but we are in async method...
                                    # Let's rely on the instance's Kiwi initialized in __init__
                                    try:
                                        keywords = self.kiwi.tokenize(title, normalize_coda=True)
                                        # Filter Noun-like tags
                                        for token in keywords:
                                            if token.tag in ['NNG', 'NNP', 'SL', 'XR'] and len(token.form) > 1:
                                                # Manually filter stopwords if needed, or rely on downstream analyzer
                                                clean_tags.append(token.form)
                                    except Exception as e:
                                        logger.warning(f"Kiwi NLP Fallback Error: {e}")

                                # Format as String "#Tag1 #Tag2"
                                # Unique tags only
                                unique_tags = list(dict.fromkeys(clean_tags)) # preserve order
                                final_tags_str = " ".join([f"#{t}" for t in unique_tags])

                                results.append(Product(
                                    rank=count + 1, # Organic Rank
                                    title=title,
                                    store_name=store_name,
                                    price=price,
                                    url=final_url,
                                    is_ad=is_ad,
                                    tags=final_tags_str
                                ))
                                logger.info(f"[Organic #{count+1}] {title} / {price}원 / Tags: {final_tags_str}")
                                print(f"Found: [{title}] - [{price}원] - Tags: {final_tags_str[:30]}...")
                                count += 1
                                
                    except Exception as e:
                        logger.error(f"JSON 파싱 중 에러: {e}")
                else:
                    logger.warning("__NEXT_DATA__ 스크립트를 찾을 수 없습니다!")
                    # Debug save
                    with open("debug_fail_nextdata.html", "w", encoding="utf-8") as f:
                        f.write(soup.prettify())

            except Exception as e:
                logger.error(f"크롤링 전체 에러: {e}")
            finally:
                await browser.close()
                
        return results
