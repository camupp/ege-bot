from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject

router = Router()


async def get_subjects(session):
    result = await session.execute(select(Subject).order_by(Subject.name))
    return result.scalars().all()


async def get_subjects_keyboard():
    async with SessionLocal() as session:
        subjects = await get_subjects(session)

    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(
            text=f"{subject.emoji} {subject.name}",
            callback_data=f"subject:{subject.id}"
        )
    builder.adjust(2)
    return subjects, builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    subjects, keyboard = await get_subjects_keyboard()

    if not subjects:
        await message.answer(
            "👋 Привет! Я помогу тебе подготовиться к ЕГЭ.\n\n"
            "😔 Пока предметов нет. Загляни позже!"
        )
        return

    await message.answer(
        "👋 Привет! Я помогу тебе подготовиться к ЕГЭ.\n\n"
        "📚 Выбери предмет:",
        reply_markup=keyboard
    )
