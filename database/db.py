from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, func
import datetime

from config import DATABASE_URL

ASYNC_DB_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    emoji: Mapped[str] = mapped_column(String(10), default="🏫")

    notes: Mapped[list["Note"]] = relationship(back_populates="school", cascade="all, delete")


class UserSchool(Base):
    __tablename__ = "user_schools"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))

    school: Mapped["School"] = relationship()


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📚")

    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str] = mapped_column(String(200))

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    notes: Mapped[list["Note"]] = relationship(back_populates="topic", cascade="all, delete")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    content_type: Mapped[str] = mapped_column(String(10))  # "theory" | "practice"
    title: Mapped[str] = mapped_column(String(300))
    file_id: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(20))  # "document" | "photo"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    topic: Mapped["Topic"] = relationship(back_populates="notes")
    school: Mapped["School"] = relationship(back_populates="notes")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
