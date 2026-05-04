from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject, Topic, Note
from config import ADMIN_IDS

router = Router()


# --- FSM состояния ---
class UploadNote(StatesGroup):
    choosing_subject = State()
    choosing_topic = State()
    entering_title = State()
    waiting_file = State()


class AddSubject(StatesGroup):
    entering_name = State()
    entering_emoji = State()


class AddTopic(StatesGroup):
    choosing_subject = State()
    entering_name = State()


# --- Проверка что это админ ---
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# --- Главное админ меню ---
@router.message(Command("admin"))
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить конспект", callback_data="admin:upload")
    builder.button(text="📚 Добавить предмет", callback_data="admin:add_subject")
    builder.button(text="📝 Добавить тему", callback_data="admin:add_topic")
    builder.adjust(1)

    await message.answer("🛠 *Админ панель*", parse_mode="Markdown", reply_markup=builder.as_markup())


# ========================
# ЗАГРУЗКА КОНСПЕКТА
# ========================

@router.callback_query(F.data == "admin:upload")
async def upload_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    async with SessionLocal() as session:
        result = await session.execute(select(Subject).order_by(Subject.name))
        subjects = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for s in subjects:
        builder.button(text=f"{s.emoji} {s.name}", callback_data=f"upl_subj:{s.id}")
    builder.adjust(2)

    await callback.message.edit_text("Выбери предмет для конспекта:", reply_markup=builder.as_markup())
    await state.set_state(UploadNote.choosing_subject)
    await callback.answer()


@router.callback_query(F.data.startswith("upl_subj:"), UploadNote.choosing_subject)
async def upload_choose_topic(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    await state.update_data(subject_id=subject_id)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.name)
        )
        topics = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for t in topics:
        builder.button(text=f"📝 {t.name}", callback_data=f"upl_topic:{t.id}")
    builder.adjust(1)

    await callback.message.edit_text("Выбери тему:", reply_markup=builder.as_markup())
    await state.set_state(UploadNote.choosing_topic)
    await callback.answer()


@router.callback_query(F.data.startswith("upl_topic:"), UploadNote.choosing_topic)
async def upload_enter_title(callback: CallbackQuery, state: FSMContext):
    topic_id = int(callback.data.split(":")[1])
    await state.update_data(topic_id=topic_id)

    await callback.message.edit_text("Введи название конспекта:")
    await state.set_state(UploadNote.entering_title)
    await callback.answer()


@router.message(UploadNote.entering_title)
async def upload_wait_file(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Теперь отправь файл (PDF, фото или документ):")
    await state.set_state(UploadNote.waiting_file)


@router.message(UploadNote.waiting_file, F.document | F.photo)
async def upload_save_file(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        file_id = message.photo[-1].file_id  # Берём самое высокое качество
        file_type = "photo"

    async with SessionLocal() as session:
        note = Note(
            topic_id=data["topic_id"],
            title=data["title"],
            file_id=file_id,
            file_type=file_type
        )
        session.add(note)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Конспект *{data['title']}* сохранён!", parse_mode="Markdown")


# ========================
# ДОБАВЛЕНИЕ ПРЕДМЕТА
# ========================

@router.callback_query(F.data == "admin:add_subject")
async def add_subject_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("Введи название предмета (например: Математика):")
    await state.set_state(AddSubject.entering_name)
    await callback.answer()


@router.message(AddSubject.entering_name)
async def add_subject_emoji(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введи эмодзи для предмета (например: 📐):")
    await state.set_state(AddSubject.entering_emoji)


@router.message(AddSubject.entering_emoji)
async def add_subject_save(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        subject = Subject(name=data["name"], emoji=message.text)
        session.add(subject)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Предмет *{data['name']}* добавлен!", parse_mode="Markdown")


# ========================
# ДОБАВЛЕНИЕ ТЕМЫ
# ========================

@router.callback_query(F.data == "admin:add_topic")
async def add_topic_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    async with SessionLocal() as session:
        result = await session.execute(select(Subject).order_by(Subject.name))
        subjects = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for s in subjects:
        builder.button(text=f"{s.emoji} {s.name}", callback_data=f"topic_subj:{s.id}")
    builder.adjust(2)

    await callback.message.edit_text("К какому предмету добавить тему?", reply_markup=builder.as_markup())
    await state.set_state(AddTopic.choosing_subject)
    await callback.answer()


@router.callback_query(F.data.startswith("topic_subj:"), AddTopic.choosing_subject)
async def add_topic_name(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    await state.update_data(subject_id=subject_id)
    await callback.message.edit_text("Введи название темы:")
    await state.set_state(AddTopic.entering_name)
    await callback.answer()


@router.message(AddTopic.entering_name)
async def add_topic_save(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        topic = Topic(subject_id=data["subject_id"], name=message.text)
        session.add(topic)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Тема *{message.text}* добавлена!", parse_mode="Markdown")
