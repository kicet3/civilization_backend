from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import game, map, websocket, research, city
from core.config import Settings, prisma_client
import uvicorn
import os
import logging

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

# 라우터 등록
app.include_router(game.router, prefix="/game", tags=["Game"])
app.include_router(map.router, prefix="/map", tags=["Map"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(research.router, prefix="/research", tags=["Research"])
app.include_router(city.router, prefix="/city", tags=["City"])

@app.on_event("startup")
async def startup():
    await prisma_client.connect()

@app.on_event("shutdown")
async def shutdown():
    await prisma_client.disconnect()

@app.get("/")
async def root():
    return {"message": "Welcome to Civilization LLM Game API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)