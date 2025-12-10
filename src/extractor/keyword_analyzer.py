import pandas as pd
from kiwipiepy import Kiwi
from collections import Counter
from typing import List, Dict, Set
import os

class KeywordAnalyzer:
    """
    수집된 상품 데이터(CSV)를 분석하여 '황금 키워드'를 추출하는 클래스
    """
    def __init__(self):
        self.kiwi = Kiwi()
        # 불용어 리스트 (판매 유도 문구, 배송 관련 등)
        self.stopwords = {
            '무료배송', '할인', '특가', '당일발송', '당일', '출고', '기획', '세일', 
            '공구', '이벤트', '증정', '사은품', '프로모션', '쿠폰', '혜택',
            '한정수량', '신상', '국내생산', '자체제작', '빅사이즈',
            '여성', '여자', '남자', '남성', '무료', '배송', '도착', '보장',
            '추천', '인기', '공식', '정품', '세트', '1+1', '2+1'
        }

    def analyze_file(self, csv_path: str, output_path: str = "keyword_report.csv") -> str:
        """
        CSV 파일을 읽어서 키워드 분석을 수행하고 보고서를 저장함.
        Returns: 저장된 보고서 파일 경로
        """
        print(f"Analyzing file: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            
            if '상품명' not in df.columns or 'is_ad' not in df.columns:
                raise ValueError("CSV 파일에 '상품명' 또는 'is_ad' 컬럼이 없습니다.")
            
            # 0. 광고 상품 제외 (is_ad == True 필터링)
            # CSV reads boolean as string sometimes, so handle that carefully
            # Usually pandas handles 'True'/'False' string to bool automatically if properly formatted, 
            # but let's be safe.
            original_count = len(df)
            df = df[df['is_ad'] != True]
            # Also handle string 'True' just in case
            # df = df[df['is_ad'].astype(str) != 'True'] 
            
            filtered_count = len(df)
            print(f"Ad filtering: {original_count} -> {filtered_count} (Excluded {original_count - filtered_count} ads)")

            titles = df['상품명'].dropna().tolist()
            
            # 1. 키워드 추출 & 빈도 계산
            keyword_counts = Counter()
            keyword_to_titles_map: Dict[str, Set[int]] = {} # 키워드가 포함된 상품 인덱스 추적
            
            for idx, title in enumerate(titles):
                extracted = self._extract_keywords(title)
                for word in extracted:
                    keyword_counts[word] += 1
                    
                    if word not in keyword_to_titles_map:
                        keyword_to_titles_map[word] = set()
                    keyword_to_titles_map[word].add(idx)
            
            # 2. Top 30 선정
            top_30 = keyword_counts.most_common(30)
            
            # 3. 보고서 데이터 생성
            report_data = []
            for rank, (word, freq) in enumerate(top_30, 1):
                related_product_count = len(keyword_to_titles_map.get(word, []))
                report_data.append({
                    '순위': rank,
                    '키워드': word,
                    '등장횟수': freq,
                    '관련_상품수': related_product_count
                })
            
            # 4. CSV 저장
            report_df = pd.DataFrame(report_data)
            report_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            
            print(f"Keyword analysis complete. Report saved to: {output_path}")
            return output_path

        except Exception as e:
            print(f"Error during analysis: {e}")
            return ""


    def verify_tag_report(self, report_path: str):
        """
        태그 리포트 생성 검증
        """
        if os.path.exists(report_path):
            print(f"Tag report verifed at: {report_path}")
        else:
            print(f"Tag report NOT found at: {report_path}")

    def analyze_tags(self, csv_path: str, output_path: str = "tag_report.csv") -> str:
        """
        '판매자_설정_태그' 컬럼을 분석하여 태그 빈도 리포트를 생성함.
        """
        print(f"Analyzing tags from: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            
            if '판매자_설정_태그' not in df.columns:
                print("CSV 파일에 '판매자_설정_태그' 컬럼이 없습니다. 태그 분석을 건너뜁니다.")
                return ""

            # Filter ads first (consistent with keyword analysis)
            if 'is_ad' in df.columns:
                 df = df[df['is_ad'] != True]

            tag_counts = Counter()
            
            # Extract tags
            tags_series = df['판매자_설정_태그'].dropna().astype(str)
            for tags_str in tags_series:
                if not tags_str.strip():
                    continue
                
                # Split by space (since we joined with " ") or find all #... matches
                # Our format is "#Tag1 #Tag2"
                # Simple split/strip
                for tag in tags_str.split():
                    clean_tag = tag.strip()
                    if clean_tag.startswith("#"):
                        # Remove # for counting, or keep it? User asked for "태그명". 
                        # Keeping # makes it clear it's a tag. Let's keep it.
                        tag_counts[clean_tag] += 1
            
            # Data for report
            report_data = []
            # Rank by frequency
            for rank, (tag, freq) in enumerate(tag_counts.most_common(), 1):
                report_data.append({
                    '순위': rank,
                    '태그명': tag,
                    '사용_빈도': freq
                })
            
            # Save CSV
            report_df = pd.DataFrame(report_data)
            report_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            
            print(f"Tag analysis complete. Report saved to: {output_path}")
            return output_path

        except Exception as e:
            print(f"Error during tag analysis: {e}")
            return ""

    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 명사(NNG, NNP)와 외국어(SL)만 추출하고 불용어를 제거함
        """
        keywords = []
        token_results = self.kiwi.analyze(text)
        
        for tokens in token_results:
            for token, tag, _, _ in tokens[0]:
                if tag in ['NNG', 'NNP', 'SL']:
                    word = token
                    # 1글자 제외 (선택사항, 보통 1글자는 의미가 적음) 및 불용어 필터
                    if len(word) > 1 and word not in self.stopwords:
                        keywords.append(word)
        
        return keywords
