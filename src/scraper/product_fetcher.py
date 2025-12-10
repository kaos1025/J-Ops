import os
import requests
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from playwright.async_api import async_playwright
import config

class ProductDataFetcher:
    """
    URL에서 상품명과 대표 이미지를 추출하고 다운로드하는 클래스.
    """
    
    def __init__(self):
        self.image_dir = config.DATA_DIR / "temp_images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def clean_title(title: str) -> str:
        # 0. 접미사 정리
        title = re.sub(r' : 네이버.*', '', title)
        title = re.sub(r' : \S+', '', title) 

        # 1. 괄호 안의 내용 제거
        title = re.sub(r'\[.*?\]', '', title)
        title = re.sub(r'\(.*?\)', '', title)
        
        # 2. 불필요한 공백 정리
        title = " ".join(title.split())
        return title

    async def fetch_product_info(self, url: str) -> Dict[str, any]:
        """
        Fetches product title and multiple images (gallery + detail) from URL.
        Downloads images to data/temp_images/{product_id}.
        """
        # 1. PC URL -> Mobile URL conversion
        if "smartstore.naver.com" in url and "m.smartstore.naver.com" not in url:
            url = url.replace("smartstore.naver.com", "m.smartstore.naver.com")
            
        print(f"Fetching product info from: {url}")
        
        info = {
            "title": "",
            "image_paths": []
        }

        async with async_playwright() as p:
            # Device config
            iphone_13 = p.devices[config.BROWSER_CONFIG.get("DEVICE", 'iPhone 13 Pro')]
            
            browser = await p.chromium.launch(
                headless=config.BROWSER_CONFIG.get("HEADLESS", False), 
                args=config.BROWSER_CONFIG.get("ARGS", ["--disable-blink-features=AutomationControlled"])
            )
            
            context = await browser.new_context(
                **iphone_13,
                locale=config.BROWSER_CONFIG.get("LOCALE", 'ko-KR'),
                timezone_id=config.BROWSER_CONFIG.get("TIMEZONE", 'Asia/Seoul')
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()

            # Resource Optimization
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["media", "font"] 
                else route.continue_()
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000) # Increased timeout, relaxed wait condition
                
                # 1. Title Extraction
                og_title_loc = page.locator('meta[property="og:title"]')
                if await og_title_loc.count() > 0:
                    raw_title = await og_title_loc.first.get_attribute("content")
                    info["title"] = self.clean_title(raw_title)
                
                if not info["title"]:
                    info["title"] = self.clean_title(await page.title())

                print(f"Title found: {info['title']}")

                # 2. Lazy Load Handling & Scroll
                # Naver often uses 'data-src' or 'data-lazy-src'. Scroll triggers loading.
                print("Scrolling down to load images...")
                
                # Force trigger lazy loads explicitly if elements exist
                await page.evaluate("""() => {
                    const images = document.querySelectorAll('img');
                    images.forEach(img => {
                        if (img.dataset.src) img.src = img.dataset.src;
                        if (img.dataset.lazySrc) img.src = img.dataset.lazySrc;
                    });
                }""")

                last_height = await page.evaluate("document.body.scrollHeight")
                while True:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000) 
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                await page.wait_for_timeout(1500) # Extra wait

                # 3. Extract Image URLs
                image_urls = []
                distinct_urls = set()

                def add_url(u):
                    if not u: return
                    if u.startswith('//'): u = 'https:' + u
                    if u not in distinct_urls:
                        # Filtering
                        if ".gif" in u or "data:image" in u or "type=m" in u: # Filter thumbnails/GIFs
                            return
                        distinct_urls.add(u)
                        image_urls.append(u)

                # Target A: Top Gallery
                # Naver Mobile: Swiper area usually has class like 'swipe_area' or specific generic structure
                # We try to get the 'representative' images first (og:image is good for cover)
                og_image_loc = page.locator('meta[property="og:image"]')
                if await og_image_loc.count() > 0:
                     add_url(await og_image_loc.first.get_attribute("content"))

                # Try to find gallery images (flicker-container, swiper-slide, etc)
                # Naver SmartStore Mobile usually puts main images in `._23RpQU_J` or similar obfuscated classes.
                # Heuristic: Large images at the top of the page.
                
                # Target B: Detail Images (SmartEditor)
                # Usually inside `#INTRODUCE` or `.se-main-container` or `._2E4i2`
                detail_selectors = ["#INTRODUCE", "div.se-main-container", "div._2E4i2", "div.detail_area"]
                
                found_detail = False
                for selector in detail_selectors:
                    if await page.locator(selector).count() > 0:
                        print(f"Scraping detail images from: {selector}")
                        found_detail = True
                        
                        # Get all images in this container
                        # Check both src and data-src
                        imgs = page.locator(f"{selector} img")
                        count = await imgs.count()
                        print(f" - Found {count} img tags in detail section.")
                        
                        for i in range(count):
                            # Try data-src first (high res), then src
                            data_src = await imgs.nth(i).get_attribute("data-src")
                            src = await imgs.nth(i).get_attribute("src")
                            
                            add_url(data_src if data_src else src)
                        break # If we found the main container, stop looking for others to avoid duplication context

                # If no detail images found, try generic fallback (all large images)
                if not found_detail or len(image_urls) <= 1:
                    print("Detail section specific scraping failed/low count. Running generic image sweep...")
                    imgs = page.locator("img")
                    count = await imgs.count()
                    for i in range(count):
                         # Heuristic: Skip small icons (optional, hard without downloading)
                         # We rely on URL filtering (type=m, etc)
                         data_src = await imgs.nth(i).get_attribute("data-src")
                         src = await imgs.nth(i).get_attribute("src")
                         add_url(data_src if data_src else src)

                print(f"Found {len(image_urls)} unique potential images.")

                # 4. Download Images (Max 15)
                if image_urls:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    product_id = timestamp 
                    
                    save_dir = self.image_dir / product_id
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    saved_paths = []
                    download_count = 0
                    
                    for i, img_url in enumerate(image_urls):
                        # if download_count >= 30: break # Limit removed by user request
                        
                        # Clean URL query params for Naver specifically to get better quality if possible?
                        # Naver images often have ?type=... 
                        # If we strip it, we might get original, but sometimes it breaks. 
                        # Safe bet: leave as is or ensure it's not a thumbnail.
                        
                        ext = ".jpg"
                        if ".png" in img_url: ext = ".png"
                        
                        filename = f"image_{download_count+1:02d}{ext}"
                        save_path = save_dir / filename
                        
                        if self._download_image(img_url, save_path):
                            saved_paths.append(str(save_path))
                            download_count += 1
                            print(f"Saved: {filename}")
                            
                    info["image_paths"] = saved_paths
                    print(f"Total {len(saved_paths)} images saved in {save_dir}")

            except Exception as e:
                print(f"Error fetching product inputs: {e}")
            finally:
                await browser.close()
                
        return info

    def _download_image(self, url: str, path: Path) -> bool:
        try:
            # Clean URL if needed (sometimes they have query params resizing them)
            # For Naver, 'type=m200' etc. implies small size. 'type=w750' is better.
            # But changing URL might break it if we don't know the logic. We'll download as is.
            
            response = requests.get(url, stream=True, timeout=5)
            if response.status_code == 200:
                # Check size to filter icons (optional, reading content length)
                # if int(response.headers.get('content-length', 0)) < 5000: return False
                
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
            return False
        except Exception:
            return False
