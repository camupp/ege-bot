from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.db import SessionLocal, Subject, Topic, Note, School
from config import ADMIN_IDS

router = Router()


class UploadNote(StatesGroup):
    choosing_subject = State()
    choosing_topic = State()
    choosing_school = State()
    choosing_content_type = State()
    batch_uploading = State()


class AddSubject(StatesGroup):
    entering_name = State()
    entering_emoji = State()


class AddTopic(StatesGroup):
    choosing_subject = State()
    entering_names = State()


class AddSchool(StatesGroup):
    entering_name = State()
    entering_emoji = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def done_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data="upl_done")
    return builder.as_markup()


@router.message(Command("admin"))
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить конспекты", callback_data="admin:upload")
    builder.button(text="📚 Добавить предмет", callback_data="admin:add_subject")
    builder.button(text="📝 Добавить тему", callback_data="admin:add_topic")
    builder.button(text="🏫 Добавить школу", callback_data="admin:add_school")
    builder.adjust(1)

    await message.answer("🛠 *Админ панель*", parse_mode="Markdown", reply_markup=builder.as_markup())


# ========================
# ЗАГРУЗКА КОНСПЕКТОВ
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

    await callback.message.edit_text("Выбери предмет:", reply_markup=builder.as_markup())
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
        builder.button(text=t.name, callback_data=f"upl_topic:{t.id}")
    builder.adjust(1)

    await callback.message.edit_text("Выбери тему:", reply_markup=builder.as_markup())
    await state.set_state(UploadNote.choosing_topic)
    await callback.answer()


@router.callback_query(F.data.startswith("upl_topic:"), UploadNote.choosing_topic)
async def upload_choose_school(callback: CallbackQuery, state: FSMContext):
    topic_id = int(callback.data.split(":")[1])
    await state.update_data(topic_id=topic_id)

    async with SessionLocal() as session:
        result = await session.execute(select(School).order_by(School.name))
        schools = result.scalars().all()

    builder = InlineKeyboardBuilder()
    for s in schools:
        builder.button(text=f"{s.emoji} {s.name}", callback_data=f"upl_school:{s.id}")
    builder.adjust(1)

    await callback.message.edit_text("Выбери школу:", reply_markup=builder.as_markup())
    await state.set_state(UploadNote.choosing_school)
    await callback.answer()


@router.callback_query(F.data.startswith("upl_school:"), UploadNote.choosing_school)
async def upload_choose_content_type(callback: CallbackQuery, state: FSMContext):
    school_id = int(callback.data.split(":")[1])
    await state.update_data(school_id=school_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Теория", callback_data="upl_type:theory")
    builder.button(text="✏️ Практика", callback_data="upl_type:practice")
    builder.adjust(2)

    await callback.message.edit_text("Теория или практика?", reply_markup=builder.as_markup())
    await state.set_state(UploadNote.choosing_content_type)
    await callback.answer()


@router.callback_query(F.data.startswith("upl_type:"), UploadNote.choosing_content_type)
async def upload_batch_start(callback: CallbackQuery, state: FSMContext):
    content_type = callback.data.split(":")[1]
    await state.update_data(content_type=content_type, count=0)

    await callback.message.edit_text(
        "Отправляй файлы — бот сохранит каждый автоматически.\n"
        "Название берётся из имени файла.\n\n"
        "Когда закончишь — нажми *Готово*.",
        parse_mode="Markdown",
        reply_markup=done_keyboard()
    )
    await state.set_state(UploadNote.batch_uploading)
    await callback.answer()


@router.message(UploadNote.batch_uploading, F.document | F.photo)
async def upload_batch_file(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        title = message.document.file_name or "Конспект"
        # убираем расширение
        if "." in title:
            title = title.rsplit(".", 1)[0]
    else:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        title = f"Фото {data['count'] + 1}"

    async with SessionLocal() as session:
        note = Note(
            topic_id=data["topic_id"],
            school_id=data["school_id"],
            content_type=data["content_type"],
            title=title,
            file_id=file_id,
            file_type=file_type,
        )
        session.add(note)
        await session.commit()

    count = data["count"] + 1
    await state.update_data(count=count)
    await message.reply(f"✅ {count}. {title}", reply_markup=done_keyboard())


@router.callback_query(F.data == "upl_done", UploadNote.batch_uploading)
async def upload_batch_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = data.get("count", 0)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Загрузка завершена. Сохранено конспектов: *{count}*",
        parse_mode="Markdown"
    )
    await callback.answer()


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
async def add_topic_batch_start(callback: CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split(":")[1])
    await state.update_data(subject_id=subject_id, count=0)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data="topic_done")

    await callback.message.edit_text(
        "Отправляй темы по одной — каждая сохраняется сразу.\n\n"
        "Когда закончишь — нажми *Готово*.",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AddTopic.entering_names)
    await callback.answer()


@router.message(AddTopic.entering_names, F.text)
async def add_topic_save_one(message: Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip()

    async with SessionLocal() as session:
        topic = Topic(subject_id=data["subject_id"], name=name)
        session.add(topic)
        await session.commit()

    count = data["count"] + 1
    await state.update_data(count=count)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data="topic_done")
    await message.reply(f"✅ {count}. {name}", reply_markup=builder.as_markup())


@router.callback_query(F.data == "topic_done", AddTopic.entering_names)
async def add_topic_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = data.get("count", 0)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Готово. Добавлено тем: *{count}*",
        parse_mode="Markdown"
    )
    await callback.answer()


# ========================
# ДОБАВЛЕНИЕ ШКОЛЫ
# ========================

@router.callback_query(F.data == "admin:add_school")
async def add_school_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("Введи название школы (например: Умскул):")
    await state.set_state(AddSchool.entering_name)
    await callback.answer()


@router.message(AddSchool.entering_name)
async def add_school_emoji(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введи эмодзи для школы (например: 🎓):")
    await state.set_state(AddSchool.entering_emoji)


@router.message(AddSchool.entering_emoji)
async def add_school_save(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        school = School(name=data["name"], emoji=message.text)
        session.add(school)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Школа *{data['name']}* добавлена!", parse_mode="Markdown")
