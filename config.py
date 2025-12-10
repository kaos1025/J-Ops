from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
REPORTS_DIR = DATA_DIR / "reports"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# URLs
URLS = {
    "NAVER_SHOPPING_MOBILE": "https://m.shopping.naver.com/search/all",
    "NAVER_MAIN": "https://m.naver.com/",
}

# Selectors & Script IDs
SELECTORS = {
    "NEXT_DATA_SCRIPT": {"id": "__NEXT_DATA__", "type": "application/json"},
    "CAPTCHA_CHECK": [
        "captcha", 
        "wtm_captcha.js", 
        'class="captcha_form"'
    ],
}

# Browser / Playwright Config
BROWSER_CONFIG = {
    "HEADLESS": False, # Default, can be overridden
    "ARGS": ["--disable-blink-features=AutomationControlled"],
    "DEVICE": "iPhone 13 Pro",
    "LOCALE": "ko-KR",
    "TIMEZONE": "Asia/Seoul",
}

# Request Headers
HEADERS = {
    "Referer": "https://m.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Delays & Timeouts (Seconds)
DELAYS = {
    "MIN_REQUEST": 1.0,
    "MAX_REQUEST": 3.0,
    "PAGE_LOAD": 5.0,
    "CAPTCHA_WAIT": 20.0,
    "SCROLL_PAUSE": 2.0,
}

# Settings
SETTINGS = {
    "SCROLL_COUNT": 3,
    "MAX_ITEMS": 20,
}

# AI Writer Config
GENAI_CONFIG = {
    "MODEL_NAME": "gemini-2.5-flash",
    "API_KEY_ENV": "GOOGLE_API_KEY",
}
