import logging
import pytesseract
from PIL import Image
import io


logger = logging.getLogger(__name__)

# ⚠ Укажи путь к tesseract.exe (если нужно)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRService:
    async def extract_text(self, image_bytes: bytes) -> str:
        try:
            logger.info(
                "OCRService.extract_text called, image size=%s bytes",
                len(image_bytes),
            )

            image = Image.open(io.BytesIO(image_bytes))

            text = pytesseract.image_to_string(
                image,
                lang="rus+eng"
            )

            logger.info("OCR extracted text length=%s", len(text))

            return text

        except Exception as e:
            logger.exception("OCR error: %s", e)
            return ""