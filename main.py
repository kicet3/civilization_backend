from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import game, map, websocket, research, city
import uvicorn
import os
import logging
from db.client import prisma


app = FastAPI(title="Civilization LLM Game API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시 수정 필요
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

# Prisma 초기화 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    await prisma.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await prisma.disconnect()

# 라우터 등록
app.include_router(game.router, prefix="/game", tags=["Game"])
app.include_router(map.router, prefix="/map", tags=["Map"])
# app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
# app.include_router(research.router, prefix="/research", tags=["Research"])
# app.include_router(city.router, prefix="/city", tags=["City"])


@app.get("/")
async def root():
    return {"message": "Welcome to Civilization LLM Game API"}
