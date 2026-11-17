import io
import os
from PIL import Image, ImageEnhance

from .desktop import DesktopError, game_window_geometry, run_bytes

JPEG_QUALITY = 85


def capture() -> Image.Image:
    geometry = game_window_geometry()
    if geometry is None:
        raise DesktopError("there is no game window to capture")
    return Image.open(
        io.BytesIO(run_bytes(["grim", "-g", geometry, "-t", "ppm", "-"]))
    ).convert("RGB")


def write(
    path: str,
    frames: list[Image.Image],
    boxes: list[tuple[int, int, int, int] | None],
    scale: float,
    brightness: float,
) -> dict:
    tiles = []
    for frame, box in zip(frames, boxes):
        tile = frame
        if box is not None:
            left, top, width, height = box
            tile = tile.crop((left, top, left + width, top + height))
        if brightness != 1.0:
            tile = ImageEnhance.Brightness(tile).enhance(brightness)
        if scale != 1.0:
            tile = tile.resize(
                (max(1, round(tile.width * scale)), max(1, round(tile.height * scale))),
                Image.LANCZOS,
            )
        tiles.append(tile)
    sheet = Image.new(
        "RGB", (sum(tile.width for tile in tiles), max(tile.height for tile in tiles))
    )
    offset = 0
    for tile in tiles:
        sheet.paste(tile, (offset, 0))
        offset += tile.width
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        sheet.save(path, quality=JPEG_QUALITY)
    except (OSError, ValueError) as error:
        raise DesktopError(f"could not write {path}: {error}") from error
    return {
        "path": path,
        "width": sheet.width,
        "height": sheet.height,
        "frames": len(tiles),
    }
