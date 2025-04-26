from prisma import Prisma

# Prisma 클라이언트 인스턴스 생성
prisma = Prisma()

async def init_prisma():
    await prisma.connect()

async def close_prisma():
    await prisma.disconnect() 