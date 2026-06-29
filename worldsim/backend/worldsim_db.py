import os
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./worldsim.db")
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        for sql in (
            "CREATE INDEX IF NOT EXISTS idx_hexculture_hex ON hexculture(hex_id)",
            "CREATE INDEX IF NOT EXISTS idx_hexculture_nation ON hexculture(nation_id)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_nation_tick ON resourceflowledger(nation_id,tick_number)",
            "CREATE INDEX IF NOT EXISTS idx_deposit_hex_dev ON resourcedeposit(hex_id,developed_by)",
        ):
            await conn.execute(text(sql))

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
