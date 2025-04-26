from langchain.chat_models import ChatOpenAI
import os

# 환경변수에서 API 키 가져오기 (없으면 기본값 사용)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

# LLM 인스턴스 초기화
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4o-mini",
    temperature=0.7,
    streaming=False,
    max_tokens=512
)

# 프로덕션용 설정 (더 많은 토큰, 낮은 temperature)
production_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-4-turbo",
    temperature=0.2,
    streaming=False,
    max_tokens=1024
)

# 경제적인 설정 (더 적은 비용)
economy_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model_name="gpt-3.5-turbo",
    temperature=0.5,
    streaming=False,
    max_tokens=512
) 