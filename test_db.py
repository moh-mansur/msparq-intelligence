import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=True)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM schools"))
        row = result.fetchone()
        print(f"✅ Connected! Schools in database: {row[0]}")
    await engine.dispose()

asyncio.run(test())