from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import SessionLocal, Topic, Note

router = Router()


@router.callback_query(F.data.startswith("topic:"))
async def show_notes(callback: CallbackQuery):
    topic_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        topic = await session.get(Topic, topic_id, options=[selectinload(Topic.subject)])
        result = await session.execute(
            select(Note)
            .where(Note.topic_id == topic_id)
            .order_by(Note.title)
        )
        notes = result.scalars().all()

    if not notes:
        await callback.answer("Конспекты ещё не добавлены", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for note in notes:
        builder.button(
            text=f"📄 {note.title}",
            callback_data=f"note:{note.id}"
        )
    builder.button(
        text="◀️ Назад",
        callback_data=f"subject:{topic.subject_id}"
    )
    builder.adjust(1)

    await callback.message.edit_text(
        f"📝 *{topic.name}*\n\nВыбери конспект:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("note:"))
async def send_note(callback: CallbackQuery, bot: Bot):
    note_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        note = await session.get(Note, note_id)

    if not note:
        await callback.answer("Конспект не найден", show_alert=True)
        return

    await callback.answer("Отправляю конспект...")

    if note.file_type == "document":
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=note.file_id,
            caption=f"📄 *{note.title}*",
            parse_mode="Markdown"
        )
    elif note.file_type == "photo":
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=note.file_id,
            caption=f"🖼 *{note.title}*",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "back:start")
async def back_to_start(callback: CallbackQuery):
    from handlers.start import get_subjects_keyboard
    _, keyboard = await get_subjects_keyboard()
    await callback.message.edit_text(
        "📚 Выбери предмет:",
        reply_markup=keyboard
    )
    await callback.answer()
