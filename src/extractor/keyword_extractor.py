from typing import List, Dict
from kiwipiepy import Kiwi
from collections import Counter

class KeywordExtractor:
    """
    상품명에서 유의미한 키워드(명사)를 추출하고 빈도를 분석하는 클래스
    """
    def __init__(self):
        self.kiwi = Kiwi()
        # 불용어 리스트 (판매 유도 문구 등)
        self.stopwords = {
            '무료배송', '할인', '특가', '당일발송', '기획', '세일', 
            '공구', '이벤트', '증정', '사은품', '프로모션', 
            '한정수량', '신상', '국내생산', '자체제작', '빅사이즈',
            '여성', '여자', '남자', '남성', '무료', '배송'
        }

    def extract_keywords(self, titles: List[str]) -> Dict[str, int]:
        """
        상품명 리스트에서 키워드를 추출하여 빈도수를 계산함
        """
        all_keywords = []

        for title in titles:
            # 형태소 분석
            # NNG(일반명사), NNP(고유명사) 만 추출
            tokens = self.kiwi.analyze(title)
            
            for token_results in tokens:
                for token, tag, _, _ in token_results[0]: # top 1 result
                    if tag in ['NNG', 'NNP']:
                        word = token
                        # 불용어 필터링 및 1글자 제외 (옵션)
                        if word not in self.stopwords and len(word) > 1:
                            all_keywords.append(word)

        # 빈도수 계산
        counter = Counter(all_keywords)
        # 상위 키워드 전체 반환 (호출부에서 top 10 슬라이싱 or 여기서 처리)
        # 요구사항: 상위 10개 상품에서... 등장한 키워드 빈도수 계산. 
        # 여기서는 전체 리스트를 받아 카운트하고, 반환은 전체 딕셔너리로 하되 순서대로 정렬하면 좋음.
        
        # 빈도순 정렬된 딕셔너리 생성
        sorted_keywords = dict(sorted(counter.items(), key=lambda item: item[1], reverse=True))
        
        return sorted_keywords
