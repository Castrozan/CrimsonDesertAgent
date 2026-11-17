import statistics
import subprocess
import sys
import time

from .client import run_script

SEQUENCES = (
    ("state", 0.0),
    ("state; state; state; state; state", 0.0),
    ("press dpad_up; press dpad_down", 0.2),
    ("state; move 0 1 0.4; press rb; look 1 0 0.2; look -1 0 0.2; state", 0.9),
    (
        "down lt; wait 0.1; press rb 0.05 0.05; press rb 0.05 0.05; up lt; stick left 0 1; wait 0.2; release",
        0.5,
    ),
)


def new_process_round_trip_ms(script: str) -> float:
    started = time.perf_counter()
    subprocess.run(
        [sys.executable, "-m", "crimson_desert_agent", "run", script],
        capture_output=True,
        check=True,
    )
    return (time.perf_counter() - started) * 1000


def report(repetitions: int) -> str:
    run_script("focus")
    rows = [
        "| Script | Requested ms | Engine ms | Socket round trip ms | Overhead ms | New process ms |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for script, requested_seconds in SEQUENCES:
        answers = [run_script(script) for _ in range(repetitions)]
        failures = [answer["error"] for answer in answers if not answer["ok"]]
        if failures:
            rows.append(f"| `{script}` | failed: {failures[0]} | | | | |")
            continue
        engine = statistics.median(answer["elapsed_ms"] for answer in answers)
        round_trip = statistics.median(answer["round_trip_ms"] for answer in answers)
        new_process = statistics.median(
            new_process_round_trip_ms(script) for _ in range(repetitions)
        )
        requested = requested_seconds * 1000
        rows.append(
            f"| `{script}` | {requested:.0f} | {engine:.1f} | {round_trip:.1f} | "
            f"{round_trip - requested:.1f} | {new_process:.1f} |"
        )
    return "\n".join(rows)
