from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject, School, UserSchool

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📚 Предметы"), KeyboardButton(text="🏫 Сменить школу")]],
    resize_keyboard=True
)


async def get_schools_keyboard():
    async with SessionLocal() as session:
        result = await session.execute(select(School).order_by(School.name))
        schools = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for school in schools:
        builder.button(text=f"{school.emoji} {school.name}", callback_data=f"school:{school.id}")
    builder.adjust(1)
    return schools, builder.as_markup()


async def get_subjects_keyboard():
    async with SessionLocal() as session:
        result = await session.execute(select(Subject).order_by(Subject.name))
        subjects = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=f"{subject.emoji} {subject.name}", callback_data=f"subject:{subject.id}")
    builder.adjust(2)
    return subjects, builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with SessionLocal() as session:
        user_school = await session.get(UserSchool, message.from_user.id)

    if user_school:
        subjects, keyboard = await get_subjects_keyboard()
        if not subjects:
            await message.answer("😔 Пока предметов нет. Загляни позже!", reply_markup=MAIN_MENU)
            return
        await message.answer("👋 Привет! Я помогу тебе подготовиться к ЕГЭ.", reply_markup=MAIN_MENU)
        await message.answer("📚 Выбери предмет:", reply_markup=keyboard)
    else:
        schools, keyboard = await get_schools_keyboard()
        if not schools:
            await message.answer("😔 Пока школ нет. Загляни позже!")
            return
        await message.answer(
            "👋 Привет! Я помогу тебе подготовиться к ЕГЭ.\n\n🏫 Сначала выбери свою онлайн-школу:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("school:"))
async def select_school(callback: CallbackQuery):
    school_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        user_school = await session.get(UserSchool, callback.from_user.id)
        if user_school:
            user_school.school_id = school_id
        else:
            session.add(UserSchool(user_id=callback.from_user.id, school_id=school_id))
        await session.commit()

    subjects, keyboard = await get_subjects_keyboard()
    if not subjects:
        await callback.message.answer("😔 Пока предметов нет. Загляни позже!", reply_markup=MAIN_MENU)
        await callback.answer()
        return

    await callback.message.answer("✅ Школа выбрана!", reply_markup=MAIN_MENU)
    await callback.message.answer("📚 Выбери предмет:", reply_markup=keyboard)
    await callback.answer()


@router.message(F.text == "📚 Предметы")
async def menu_subjects(message: Message):
    subjects, keyboard = await get_subjects_keyboard()
    if not subjects:
        await message.answer("😔 Пока предметов нет. Загляни позже!")
        return
    await message.answer("📚 Выбери предмет:", reply_markup=keyboard)


@router.message(F.text == "🏫 Сменить школу")
async def menu_change_school(message: Message):
    schools, keyboard = await get_schools_keyboard()
    await message.answer("🏫 Выбери онлайн-школу:", reply_markup=keyboard)


@router.callback_query(F.data == "change_school")
async def change_school(callback: CallbackQuery):
    schools, keyboard = await get_schools_keyboard()
    await callback.message.edit_text("🏫 Выбери онлайн-школу:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back:subjects")
async def back_to_subjects(callback: CallbackQuery):
    subjects, keyboard = await get_subjects_keyboard()
    await callback.message.edit_text("📚 Выбери предмет:", reply_markup=keyboard)
    await callback.answer()
