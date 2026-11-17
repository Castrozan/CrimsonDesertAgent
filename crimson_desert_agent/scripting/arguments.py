from ..game.virtual_pad import CONTROL_NAMES

MAXIMUM_SECONDS = 120.0
STICK_SIDES = ("left", "right")


def control(word: str) -> str:
    if word not in CONTROL_NAMES:
        raise ValueError(
            f"unknown control {word!r}; controls: {', '.join(CONTROL_NAMES)}"
        )
    return word


def seconds(word: str) -> float:
    value = float(word)
    if not 0.0 <= value <= MAXIMUM_SECONDS:
        raise ValueError(
            f"seconds must be between 0 and {MAXIMUM_SECONDS:g}, got {word}"
        )
    return value


def axis(word: str) -> float:
    value = float(word)
    if not -1.0 <= value <= 1.0:
        raise ValueError(f"stick deflection must be between -1 and 1, got {word}")
    return value


def number(word: str) -> float:
    value = float(word)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"expected a finite number, got {word}")
    return value


def stick_side(word: str) -> str:
    if word not in STICK_SIDES:
        raise ValueError(f"stick must be left or right, got {word!r}")
    return word


def path(word: str) -> str:
    return word


def positive(word: str) -> float:
    value = number(word)
    if value <= 0:
        raise ValueError(f"expected a number above zero, got {word}")
    return value


def count(word: str) -> int:
    value = int(word)
    if not 1 <= value <= 12:
        raise ValueError(f"expected a count from 1 to 12, got {word}")
    return value


def count_of_pixels(word: str) -> int:
    value = int(word)
    if not 16 <= value <= 4096:
        raise ValueError(f"expected 16 to 4096 pixels, got {word}")
    return value


def pixel_box(word: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in word.split(",")]
    if len(parts) != 4 or min(parts) < 0 or parts[2] == 0 or parts[3] == 0:
        raise ValueError(f"expected LEFT,TOP,WIDTH,HEIGHT in pixels, got {word}")
    return (parts[0], parts[1], parts[2], parts[3])
