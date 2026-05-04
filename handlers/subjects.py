from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject, Topic

router = Router()


@router.callback_query(F.data.startswith("subject:"))
async def show_topics(callback: CallbackQuery):
    subject_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        subject = await session.get(Subject, subject_id)
        result = await session.execute(
            select(Topic)
            .where(Topic.subject_id == subject_id)
            .order_by(Topic.name)
        )
        topics = result.scalars().all()

    if not topics:
        await callback.answer("Темы ещё не добавлены", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for topic in topics:
        builder.button(
            text=f"📝 {topic.name}",
            callback_data=f"topic:{topic.id}"
        )
    builder.button(text="◀️ Назад", callback_data="back:start")
    builder.adjust(1)

    await callback.message.edit_text(
        f"{subject.emoji} *{subject.name}*\n\nВыбери тему:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()
