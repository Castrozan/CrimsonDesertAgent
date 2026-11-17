from ..scripting.observation import summarize
from .hud_layout import describe
from .screen_lines import lines_from_words


def read_hud(
    camera, read_words, read_marker, read_state, crop: tuple | None = None
) -> dict:
    frame = camera.capture()
    state = summarize(read_state(), 0)
    if crop is None:
        return describe(
            lines_from_words(read_words(frame)), frame.size, state, read_marker(frame)
        )
    left, top, width, height = crop
    words = read_words(frame.crop((left, top, left + width, top + height)))
    return describe(lines_from_words(words, left, top), frame.size, state, None)
