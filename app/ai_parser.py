import logging
import re
from typing import Any, Optional


logger = logging.getLogger(__name__)


class AIParserService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model

    async def parse_lead_text(self, raw_text: str) -> dict[str, Any]:
        logger.info(
            "AIParserService.parse_lead_text called, text length=%s",
            len(raw_text) if raw_text else 0,
        )

        if not raw_text:
            return self._empty()

        full_text = self._normalize_text(raw_text)

        # Имя ищем во всём тексте (с fallback)
        name = self._extract_name(full_text)

        # Блок подтверждённых данных
        confirmation_block = self._extract_confirmation_block(full_text)

        if not confirmation_block:
            return {
                "name": name,
                **self._empty_contacts_and_params(),
            }

        contact, contact_type = self._extract_contact(confirmation_block)
        weight, height = self._extract_weight_height(confirmation_block)

        return {
            "name": name,
            "phone": contact if contact_type == "Телефон" else None,
            "contact": contact,
            "contact_type": contact_type,
            "telegram": contact if contact_type == "Telegram" else None,
            "whatsapp": contact if contact_type == "WhatsApp" else None,
            "max": contact if contact_type == "MAX" else None,
            "vk": contact if contact_type == "VK" else None,
            "email": contact if contact_type == "Email" else None,
            "weight_kg": weight,
            "height_cm": height,
        }

    # =====================================================
    # EMPTY
    # =====================================================

    def _empty(self) -> dict[str, Any]:
        return {
            "name": None,
            **self._empty_contacts_and_params(),
        }

    def _empty_contacts_and_params(self) -> dict[str, Any]:
        return {
            "phone": None,
            "contact": None,
            "contact_type": None,
            "telegram": None,
            "whatsapp": None,
            "max": None,
            "vk": None,
            "email": None,
            "weight_kg": None,
            "height_cm": None,
        }

    # =====================================================
    # CONFIRMATION BLOCK
    # =====================================================

    def _extract_confirmation_block(self, text: str) -> Optional[str]:
        marker = "Пожалуйста, подтвердите ваши данные"
        idx = text.lower().find(marker.lower())

        if idx == -1:
            return None

        return text[idx + len(marker):].strip()

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\b\d{1,2}:\d{2}\b", " ", text)
        return text.strip()

    # =====================================================
    # NAME (с fallback)
    # =====================================================

    def _extract_name(self, text: str) -> Optional[str]:
        m = re.search(
            r"(?:\bИмя\b|\bФИО\b)\s*[:\-]?\s*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
            text,
        )
        if m:
            return m.group(1).strip()

        # fallback
        m = re.search(r"\b[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+\b", text)
        return m.group(0) if m else None

    # =====================================================
    # CONTACT (ТОЛЬКО ИЗ CONFIRMATION BLOCK)
    # =====================================================

    def _extract_contact(self, text: str) -> tuple[Optional[str], Optional[str]]:
        low = text.lower()

        # Telegram
        tg = re.search(r"@([a-zA-Z0-9_]{4,32})", text)
        if tg:
            return f"@{tg.group(1)}", "Telegram"

        # Email
        email = re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", text)
        if email:
            return email.group(0), "Email"

        # VK
        vk = re.search(r"(vk\.com/[A-Za-z0-9_\.]+|id\d+)", text)
        if vk:
            return vk.group(0), "VK"

        # Телефон
        phone = re.search(r"(?:\+7|8)\d{10}", text)
        if phone:
            p = self._normalize_phone(phone.group(0))

            if "whatsapp" in low:
                return p, "WhatsApp"
            if "max" in low:
                return p, "MAX"

            return p, "Телефон"

        return None, None

    def _normalize_phone(self, phone: str) -> str:
        digits = re.sub(r"\D", "", phone)

        if digits.startswith("8") and len(digits) == 11:
            return "+7" + digits[1:]
        if digits.startswith("7") and len(digits) == 11:
            return "+7" + digits[1:]

        return phone

    # =====================================================
    # WEIGHT / HEIGHT
    # =====================================================

    def _extract_weight_height(self, text: str) -> tuple[Optional[float], Optional[float]]:
        height = None
        weight = None

        hm = re.search(r"\bРост\s*[:\-]?\s*(\d{2,3})\b", text, re.IGNORECASE)
        if hm:
            v = int(hm.group(1))
            if 120 <= v <= 220:
                height = float(v)

        wm = re.search(r"\bВес\s*[:\-]?\s*(\d{2,3})\b", text, re.IGNORECASE)
        if wm:
            v = int(wm.group(1))
            if 35 <= v <= 300:
                weight = float(v)

        return weight, height