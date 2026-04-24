# app/storage/db.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings
from app.storage.models import Base

engine = create_async_engine(f"sqlite+aiosqlite:///{settings.sqlite_path}", echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Migrate existing databases: add new columns if missing
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE rca_reports ADD COLUMN flaky_assessment_json JSON"))
        except Exception:
            pass  # column already exists or table doesn't exist yet

@asynccontextmanager
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

