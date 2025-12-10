from src.extractor.keyword_extractor import KeywordExtractor

def test_extractor():
    titles = [
        "기모 부츠컷 슬랙스 겨울 여자 바지",
        "무료배송 밍크 기모 팬츠 세일",
        "특가 [기획] 따뜻한 겨울 슬랙스",
        "밴딩 스판 부츠컷 기모 바지 1+1",
        "여자 슬랙스 블랙 부츠컷 하이웨스트"
    ]
    
    print("Test Titles:")
    for t in titles:
        print(f"- {t}")
        
    extractor = KeywordExtractor()
    keywords = extractor.extract_keywords(titles)
    
    print("\nExtracted Keywords (Frequency):")
    for word, count in keywords.items():
        print(f"{word}: {count}")

if __name__ == "__main__":
    test_extractor()
