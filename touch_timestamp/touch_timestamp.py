#!/usr/bin/env python3
from dataclasses import MISSING, dataclass, field
from datetime import datetime
from os import utime
from pathlib import Path
import subprocess

import dateutil.parser
from mininterface import Tag, run
from mininterface.experimental import SubmitButton
from mininterface.validators import not_empty
from tyro.conf import Positional

try:
    from eel import expose, init, start  # NOTE remove eel
    eel = True
except ImportError:
    eel = None


DateFormat = str  # Use type as of Python3.12


@dataclass
class Env:
    files: Positional[list[Path]] = field(default_factory=list)
    """ Files the modification date is to be changed. """

    eel: bool = False
    """ Prefer Eel GUI. (Set the date as in a chromium browser.)
    Does not allow setting from EXIF and relative set.
    """

    from_name: bool | DateFormat = False
    """
    Fetch the modification time from the file names stem. Set the format as for `datetime.strptime` like '%Y%m%d_%H%M%S'.
    If set to True, the format will be auto-detected.
    If a file name does not match the format or the format cannot be auto-detected, the file remains unchanged.

    Ex: `--from-name True 20240827_154252.heic` → modification time = 27.8.2024 15:42
    """
    # NOTE put into the GUI from_name


def count_relative_shift(date, time, path: str | Path):
    target = dateutil.parser.parse(date + " " + time)
    date = get_date(path)
    return target - date


def get_date(path: str | Path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def refresh_relative(tag: Tag):
    def r(d): return d.replace(microsecond=0)

    d = tag.facet._form["Relative with anchor"]

    files = tag.facet._env.files
    dates = [get_date(p) for p in files]

    shift = count_relative_shift(d["date"].val, d["time"].val, d["Anchor"].val)

    tag.facet.set_title(f"Currently, {len(files)} files have time span:"
                        f"\n{r(min(dates))} – {r(max(dates))}"
                        f"\nIt will be shifted by {shift} to:"
                        f"\n{r(shift+min(dates))} – {r(shift+max(dates))}")

    # NOTE: when mininterface allow form refresh, fetch the date and time from the newly-chosen anchor field


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
    m = run(Env, prog="Touch", interface="gui")

    if m.env.files is MISSING or not len(m.env.files):
        m.env.files = m.form({"Choose files": Tag("", annotation=list[Path], validation=not_empty)})
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
        anchor = m.env.files[0]
        if len(m.env.files) > 1:
            title = f"Touch {len(m.env.files)} files"
        else:
            title = f"Touch {anchor.name}"

        with m:
            m.title = title  # NOTE: Changing window title does not work
            date = get_date(anchor)
            form = {
                "Specific time": {
                    "date": str(date.date()), "time": str(date.time()), "Set": SubmitButton()
                    # NOTE program fails on wrong date
                }, "From exif": {
                    "Fetch...": SubmitButton()
                }, "Relative time": {
                    # NOTE: mininterface GUI works bad with negative numbers
                    "Action": Tag("add", choices=["add", "subtract"]),
                    "Unit": Tag("minutes", choices=["minutes", "hours"]),
                    "How many": Tag(0, annotation=int),
                    "Shift": SubmitButton()
                }
            }

            if len(m.env.files) > 1:
                form["Relative with anchor"] = {
                    "Anchor": Tag(anchor, choices=m.env.files, on_change=refresh_relative,
                                  description="Set the file to the specific date, then shift all the other relative to this"),
                    "date": Tag(str(date.date()), on_change=refresh_relative, validation=lambda tag: str(tag.val).startswith("2")),
                    "time": Tag(str(date.time()), on_change=refresh_relative),
                    "Set": SubmitButton()
                }

            output = m.form(form, title)  # NOTE: Do not display submit button

            # NOTE use callbacks instead of these ifs
            if (d := output["Specific time"])["Set"]:
                set_files_timestamp(d["date"], d["time"], m.env.files)
            elif output["From exif"]["Fetch..."]:
                m.facet.set_title("")
                if m.is_yes("Fetches the times from the EXIF if the fails are JPGs."):
                    [subprocess.run(["jhead", "-ft", f]) for f in m.env.files]
                else:
                    m.alert("Ok, exits")
            elif (d := output["Relative time"])["Shift"]:
                quantity = d['How many']
                if d["Action"] == "subtract":
                    quantity *= -1
                touch_multiple(m.env.files, f"{quantity} {d['Unit']}")
            elif (d := output["Relative with anchor"])["Set"]:
                reference = count_relative_shift(d["date"], d["time"], d["Anchor"])

                # microsecond precision is neglected here, touch does not takes it
                touch_multiple(m.env.files, f"{reference.days} days {reference.seconds} seconds")


def touch_multiple(files, relative_str):
    [subprocess.run(["touch", "-d", relative_str, "-r", f, f]) for f in files]


if __name__ == "__main__":
    main()
