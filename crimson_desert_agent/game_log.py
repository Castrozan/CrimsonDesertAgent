import os
import re

ROUTINE_LINES = re.compile(
    r"Timing:|Overlay|Net: connected|co-op: other|Local: pos|Suppress:|Enemy relay: the guest|Agent bridge: client"
)
MAXIMUM_LINES = 40
MAXIMUM_LINE_LENGTH = 220


class GameLog:
    def __init__(self, path: str) -> None:
        self._path = path
        self._offset = os.path.getsize(path) if os.path.exists(path) else 0

    def new_lines(self) -> list[str]:
        if not os.path.exists(self._path):
            return []
        if os.path.getsize(self._path) < self._offset:
            self._offset = 0
        with open(self._path, errors="replace") as log_file:
            log_file.seek(self._offset)
            lines = log_file.readlines()
            self._offset = log_file.tell()
        kept = [
            line.rstrip()[:MAXIMUM_LINE_LENGTH]
            for line in lines
            if not ROUTINE_LINES.search(line)
        ]
        return kept[-MAXIMUM_LINES:]
