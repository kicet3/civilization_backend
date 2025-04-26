import os
from pydantic_settings import BaseSettings
from prisma import Prisma

# Prisma 클라이언트를 모듈 레벨에서 생성
prisma_client = Prisma()

class Settings(BaseSettings):
    """애플리케이션 설정"""
    APP_NAME: str = "텍스트 문명 (Text Civilization) API"
    APP_VERSION: str = "0.1.0"
    
    # 데이터베이스 설정
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # 디버그 설정 추가 (기본값은 False)
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 게임 설정
    DEFAULT_MAP_WIDTH: int = 20
    DEFAULT_MAP_HEIGHT: int = 15
    
    # API 설정
    API_PREFIX: str = "/api"
    
    class Config:
        env_file = ".env"
        extra = 'allow'
        case_sensitive = True

# 설정 인스턴스 생성
settings = Settings()

async def setup_app():
    """애플리케이션 초기화"""
    # Prisma 클라이언트 연결
    await prisma_client.connect()
    
    # 추가 초기화 로직이 필요한 경우 여기에 작성
    
    if settings.DEBUG:
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작됨")

async def close_app():
    """애플리케이션 종료"""
    await prisma_client.disconnect()