from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from typing import Optional
import datetime

from config import DATABASE_URL

# Меняем postgresql:// на postgresql+asyncpg:// для asyncpg
ASYNC_DB_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Subject(Base):
    """Предметы: Математика, Русский язык, История..."""
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📚")

    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete")


class Topic(Base):
    """Темы внутри предмета: Тригонометрия, Логарифмы..."""
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str] = mapped_column(String(200))

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    notes: Mapped[list["Note"]] = relationship(back_populates="topic", cascade="all, delete")


class Note(Base):
    """Конспекты — храним file_id от Telegram"""
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    title: Mapped[str] = mapped_column(String(300))
    file_id: Mapped[str] = mapped_column(String(500))       # Telegram file_id
    file_type: Mapped[str] = mapped_column(String(20))      # "document" | "photo"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    topic: Mapped["Topic"] = relationship(back_populates="notes")


async def init_db():
    """Создаём таблицы при старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
