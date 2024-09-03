#!/usr/bin/env python3
from dataclasses import dataclass, field
from datetime import datetime
from os import utime
from pathlib import Path

import dateutil.parser
from mininterface import run
from tyro.conf import Positional

try:
    from eel import expose, init, start
    eel = True
except ImportError:
    eel = None


DateFormat = str  # Use type as of Python3.12


@dataclass
class Env:
    files: Positional[list[Path]] = field(default_factory=list)
    """ Files the modification date is to be changed. """

    eel: bool = True
    """ Prefer Eel GUI. (Set the date as in a chromium browser.) """

    from_name: bool | DateFormat = False
    """
    Fetch the modification time from the file names stem. Set the format as for `datetime.strptime` like '%Y%m%d_%H%M%S'.
    If set to True, the format will be auto-detected.
    If a file name does not match the format or the format cannot be auto-detected, the file remains unchanged.

    Ex: `--from-name True 20240827_154252.heic` → modification time = 27.8.2024 15:42
    """


def set_files_timestamp(date, time, files: list[str]):
    print("Touching files", date, time)
    print(", ".join(str(f) for f in files))
    if date and time:
        time = dateutil.parser.parse(date + " " + time).timestamp()
        [utime(f, (time, time)) for f in files]
        return True


def run_eel(files):
    @expose
    def get_len_files():
        return len(files)

    @expose
    def get_first_file_date():
        return Path(files[0]).stat().st_mtime

    @expose
    def set_timestamp(date, time):
        return set_files_timestamp(date, time, files)

    init(Path(__file__).absolute().parent.joinpath('static'))
    start('index.html', size=(330, 30), port=0, block=True)


def main():
    m = run(Env, prog="Touch")

    if m.env.from_name:
        for p in m.env.files:
            if m.env.from_name is True:  # auto detection
                try:
                    # 20240828_160619.heic -> "20240828 160619" -> "28.8."
                    dt = dateutil.parser.parse(p.stem.replace("_", ""))
                except ValueError:
                    print(f"Cannot auto detect the date format: {p}")
                    continue
            else:
                try:
                    dt = datetime.strptime(p.stem, m.env.from_name)
                except ValueError:
                    print(f"Does not match the format {m.env.from_name}: {p}")
                    continue
            timestamp = int(dt.timestamp())
            original = datetime.fromtimestamp(p.stat().st_mtime)
            utime(str(p), (timestamp, timestamp))
            print(f"Changed {original.isoformat()} → {dt.isoformat()}: {p}")
    elif eel and m.env.eel:  # set exact date with eel
        run_eel(m.env.files)
    else:  # set exact date with Mininterface
        if len(m.env.files) > 1:
            title = f"Touch {len(m.env.files)} files"
        else:
            title = f"Touch {m.env.files[0].name}"

        with m:
            m.title = title # NOTE: Changing title does not work
            date = datetime.fromtimestamp(Path(m.env.files[0]).stat().st_mtime)
            output = {title: {"date": str(date.date()), "time": str(date.time())}}
            m.form(output)
            set_files_timestamp(output["date"], output["time"], m.env.files)


if __name__ == "__main__":
    main()
