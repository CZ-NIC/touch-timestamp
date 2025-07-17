from datetime import datetime
from os import utime
from pathlib import Path
import subprocess
from typing import Sequence


def get_date(path: str | Path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def set_files_timestamp(date: datetime, files: Sequence[Path]):
    print("Touching files", date)
    print(", ".join(str(f) for f in files))
    if date:
        time = date.timestamp()
        [utime(f, (time, time)) for f in files]
        return True


def count_relative_shift(date: datetime, path: str | Path):
    return date - get_date(path)


def touch_multiple(files: list[Path], relative_str):
    print(f"Touch shift {relative_str}")
    for f in files:
        print(f"{f.name} {get_date(f)} → ", end="")
        subprocess.run(["touch", "-d", relative_str, "-r", f, f])
        print(get_date(f))
