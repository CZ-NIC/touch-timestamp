from datetime import datetime
from os import utime
from pathlib import Path
import subprocess

import dateutil


def get_date(path: str | Path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def set_files_timestamp(date, time, files: list[str]):
    print("Touching files", date, time)
    print(", ".join(str(f) for f in files))
    if date and time:
        time = dateutil.parser.parse(date + " " + time).timestamp()
        [utime(f, (time, time)) for f in files]
        return True


def count_relative_shift(date, time, path: str | Path):
    target = dateutil.parser.parse(f"{date} {time}")
    date = get_date(path)
    return target - date


def touch_multiple(files: list[Path], relative_str):
    print(f"Touch shift {relative_str}")
    for f in files:
        print(f"{f.name} {get_date(f)} → ", end="")
        subprocess.run(["touch", "-d", relative_str, "-r", f, f])
        print(get_date(f))
