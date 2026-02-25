from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models import Manager


# ================= Выбор менеджера (для администратора) =================

def managers_keyboard(managers: list[Manager]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for manager in managers:
        builder.row(
            InlineKeyboardButton(
                text=manager.name,
                callback_data=f"manager:{manager.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="Отмена",
            callback_data="manager:cancel",
        )
    )

    return builder.as_markup()


# ================= Статусы лида (только для менеджеров) =================

def lead_status_keyboard(lead_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🔵 В работе", callback_data=f"status:{lead_id}:in_work")
    builder.button(text="📅 Перезвонить", callback_data=f"status:{lead_id}:callback_later")
    builder.button(text="📞 Нет ответа", callback_data=f"status:{lead_id}:no_answer")
    builder.button(text="❌ Отказ", callback_data=f"status:{lead_id}:rejected")
    builder.button(text="🩺 Консультация", callback_data=f"status:{lead_id}:consult_scheduled")
    builder.button(text="🏥 Операция", callback_data=f"status:{lead_id}:surgery_scheduled")
    builder.button(text="✅ Прооперирован", callback_data=f"status:{lead_id}:operated")

    builder.adjust(2)  # по 2 кнопки в строке

    return builder.as_markup()