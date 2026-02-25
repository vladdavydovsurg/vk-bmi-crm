import uuid
from dataclasses import dataclass, asdict
from typing import Any, Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_parser import AIParserService
from app.keyboards import managers_keyboard, lead_status_keyboard
from app.models import Lead, Manager, LeadStatus
from app.ocr_service import OCRService
from app.sheets_service import SheetsService


router = Router(name="lead_handlers")


# ================= FSM =================

class LeadFSM(StatesGroup):
    waiting_manager = State()
    waiting_comment = State()


# ================= Draft =================

@dataclass(slots=True)
class LeadDraft:
    id: str
    name: Optional[str]
    contact: Optional[str]
    contact_type: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    bmi: Optional[float]


def calculate_bmi(weight: float | None, height: float | None) -> float | None:
    if not weight or not height:
        return None
    try:
        height_m = height / 100
        return round(weight / (height_m ** 2), 2)
    except Exception:
        return None


# ================= START =================

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет 👋\n\n"
        "Пришли скрин заявки (фото) — я извлеку данные, "
        "дам выбрать менеджера и сохраню лид."
    )


@router.message(Command("chatid"))
async def get_chat_id(message: Message):
    await message.answer(f"Chat ID: {message.chat.id}")


# ================= PHOTO =================

@router.message(F.photo)
async def process_lead_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    ocr_service: OCRService,
    ai_parser: AIParserService,
) -> None:
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    image_bytes = file_bytes.read()

    raw_text = await ocr_service.extract_text(image_bytes)

    if not raw_text.strip():
        await message.answer("Не удалось извлечь текст из изображения.")
        return

    parsed = await ai_parser.parse_lead_text(raw_text)

    weight = float(parsed["weight_kg"]) if parsed.get("weight_kg") else None
    height = float(parsed["height_cm"]) if parsed.get("height_cm") else None
    bmi = calculate_bmi(weight, height)

    contact = None
    contact_type = None

    if parsed.get("phone"):
        contact = parsed["phone"]
        contact_type = "Телефон"
    elif parsed.get("telegram"):
        contact = parsed["telegram"]
        contact_type = "Telegram"
    elif parsed.get("whatsapp"):
        contact = parsed["whatsapp"]
        contact_type = "WhatsApp"
    elif parsed.get("max"):
        contact = parsed["max"]
        contact_type = "MAX"

    draft = LeadDraft(
        id=str(uuid.uuid4()),
        name=parsed.get("name"),
        contact=contact,
        contact_type=contact_type,
        weight_kg=weight,
        height_cm=height,
        bmi=bmi,
    )

    await state.update_data(lead_draft=asdict(draft))

    result = await session.execute(select(Manager).where(Manager.active.is_(True)))
    managers = list(result.scalars().all())

    card_text = (
        f"Имя: {draft.name or '-'}\n"
        f"Контакт ({draft.contact_type or '-'}): {draft.contact or '-'}\n"
        f"Вес: {draft.weight_kg or '-'}\n"
        f"Рост: {draft.height_cm or '-'}\n"
        f"BMI: {draft.bmi or '-'}"
    )

    await message.answer(card_text, reply_markup=managers_keyboard(managers))
    await state.set_state(LeadFSM.waiting_manager)


# ================= MANAGER CHOICE =================

@router.callback_query(LeadFSM.waiting_manager, F.data.startswith("manager:"))
async def choose_manager(callback: CallbackQuery, state: FSMContext):
    if callback.data == "manager:cancel":
        await state.clear()
        await callback.message.answer("Создание лида отменено.")
        await callback.answer()
        return

    manager_id = callback.data.split(":", maxsplit=1)[1]

    await state.update_data(manager_id=manager_id)
    await state.set_state(LeadFSM.waiting_comment)

    await callback.message.answer(
        "Добавить комментарий? Напишите текст или отправьте '-' если без комментария."
    )
    await callback.answer()


# ================= SAVE LEAD =================

@router.message(LeadFSM.waiting_comment)
async def save_lead(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    sheets_service: SheetsService,
):
    data = await state.get_data()
    lead_draft: dict[str, Any] = data.get("lead_draft", {})
    manager_id = data.get("manager_id")

    comment = None if message.text == "-" else message.text

    phone = None
    telegram_username = None
    whatsapp = None
    messenger_max = None
    email = None

    contact = lead_draft.get("contact")
    contact_type = lead_draft.get("contact_type")

    if contact:
        if contact_type == "Телефон":
            phone = contact
        elif contact_type == "Telegram":
            telegram_username = contact
        elif contact_type == "WhatsApp":
            whatsapp = contact
        elif contact_type == "MAX":
            messenger_max = contact

    has_contact = any([phone, telegram_username, whatsapp, messenger_max, email])

    lead = Lead(
        id=uuid.UUID(lead_draft["id"]),
        source="telegram",
        name=lead_draft.get("name") or "-",
        phone=phone,
        telegram_username=telegram_username,
        whatsapp=whatsapp,
        messenger_max=messenger_max,
        email=email,
        weight_kg=lead_draft.get("weight_kg"),
        height_cm=lead_draft.get("height_cm"),
        bmi=lead_draft.get("bmi"),
        lead_type="hot" if has_contact else "cold",
        manager_id=uuid.UUID(manager_id) if has_contact and manager_id else None,
        manager_status=LeadStatus.new,
        comment_from_admin=comment,
        created_by=message.from_user.id if message.from_user else 0,
    )

    session.add(lead)
    await session.commit()
    await session.refresh(lead)

    # -------- получаем менеджера --------
    manager: Manager | None = None
    manager_name: str | None = None

    if lead.manager_id:
        result = await session.execute(select(Manager).where(Manager.id == lead.manager_id))
        manager = result.scalar_one_or_none()
        if manager:
            manager_name = manager.name

    # -------- отправка лида в группу + ссылка на сообщение --------
    tg_message_link: Optional[str] = None

    if manager and manager.manager_group_chat_id:
        contacts = []
        if lead.phone:
            contacts.append(f"📞 Телефон: {lead.phone}")
        if lead.telegram_username:
            contacts.append(f"💬 Telegram: {lead.telegram_username}")
        if lead.whatsapp:
            contacts.append(f"🟢 WhatsApp: {lead.whatsapp}")
        if lead.messenger_max:
            contacts.append(f"🔵 MAX: {lead.messenger_max}")

        sent_message = await message.bot.send_message(
            chat_id=manager.manager_group_chat_id,
            text=(
                "📥 Новый лид\n\n"
                f"Имя: {lead.name}\n\n"
                f"{chr(10).join(contacts) if contacts else 'Нет контактов'}\n\n"
                f"Вес: {lead.weight_kg or '-'}\n"
                f"Рост: {lead.height_cm or '-'}\n"
                f"BMI: {lead.bmi or '-'}\n\n"
                f"Комментарий: {lead.comment_from_admin or 'нет'}\n\n"
                f"🔄 Статус: {lead.manager_status.value}"
            ),
            reply_markup=lead_status_keyboard(str(lead.id)),
        )

        chat_id_str = str(manager.manager_group_chat_id)
        if chat_id_str.startswith("-100"):
            internal_id = chat_id_str[4:]
            tg_message_link = f"https://t.me/c/{internal_id}/{sent_message.message_id}"

    # -------- Google Sheets payload --------
    lead_payload = {
        "id": str(lead.id),
        "created_at": lead.created_at.isoformat(),
        "name": lead.name,
        "phone": lead.phone,
        "telegram_username": lead.telegram_username,
        "whatsapp": lead.whatsapp,
        "messenger_max": lead.messenger_max,
        "email": lead.email,
        "weight_kg": lead.weight_kg,
        "height_cm": lead.height_cm,
        "bmi": lead.bmi,
        "lead_type": lead.lead_type,
        "manager_name": manager_name,
        "manager_status": lead.manager_status.value,
        "comment_from_admin": lead.comment_from_admin,
        "tg_link": tg_message_link,
    }

    await sheets_service.append_to_master(lead_payload)

    if manager and manager.manager_sheet_id:
        await sheets_service.append_to_manager_sheet(
            manager.manager_sheet_id,
            lead_payload,
        )

        # 📊 Ссылка на индивидуальную таблицу менеджера (в ту же группу)
        if manager.manager_group_chat_id:
            manager_sheet_link = f"https://docs.google.com/spreadsheets/d/{manager.manager_sheet_id}"
            await message.bot.send_message(
                chat_id=manager.manager_group_chat_id,
                text=(
                    "📊 Ваша таблица:\n"
                    f"{manager_sheet_link}"
                ),
            )

    await message.answer(f"Лид сохранён. ID: {lead.id}")
    await state.clear()


# ================= UPDATE STATUS =================

@router.callback_query(F.data.startswith("status:"))
async def update_lead_status(
    callback: CallbackQuery,
    session: AsyncSession,
    sheets_service: SheetsService,
):
    try:
        _, lead_id, new_status = callback.data.split(":")
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    result = await session.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
    lead = result.scalar_one_or_none()

    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return

    try:
        lead.manager_status = LeadStatus(new_status)
    except Exception:
        await callback.answer("Некорректный статус", show_alert=True)
        return

    await session.commit()
    await session.refresh(lead)

    await callback.answer("Статус обновлён")

    base_text = (callback.message.text or "").split("🔄 Статус:")[0]

    await callback.message.edit_text(
        base_text + f"\n\n🔄 Статус: {lead.manager_status.value}",
        reply_markup=lead_status_keyboard(str(lead.id)),
    )

    # ------------------- GOOGLE SHEETS -------------------
    try:
        # master
        await sheets_service.update_status_in_sheet(
            sheets_service.master_sheet_id,
            str(lead.id),
            lead.manager_status.value,
        )

        # manager sheet
        if lead.manager_id:
            result = await session.execute(select(Manager).where(Manager.id == lead.manager_id))
            manager = result.scalar_one_or_none()

            if manager and manager.manager_sheet_id:
                await sheets_service.update_status_in_sheet(
                    manager.manager_sheet_id,
                    str(lead.id),
                    lead.manager_status.value,
                )

    except Exception as e:
        print("Ошибка обновления статуса в Google Sheets:", e)