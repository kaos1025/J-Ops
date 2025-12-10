import google.generativeai as genai
import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import config

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AICopywriter:
    """
    Google Gemini API를 사용하여 쇼핑몰 상품 원고를 생성하는 클래스.
    """
    
    def __init__(self):
        load_dotenv()
        
        self.api_key = os.getenv(config.GENAI_CONFIG["API_KEY_ENV"])
        if not self.api_key:
            logger.error("GOOGLE_API_KEY is not set in environment variables.")
            raise ValueError("GOOGLE_API_KEY is missing via .env")
            
        genai.configure(api_key=self.api_key)
        
        self.model_name = config.GENAI_CONFIG["MODEL_NAME"]
        self.model = genai.GenerativeModel(self.model_name)
        
    def generate_copy(self, product_name: str, keywords: List[str], tags: List[str], image_paths: Optional[List[str]] = None, target_keyword: Optional[str] = None) -> Optional[Dict]:
        """
        Generates marketing copy for a product using Gemini.
        Supports text-only or multimodal (text + image) input.
        Returns a JSON dictionary.
        """
        
        # Prepare inputs
        keywords_str = ", ".join(keywords)
        tags_str = ", ".join(tags)
        
        # Base System Prompt (Persona)
        system_instruction = """
        [Instruction]
        너는 3050 여성을 위한 프리미엄 의류 쇼핑몰 '쥴리씨'의 수석 큐레이터이자 카피라이터다.
        너의 역할은 **'우아한 실용주의'**를 바탕으로 고객의 구매 욕구를 자극하는 것이다.

        **1. SEO 전문가:** 검색량이 많은 키워드를 잡되, '엄마옷', '중년여성의류', '모임룩', '하객룩', '체형커버' 등 연령대에 맞는 고단가 키워드를 조합한다.
        **2. 비주얼 분석가:** 사진을 보고 '고급스러움', '마감 퀄리티', '원단감'을 강조한다.
        **3. 카피라이터 (Ogilvy):** "옷이 아니라 품격을 판다." 고객의 가장 큰 고민인 **'나잇살 커버'와 '편안함'**을 해결해주면서도, **'여전히 아름다운 여성'**임을 일깨워주는 문구를 쓴다.
        **4. 기획자:** [공감(체형고민) -> 해결(핏/소재) -> 신뢰(디테일/마감) -> 제안(코디)] 순서로 논리를 펼친다.

        [Tone & Manner - 중요!]
        - **Target:** 30대 후반 ~ 50대 초반 여성 (구매력 있음, 품질 까다로움)
        - **Voice:**
          - 너무 가볍지 않고 **신뢰감 있는** 어조. (예: "~해요" 보다는 "~하세요", "~랍니다")
          - '언니' 같은 호칭보다는 **'고객님'** 혹은 **'우리 쥴리님들'** 같이 정중하면서 친근하게.
          - 이모지는 과하지 않게, 감성적인 것 위주로 사용 (🌿, ✨, ☕, 🧥).
          - **금기어:** 촌스러운 아줌마 단어 지양, 너무 어린 MZ 용어 절대 금지.

        [Example Comparison]
        - (Bad - 20대용): "대박! 입자마자 힙해지는 뽀글이 가방🔥"
        - (Good - 3050용): "들기만 해도 우아해지는, 가볍고 따뜻한 리얼 양털의 품격 🐑"
        """

        user_prompt = f"""
        아래 정보를 바탕으로 '쥴리씨(Jullyssy)' 쇼핑몰의 상품 원고를 작성해줘.

        [상품 정보]
        - 현재 상품명: {product_name}
        - 참고: 내 상품의 현재 이름은 '{product_name}'인데, '{target_keyword if target_keyword else product_name}' 키워드로 1위를 먹고 싶어.
        - 경쟁사 분석 키워드: {keywords_str}
        - 경쟁사 분석 태그: {tags_str}
        """

        if image_paths and len(image_paths) > 0:
            user_prompt += f"\n- 참고: 첨부된 {len(image_paths[:5])}장의 이미지를 모두 분석해서 원고에 반영해줘 (비주얼 분석가 역할)."

        user_prompt += """
        
        [요청 사항]
        결과는 반드시 아래 JSON 형식으로만 출력해줘 (Markdown 코드 블록 없이 순수 JSON만).

        [출력 포맷]
        {
            "optimized_title": "SEO와 클릭률을 모두 잡은 50자 이내 상품명",
            "main_keywords": ["핵심키워드1", "핵심키워드2", "핵심키워드3"],
            "tags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5", "#태그6", "#태그7", "#태그8", "#태그9", "#태그10"],
            "catch_phrase": "오길비 스타일의 한 줄 헤드라인 (상세페이지 최상단용)",
            "detail_body": "상세페이지 본문 (3단 구성: 공감/문제/해결)",
            "insta_caption": "인스타 업로드용 텍스트 (이모지 포함)"
        }
        """
        
        # Combine instructions
        final_prompt = system_instruction + "\n" + user_prompt

        try:
            logger.info(f"Generating copy for '{product_name}' (Images: {len(image_paths) if image_paths else 0})...")
            
            content_parts = [final_prompt]
            
            # Handle Images (Max 5)
            if image_paths:
                for img_path in image_paths[:5]:
                    if os.path.exists(img_path):
                        try:
                            img_data = {
                                'mime_type': 'image/jpeg',
                                'data': open(img_path, 'rb').read()
                            }
                            content_parts.append(img_data)
                        except Exception as e:
                            logger.error(f"Failed to read image {img_path}: {e}")
                
            response = self.model.generate_content(content_parts)
            
            # Extract text
            text_response = response.text.strip()
            
            # Remove Markdown code blocks if present (```json ... ```)
            if text_response.startswith("```"):
                text_response = text_response.strip("`")
                if text_response.startswith("json"):
                    text_response = text_response[4:].strip()
            
            # Parse JSON
            result_json = json.loads(text_response)
            
            logger.info("Copy generation successful.")
            return result_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {text_response}")
            return None
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return None

if __name__ == "__main__":
    # Test Code
    try:
        writer = AICopywriter()
        test_res = writer.generate_copy(
            "뽀글이 토트백", 
            ["가방", "양털", "겨울"], 
            ["#귀여운", "#데일리"]
        )
        print(json.dumps(test_res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Init failed: {e}")
