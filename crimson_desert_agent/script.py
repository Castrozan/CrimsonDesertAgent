from dataclasses import dataclass, field
from typing import Callable

from .virtual_pad import CONTROL_NAMES

MAXIMUM_SECONDS = 120.0
STICK_SIDES = ("left", "right")


class ScriptError(ValueError):
    pass


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


Converter = Callable[[str], object]


@dataclass(frozen=True)
class Signature:
    usage: str
    required: tuple[Converter, ...] = ()
    optional: tuple[Converter, ...] = ()
    rest: Converter | None = None
    minimum_rest: int = 0
    options: dict[str, Converter] = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    verb: str
    values: tuple
    rest: tuple
    options: dict
    text: str


STEERING_OPTIONS = {"tolerance": number, "timeout": seconds}
VERBS = {
    "press": Signature(
        "press CONTROL [HOLD_SECONDS [GAP_SECONDS]]", (control,), (seconds, seconds)
    ),
    "down": Signature("down CONTROL...", rest=control, minimum_rest=1),
    "up": Signature("up CONTROL...", rest=control, minimum_rest=1),
    "stick": Signature("stick left|right RIGHT UP", (stick_side, axis, axis)),
    "release": Signature("release"),
    "wait": Signature("wait SECONDS", (seconds,)),
    "hold": Signature(
        "hold SECONDS CONTROL...", (seconds,), rest=control, minimum_rest=1
    ),
    "move": Signature(
        "move RIGHT FORWARD SECONDS [CONTROL...]", (axis, axis, seconds), rest=control
    ),
    "look": Signature("look RIGHT UP SECONDS", (axis, axis, seconds)),
    "turn": Signature(
        "turn HEADING_DEGREES [tolerance=DEGREES] [timeout=SECONDS]",
        (number,),
        options=STEERING_OPTIONS,
    ),
    "goto": Signature(
        "goto X Z [CONTROL...] [tolerance=METRES] [timeout=SECONDS]",
        (number, number),
        rest=control,
        options=STEERING_OPTIONS,
    ),
    "state": Signature("state"),
    "log": Signature("log"),
    "focus": Signature("focus"),
    "shot": Signature("shot PATH", (path,)),
}
USAGE = "Steps separated by ';' or newlines: " + " | ".join(
    signature.usage for signature in VERBS.values()
)


def parse_step(text: str) -> Step:
    words = text.split()
    verb = words[0]
    signature = VERBS.get(verb)
    if signature is None:
        raise ScriptError(f"unknown step {verb!r}. {USAGE}")
    positional = [word for word in words[1:] if "=" not in word]
    named = [word.split("=", 1) for word in words[1:] if "=" in word]
    fixed = signature.required + signature.optional
    try:
        if len(positional) < len(signature.required):
            raise ValueError("too few arguments")
        values = tuple(convert(word) for convert, word in zip(fixed, positional))
        extra = positional[len(fixed) :]
        if extra and signature.rest is None:
            raise ValueError("too many arguments")
        if len(extra) < signature.minimum_rest:
            raise ValueError("too few arguments")
        rest = tuple(signature.rest(word) for word in extra)
        options = {}
        for name, word in named:
            if name not in signature.options:
                raise ValueError(f"unknown option {name!r}")
            options[name] = signature.options[name](word)
    except ValueError as error:
        raise ScriptError(
            f"bad step {text.strip()!r}: {error}. Usage: {signature.usage}"
        ) from error
    return Step(verb, values, rest, options, " ".join(words))


def parse(script: str) -> list[Step]:
    steps = [
        parse_step(text)
        for text in script.replace("\n", ";").split(";")
        if text.strip()
    ]
    if not steps:
        raise ScriptError(f"empty script. {USAGE}")
    return steps
