from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from db.client import prisma

from routers import game, map, websocket, research, city, unit, building
from routers import diplomacy

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행
    print("서버가 시작되었습니다.")
    await prisma.connect()
    yield
    # 애플리케이션 종료 시 실행
    print("서버가 종료되었습니다.")
    await prisma.disconnect()

app = FastAPI(title="Civilization LLM Game API", lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하도록 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 라우터 등록
app.include_router(game.router, prefix="/games", tags=["Game"])
app.include_router(map.router, prefix="/map", tags=["Map"])
app.include_router(unit.router, prefix="/units", tags=["Units"])
app.include_router(research.router, prefix="/technologies", tags=["Technologies"])
app.include_router(building.router, prefix="/buildings", tags=["Buildings"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(diplomacy.router, prefix="/diplomacy", tags=["Diplomacy"])
# app.include_router(city.router, prefix="/city", tags=["City"])

@app.get("/")
async def root():
    return {"message": "문명 게임 서버에 오신 것을 환영합니다!"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": f"서버 오류: {str(exc)}", "data": None},
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
