from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject

router = Router()


async def get_subjects_keyboard():
    async with SessionLocal() as session:
        result = await session.execute(select(Subject).order_by(Subject.name))
        subjects = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(
            text=f"{subject.emoji} {subject.name}",
            callback_data=f"subject:{subject.id}"
        )
    builder.adjust(2)
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = await get_subjects_keyboard()
    await message.answer(
        "👋 Привет! Я помогу тебе подготовиться к ЕГЭ.\n\n"
        "📚 Выбери предмет:",
        reply_markup=keyboard
    )
