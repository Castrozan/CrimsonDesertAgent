import math
import re

MERGE_WITHIN_M = 1.0
PERSON_NAME = re.compile(r"^[A-Z][a-z]{2,}( [A-Z][a-z]+)?$")
NOT_NAMES = frozenset(
    {"Talk", "Next", "Skip", "Day", "Trust", "Close", "Confirm", "Interact"}
)


def name_in(texts: list[str]) -> str | None:
    for text in texts:
        if PERSON_NAME.match(text) and text.split()[0] not in NOT_NAMES:
            return text
    return None


class Acquaintances:
    def __init__(self) -> None:
        self._names: dict[str, str] = {}
        self._talked: set[str] = set()

    def learn(self, key: str, name: str | None) -> None:
        if name:
            self._names[str(key)] = name

    def mark_talked(self, key: str) -> None:
        self._talked.add(str(key))

    def key_for(self, word: str) -> str:
        for key, name in self._names.items():
            if name.lower() == word.lower():
                return key
        return word

    def annotate(self, actors: list[dict]) -> list[dict]:
        kept: list[dict] = []
        for actor in actors:
            position = actor.get("position")
            twin = next(
                (
                    other
                    for other in kept
                    if position
                    and other.get("position")
                    and math.dist(position, other["position"]) <= MERGE_WITHIN_M
                    and other.get("kind") == actor.get("kind")
                ),
                None,
            )
            if twin is not None:
                twin["stacked"] = twin.get("stacked", 1) + 1
                continue
            described = dict(actor)
            key = str(actor.get("key"))
            if key in self._names:
                described["name"] = self._names[key]
            if key in self._talked:
                described["talked"] = True
            kept.append(described)
        return kept
