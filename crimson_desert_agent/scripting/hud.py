from dataclasses import dataclass, replace

MINIMUM_CONFIDENCE = 70
MINIMUM_WORD_LENGTH = 2
LINE_HEIGHT_PIXELS = 14
WORD_GAP_PIXELS = 80
MOD_OVERLAY = (0, 0, 420, 110)


@dataclass(frozen=True)
class Word:
    text: str
    left: int
    top: int
    right: int
    confidence: float


def inside(word: Word, box: tuple[int, int, int, int]) -> bool:
    return (
        box[0] <= word.left < box[0] + box[2] and box[1] <= word.top < box[1] + box[3]
    )


def readable(word: Word) -> bool:
    letters = sum(character.isalnum() for character in word.text)
    return (
        word.confidence >= MINIMUM_CONFIDENCE
        and letters >= MINIMUM_WORD_LENGTH
        and letters * 2 >= len(word.text)
        and not inside(word, MOD_OVERLAY)
    )


def shifted(word: Word, left: int, top: int) -> Word:
    return replace(
        word, left=word.left + left, top=word.top + top, right=word.right + left
    )


def rows_of(words: list[Word]) -> list[list[Word]]:
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda word: word.top):
        if rows and word.top - rows[-1][0].top <= LINE_HEIGHT_PIXELS:
            rows[-1].append(word)
        else:
            rows.append([word])
    return rows


def lines_from_words(words: list[Word], left: int = 0, top: int = 0) -> list[dict]:
    placed = [shifted(word, left, top) for word in words]
    lines: list[list[Word]] = []
    for row in rows_of([word for word in placed if readable(word)]):
        previous = None
        for word in sorted(row, key=lambda word: word.left):
            if previous is None or word.left - previous.right > WORD_GAP_PIXELS:
                lines.append([])
            lines[-1].append(word)
            previous = word
    return [
        {
            "text": " ".join(word.text for word in line),
            "x": line[0].left,
            "y": line[0].top,
        }
        for line in lines
    ]
