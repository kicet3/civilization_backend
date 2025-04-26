from prisma import Prisma
from contextlib import asynccontextmanager

# Prisma 클라이언트 인스턴스 생성
prisma = Prisma()

@asynccontextmanager
async def get_prisma():
    try:
        await prisma.connect()
        yield prisma
    finally:
        await prisma.disconnect() 