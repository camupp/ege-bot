from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import SessionLocal, Topic, Note, UserSchool

router = Router()

CONTENT_LABELS = {
    "theory": "📖 Теория",
    "practice": "✏️ Практика",
}


@router.callback_query(F.data.startswith("topic:"))
async def show_notes(callback: CallbackQuery):
    parts = callback.data.split(":")
    topic_id = int(parts[1])
    content_type = parts[2]  # "theory" | "practice"

    async with SessionLocal() as session:
        user_school = await session.get(UserSchool, callback.from_user.id)
        school_id = user_school.school_id if user_school else None

        topic = await session.get(Topic, topic_id, options=[selectinload(Topic.subject)])

        query = (
            select(Note)
            .where(Note.topic_id == topic_id, Note.content_type == content_type)
            .order_by(Note.title)
        )
        if school_id:
            query = query.where(Note.school_id == school_id)

        result = await session.execute(query)
        notes = result.scalars().all()

    if not notes:
        await callback.answer("Конспекты ещё не добавлены", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for note in notes:
        builder.button(text=f"📄 {note.title}", callback_data=f"note:{note.id}")
    builder.button(text="◀️ Назад", callback_data=f"back:topics:{topic.subject_id}")
    builder.adjust(1)

    type_label = CONTENT_LABELS.get(content_type, content_type)
    await callback.message.edit_text(
        f"📝 *{topic.name}* — {type_label}\n\nВыбери конспект:",
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

    nav = InlineKeyboardBuilder()
    nav.button(text="◀️ К списку конспектов", callback_data=f"note_back:{note.topic_id}:{note.content_type}")
    nav.adjust(1)

    if note.file_type == "document":
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=note.file_id,
            caption=f"📄 *{note.title}*",
            parse_mode="Markdown",
            reply_markup=nav.as_markup()
        )
    elif note.file_type == "photo":
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=note.file_id,
            caption=f"🖼 *{note.title}*",
            parse_mode="Markdown",
            reply_markup=nav.as_markup()
        )


@router.callback_query(F.data.startswith("note_back:"))
async def note_back_to_list(callback: CallbackQuery):
    parts = callback.data.split(":")
    topic_id = int(parts[1])
    content_type = parts[2]

    async with SessionLocal() as session:
        user_school = await session.get(UserSchool, callback.from_user.id)
        school_id = user_school.school_id if user_school else None

        topic = await session.get(Topic, topic_id, options=[selectinload(Topic.subject)])

        query = (
            select(Note)
            .where(Note.topic_id == topic_id, Note.content_type == content_type)
            .order_by(Note.title)
        )
        if school_id:
            query = query.where(Note.school_id == school_id)

        result = await session.execute(query)
        notes = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for note in notes:
        builder.button(text=f"📄 {note.title}", callback_data=f"note:{note.id}")
    builder.button(text="◀️ Назад", callback_data=f"back:topics:{topic.subject_id}")
    builder.adjust(1)

    type_label = CONTENT_LABELS.get(content_type, content_type)
    await callback.message.answer(
        f"📝 *{topic.name}* — {type_label}\n\nВыбери конспект:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()
