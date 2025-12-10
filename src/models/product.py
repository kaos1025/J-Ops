from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class Product(BaseModel):
    """
    상품 정보를 담는 데이터 모델
    """
    rank: int = Field(..., description="검색 결과 순위")
    title: str = Field(..., description="상품명")
    store_name: str = Field(..., description="상점명")
    price: int = Field(..., description="가격")
    url: HttpUrl = Field(..., description="상품 상세 페이지 URL")
    is_ad: bool = Field(False, description="광고 상품 여부")
    tags: str = Field("", description="판매자 설정 태그 (없으면 NLP 추출)")

    class Config:
        frozen = True  # 불변 객체로 설정
