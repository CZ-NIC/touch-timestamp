#!/usr/bin/env python3
import subprocess
from dataclasses import MISSING, dataclass
from datetime import datetime
from os import utime
from pathlib import Path
from typing import Annotated, Callable

import dateutil.parser
from mininterface import Mininterface, Tag, run
from mininterface.experimental import SubmitButton
from mininterface.form_dict import dataclass_to_tagdict, TagDict
from mininterface.types import CallbackTag, TagType, TagCallback
from mininterface.validators import not_empty

from touch_timestamp.utils import touch_multiple
from .utils import count_relative_shift, get_date, set_files_timestamp

from .controller import Controller
from .env import Env


try:
    # TODO remove eel
    from eel import expose, init, start  # NOTE remove eel
    eel = True
except ImportError:
    eel = None


def refresh_relative(tag: Tag):
    def r(d): return d.replace(microsecond=0)

    e: Env = tag.facet._env

    files = e.files
    dates = [get_date(p) for p in files]

    # if e.reference:
    shift = count_relative_shift(e.date, e.time, e.reference)

    tag.facet.set_title(f"Currently, {len(files)} files have time span:"
                        f"\n{r(min(dates))} – {r(max(dates))}"
                        f"\nIt will be shifted by {shift} to:"
                        f"\n{r(shift+min(dates))} – {r(shift+max(dates))}")
    # else:
    # tag.facet.set_title("Touch")

    # NOTE: when mininterface allow form refresh, fetch the date and time from the newly-chosen anchor field


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
    else:  # set exact date with Mininterface
        anchor = m.env.files[0]
        if len(m.env.files) > 1:
            title = f"Touch {len(m.env.files)} files"
        else:
            title = f"Touch {anchor.name}"

        # with m:
        m.title = title  # NOTE: Changing window title does not work
        date = get_date(anchor)
        controller = Controller(m)
        if not controller.process_cli():

            # Since we want the UI to appear completely differently than CLI, we redefine whole form.
            # However, we fetch the tags in order to i.e. preserve the description texts.
            d: TagDict = dataclass_to_tagdict(m.env)[""]
            form = {
                "Specific time": {
                    "date": d["date"].set_val(date.date()),  # NOTE program fails on wrong date
                    "time": d["time"].set_val(date.time()),
                    "Set": controller.specific_time
                },
                "From exif": {
                    "Fetch...": controller.fetch_exif
                }, "Relative time": {
                    # NOTE: mininterface GUI works bad with negative numbers, hence we use shift_action
                    # TODO TADY TY MENA ZASE NEFUNGUJOU
                    **{d[t].name: d[t] for t in ("shift_action", "unit", "shift")},
                    "Shift": controller.relative_time
                }
            }

            if len(m.env.files) > 1:
                # TODO kde je default val??
                form["Relative with reference"] = {
                    "Reference": Tag(d["reference"].set_val(anchor), choices=m.env.files, on_change=refresh_relative),
                    # "date": Tag(str(date.date()), on_change=refresh_relative, validation=lambda tag: str(tag.val).startswith("2")),
                    # "time": Tag(str(date.time()), on_change=refresh_relative),
                    "Set": controller.referenced_shift
                    # "Set": SubmitButton()
                }

            m.form(form, title)

            quit()
            # TODO při fetchi doplnit datum na teď

            output = m.form(form, title)  # NOTE: Do not display submit button

            # TODO tohle už needitovat
            if False:     # TODO use callbacks instead of these ifs
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


if __name__ == "__main__":
    main()
