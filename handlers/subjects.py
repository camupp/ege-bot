import re

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject, Topic

router = Router()


def short_name(name: str) -> str:
    match = re.search(r'№\d+', name)
    return match.group() if match else name


async def build_topics_keyboard(subject_id: int):
    async with SessionLocal() as session:
        subject = await session.get(Subject, subject_id)
        result = await session.execute(
            select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.id)
        )
        topics = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for topic in topics:
        short = short_name(topic.name)
        builder.button(text=f"📖 {short} · Теория", callback_data=f"topic:{topic.id}:theory")
        builder.button(text=f"✏️ {short} · Практика", callback_data=f"topic:{topic.id}:practice")
    builder.button(text="◀️ Назад", callback_data="back:subjects")
    builder.adjust(1)

    return subject, topics, builder.as_markup()


@router.callback_query(F.data.startswith("subject:"))
async def show_topics(callback: CallbackQuery):
    subject_id = int(callback.data.split(":")[1])
    subject, topics, keyboard = await build_topics_keyboard(subject_id)

    if not topics:
        await callback.answer("Темы ещё не добавлены", show_alert=True)
        return

    await callback.message.edit_text(
        f"{subject.emoji} *{subject.name}*\n\nВыбери тему:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back:topics:"))
async def back_to_topics(callback: CallbackQuery):
    subject_id = int(callback.data.split(":")[2])
    subject, _, keyboard = await build_topics_keyboard(subject_id)

    await callback.message.edit_text(
        f"{subject.emoji} *{subject.name}*\n\nВыбери тему:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()
