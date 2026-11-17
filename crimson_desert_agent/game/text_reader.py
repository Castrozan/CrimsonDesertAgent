import pytesseract
from PIL import Image, ImageOps

from ..scripting.hud import Word
from .desktop import DesktopError

UPSCALE = 2
SPARSE_TEXT = "--psm 11"
BRIGHT_TEXT_THRESHOLD = 160


def read_words(frame: Image.Image) -> list[Word]:
    enlarged = frame.convert("L").resize(
        (frame.width * UPSCALE, frame.height * UPSCALE), Image.LANCZOS
    )
    bright_text = ImageOps.autocontrast(enlarged).point(
        lambda level: 255 if level > BRIGHT_TEXT_THRESHOLD else 0
    )
    try:
        table = pytesseract.image_to_data(
            bright_text,
            config=SPARSE_TEXT,
            output_type=pytesseract.Output.DICT,
        )
    except (pytesseract.TesseractError, OSError) as error:
        raise DesktopError(f"text recognition failed: {error}") from error
    return [
        Word(
            text.strip(),
            left // UPSCALE,
            top // UPSCALE,
            (left + width) // UPSCALE,
            float(confidence),
        )
        for text, left, top, width, confidence in zip(
            table["text"], table["left"], table["top"], table["width"], table["conf"]
        )
        if text.strip()
    ]
