import logging
import re
from typing import Any, Optional


logger = logging.getLogger(__name__)


class AIParserService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model

    async def parse_lead_text(self, raw_text: str) -> dict[str, Any]:
        logger.info("AIParserService.parse_lead_text called, text length=%s", len(raw_text))

        if not raw_text:
            return self._empty()

        text = self._normalize_text(raw_text)

        name = self._extract_name(text)
        contact, contact_type = self._extract_contact(text)
        weight, height = self._extract_weight_height(text)

        return {
            "name": name,
            # оставляем совместимость с текущим handlers.py
            "phone": contact,
            # и новые поля
            "contact": contact,
            "contact_type": contact_type,
            "telegram": contact if contact_type == "Telegram" else None,
            "whatsapp": contact if contact_type == "WhatsApp" else None,
            "max": contact if contact_type == "MAX" else None,
            "weight_kg": weight,
            "height_cm": height,
        }

    # =====================================================
    # EMPTY
    # =====================================================

    def _empty(self) -> dict[str, Any]:
        return {
            "name": None,
            "phone": None,
            "contact": None,
            "contact_type": None,
            "telegram": None,
            "whatsapp": None,
            "max": None,
            "weight_kg": None,
            "height_cm": None,
        }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_text(self, text: str) -> str:
        # базовая чистка
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)

        # убираем время 13:43
        text = re.sub(r"\b\d{1,2}:\d{2}\b", " ", text)

        # частые OCR-опечатки по словам
        word_replacements = {
            "Bec": "Вес",
            "BEC": "Вес",
            "BeC": "Вес",
            "PocT": "Рост",
            "Pocr": "Рост",
            "POCT": "Рост",
            "Pocm": "Рост",
            "TeNemoua": "Телефон",
            "TeNemoua.": "Телефон",
        }
        for wrong, correct in word_replacements.items():
            text = text.replace(wrong, correct)

        # нормализация единиц (в OCR часто латиница/мусор)
        # приводим всё к "см" и "кг"
        # cm / cм / cM / см
        text = re.sub(r"(?i)\b(\d{2,3})\s*(cm|cм|cM)\b", r"\1 см", text)
        # kg / kг / kG / kr / кg / Kг
        text = re.sub(r"(?i)\b(\d{2,3})\s*(kg|kг|kG|kr|кg|Kг)\b", r"\1 кг", text)

        # иногда OCR лепит "176cm," -> уберём запятые/точки рядом с единицами
        text = re.sub(r"(\d{2,3})\s*см[,\.;:]", r"\1 см ", text)
        text = re.sub(r"(\d{2,3})\s*кг[,\.;:]", r"\1 кг ", text)

        return text.strip()

    # =====================================================
    # NAME
    # =====================================================

    def _extract_name(self, text: str) -> Optional[str]:
        # "Имя: Алёна Донская" может быть, но чаще встречается просто "Алёна Донская"
        # Берём первое нормальное ФИО из 2 слов.
        m = re.search(r"\b[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+\b", text)
        return m.group(0) if m else None

    # =====================================================
    # CONTACT
    # =====================================================

    def _extract_contact(self, text: str) -> tuple[Optional[str], Optional[str]]:
        low = text.lower()

        # Telegram username
        tg = re.search(r"@([a-zA-Z0-9_]{4,32})", text)
        if tg:
            return f"@{tg.group(1)}", "Telegram"

        # phone +7/8XXXXXXXXXX (без пробелов)
        phone = re.search(r"(?:\+7|8)\d{10}", text)
        if phone:
            p = self._normalize_phone(phone.group(0))

            # если явно упоминается способ связи
            if "whatsapp" in low or "ватсап" in low or "вацап" in low:
                return p, "WhatsApp"
            if "max" in low:
                return p, "MAX"

            return p, "Телефон"

        # если в тексте есть MAX, но контакта не нашли
        if "max" in low:
            return None, "MAX"

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
        height: Optional[float] = None
        weight: Optional[float] = None

        # 1) Явные поля: "Рост 176", "Вес 125"
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

        # 2) Единицы: "176см" / "125кг" (после normalize_text уже "см"/"кг")
        cm = re.search(r"\b(\d{2,3})\s*см\b", text, re.IGNORECASE)
        if cm:
            v = int(cm.group(1))
            if 120 <= v <= 220:
                height = height or float(v)

        kg = re.search(r"\b(\d{2,3})\s*кг\b", text, re.IGNORECASE)
        if kg:
            v = int(kg.group(1))
            if 35 <= v <= 300:
                weight = weight or float(v)

        # 3) Пара "176см, 125кг" / "176 см 125 кг"
        pair_units = re.search(
            r"\b(\d{2,3})\s*см\b\s*[,;]?\s*\b(\d{2,3})\s*кг\b",
            text,
            re.IGNORECASE,
        )
        if pair_units:
            h = int(pair_units.group(1))
            w = int(pair_units.group(2))
            if 120 <= h <= 220 and 35 <= w <= 300:
                height = height or float(h)
                weight = weight or float(w)

        # 4) Форматы "176/125", "176-125", "176 125"
        pair = re.search(r"\b(\d{2,3})\s*[/\-,]\s*(\d{2,3})\b", text)
        if pair:
            n1 = int(pair.group(1))
            n2 = int(pair.group(2))
            if 120 <= n1 <= 220 and 35 <= n2 <= 300:
                height = height or float(n1)
                weight = weight or float(n2)
            elif 120 <= n2 <= 220 and 35 <= n1 <= 300:
                height = height or float(n2)
                weight = weight or float(n1)

        # 5) Fallback: если по словам не нашли, берём числа и пытаемся угадать
        if height is None or weight is None:
            nums = [int(x) for x in re.findall(r"\b(\d{2,3})\b", text)]
            # высота
            if height is None:
                for n in nums:
                    if 120 <= n <= 220:
                        height = float(n)
                        break
            # вес
            if weight is None:
                for n in nums:
                    if 35 <= n <= 300:
                        weight = float(n)
                        break

        return weight, height