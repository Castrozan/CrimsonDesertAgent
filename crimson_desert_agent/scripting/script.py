from dataclasses import dataclass, field
from itertools import permutations
from typing import Callable

from .arguments import (
    axis,
    control,
    count,
    count_of_pixels,
    number,
    path,
    pixel_box,
    positive,
    seconds,
    stick_side,
)


class ScriptError(ValueError):
    pass


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


MAXIMUM_WORDS_TO_REORDER = 4
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
    "status": Signature("status"),
    "log": Signature("log"),
    "focus": Signature("focus"),
    "shot": Signature(
        "shot PATH [scale=0.5] [crop=LEFT,TOP,WIDTH,HEIGHT] [brightness=1] [burst=FRAMES] [every=SECONDS] "
        "[actor=KEY] [size=PIXELS] [fov=DEGREES]",
        (path,),
        options={
            "scale": positive,
            "crop": pixel_box,
            "brightness": positive,
            "burst": count,
            "every": seconds,
            "actor": path,
            "size": count_of_pixels,
            "fov": positive,
        },
    ),
    "hud": Signature("hud [crop=LEFT,TOP,WIDTH,HEIGHT]", options={"crop": pixel_box}),
    "approach": Signature(
        "approach ACTOR_KEY_OR_NAME [distance=METRES] [timeout=SECONDS]",
        (path,),
        options={"distance": positive, "timeout": seconds},
    ),
    "talk": Signature(
        "talk ACTOR_KEY_OR_NAME [timeout=SECONDS]",
        (path,),
        options={"timeout": seconds},
    ),
    "marker": Signature("marker [timeout=SECONDS]", options={"timeout": seconds}),
    "prove_attack": Signature(
        "prove_attack [CONTROL] [wait=SECONDS]",
        optional=(control,),
        options={"wait": seconds},
    ),
    "fight": Signature(
        "fight ANCHOR_X ANCHOR_Z [seconds=20] [leash=METRES]",
        (number, number),
        options={"seconds": seconds, "leash": positive},
    ),
    "climb": Signature("climb [seconds=12]", options={"seconds": seconds}),
    "hazard": Signature("hazard X Z", (number, number)),
    "teach": Signature("teach [timeout=SECONDS]", options={"timeout": seconds}),
}
USAGE = "Steps separated by ';' or newlines: " + " | ".join(
    signature.usage for signature in VERBS.values()
)


def convert(signature: Signature, verb: str, words: list[str]) -> Step:
    positional = [word for word in words if "=" not in word]
    named = [word.split("=", 1) for word in words if "=" in word]
    fixed = signature.required + signature.optional
    if len(positional) < len(signature.required):
        raise ValueError("too few arguments")
    values = tuple(convert_word(word) for convert_word, word in zip(fixed, positional))
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
    return Step(verb, values, rest, options, " ".join([verb, *words]))


def reordered_hint(signature: Signature, verb: str, words: list[str]) -> str:
    if len(words) > MAXIMUM_WORDS_TO_REORDER:
        return ""
    for order in permutations(words):
        try:
            convert(signature, verb, list(order))
        except ValueError:
            continue
        return f" Did you mean {' '.join([verb, *order])!r}?"
    return ""


def parse_step(text: str) -> Step:
    verb, *words = text.split()
    signature = VERBS.get(verb)
    if signature is None:
        raise ScriptError(f"unknown step {verb!r}. {USAGE}")
    try:
        return convert(signature, verb, words)
    except ValueError as error:
        hint = reordered_hint(signature, verb, words)
        raise ScriptError(
            f"bad step {text.strip()!r}: {error}.{hint} Usage: {signature.usage}"
        ) from error


def parse(script: str) -> list[Step]:
    steps = [
        parse_step(text)
        for text in script.replace("\n", ";").split(";")
        if text.strip()
    ]
    if not steps:
        raise ScriptError(f"empty script. {USAGE}")
    return steps
