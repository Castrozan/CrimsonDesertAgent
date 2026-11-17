import math
import re

import pytesseract
from PIL import Image, ImageOps

REFERENCE_HEIGHT = 1080.0
CENTRE = (155.0, 944.0)
MAP_RADIUS = 92.0
MINIMUM_MARKER_PIXELS = 12
LABEL_ABOVE_MARKER = (-24.0, -40.0, 22.0, -12.0)
LABEL_UPSCALE = 6
LABEL_THRESHOLDS = (200, 160, 120)
SINGLE_LINE = "--psm 7 -c tessedit_char_whitelist=0123456789m"
DISTANCE = re.compile(r"(\d{1,4})m")


def marker_red(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    return red > 170 and green < 110 and blue < 120 and red - green > 90


def marker_offset(frame: Image.Image) -> tuple[float, float] | None:
    scale = frame.height / REFERENCE_HEIGHT
    radius = MAP_RADIUS * scale
    centre_x, centre_y = CENTRE[0] * scale, CENTRE[1] * scale
    left, top = int(centre_x - radius), int(centre_y - radius)
    patch = frame.crop(
        (left, top, int(centre_x + radius) + 1, int(centre_y + radius) + 1)
    ).convert("RGB")
    pixels = patch.load()
    found = [
        (x, y)
        for x in range(patch.width)
        for y in range(patch.height)
        if math.hypot(x + left - centre_x, y + top - centre_y) <= radius
        and marker_red(pixels[x, y])
    ]
    if len(found) < MINIMUM_MARKER_PIXELS * scale * scale:
        return None
    mean_x = sum(x for x, _ in found) / len(found) + left
    mean_y = sum(y for _, y in found) / len(found) + top
    return ((mean_x - centre_x) / scale, (mean_y - centre_y) / scale)


def marker_metres(frame: Image.Image, offset: tuple[float, float]) -> int | None:
    scale = frame.height / REFERENCE_HEIGHT
    marker_x, marker_y = (
        (CENTRE[0] + offset[0]) * scale,
        (CENTRE[1] + offset[1]) * scale,
    )
    box = tuple(
        int(max(0, origin + edge * scale))
        for origin, edge in zip(
            (marker_x, marker_y, marker_x, marker_y), LABEL_ABOVE_MARKER
        )
    )
    label = frame.crop(box).convert("L")
    enlarged = ImageOps.autocontrast(
        label.resize(
            (label.width * LABEL_UPSCALE, label.height * LABEL_UPSCALE), Image.LANCZOS
        )
    )
    for threshold in LABEL_THRESHOLDS:
        try:
            text = pytesseract.image_to_string(
                enlarged.point(lambda level: 255 if level > threshold else 0),
                config=SINGLE_LINE,
            )
        except (pytesseract.TesseractError, OSError):
            return None
        match = DISTANCE.search(text.replace(" ", ""))
        if match:
            return int(match.group(1))
    return None


def read_marker(frame: Image.Image) -> dict | None:
    offset = marker_offset(frame)
    if offset is None:
        return None
    return {
        "right": round(offset[0], 1),
        "down": round(offset[1], 1),
        "metres": marker_metres(frame, offset),
    }
