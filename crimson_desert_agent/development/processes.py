import subprocess
import time


def is_running(process_name: str) -> bool:
    return (
        subprocess.run(["pgrep", "-x", process_name], capture_output=True).returncode
        == 0
    )


def stop(process_name: str, timeout_seconds: float = 30.0) -> bool:
    subprocess.run(["pkill", "-x", process_name], capture_output=True)
    deadline = time.monotonic() + timeout_seconds
    while is_running(process_name) and time.monotonic() < deadline:
        time.sleep(0.5)
    return not is_running(process_name)


def start_detached(command: list[str], log_path: str, cwd: str | None = None) -> None:
    with open(log_path, "ab") as log_file:
        subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
