import os
import re

from ..settings import GAME_LOCK_PATH


class LockRefused(Exception):
    pass


def holder() -> str | None:
    try:
        with open(GAME_LOCK_PATH) as lock_file:
            return lock_file.read().strip() or None
    except FileNotFoundError:
        return None


def held_by(name: str) -> bool:
    current = holder()
    return (
        current is not None
        and re.fullmatch(re.escape(name) + r"( \d\d:\d\d:\d\d)?", current) is not None
    )


def require(name: str | None) -> None:
    if not name:
        raise LockRefused(
            "this changes the shared game: pass the name that holds the game lock"
        )
    if not held_by(name):
        raise LockRefused(
            f"the game lock {GAME_LOCK_PATH} is held by {holder() or 'nobody'}, not {name}; take it first"
        )


def take(name: str, timestamp: str) -> None:
    os.makedirs(os.path.dirname(GAME_LOCK_PATH), exist_ok=True)
    try:
        with open(GAME_LOCK_PATH, "x") as lock_file:
            lock_file.write(f"{name} {timestamp}\n")
    except FileExistsError:
        if not held_by(name):
            raise LockRefused(f"the game lock is held by {holder()}") from None


def release(name: str) -> None:
    if holder() is None:
        return
    require(name)
    os.unlink(GAME_LOCK_PATH)
