import subprocess
from datetime import datetime
from os import utime

import dateutil.parser
from mininterface import Mininterface, Tag

from .env import Env
from .utils import (count_relative_shift, get_date, set_files_timestamp,
                    touch_multiple)


class Controller:
    def __init__(self, m: Mininterface[Env]):
        self.m = m
        self.files = m.env.files

        self._used_relative = False

    def process_cli(self):
        env = self.m.env
        if bool(env.date) != bool(env.time):
            # NOTE allow only time change, the date stays
            print("You have to specify both date and time ")
            quit()
        if env.date and env.time:
            if env.reference:
                self.referenced_shift()
            else:
                self.specific_time()
        elif env.from_exif:
            self._exif()
        elif env.shift:
            self.relative_time()
        elif env.from_name:
            self.from_name()
        else:
            return False
        return True  # something has been processed

    def from_name_helper(self):
        # NOTE: get rid of this method when Mininterface is able to handle env.from_name `bool | DateFormat`
        self.m.env.from_name = True
        self.from_name()

    def from_name(self):
        e = self.m.env
        for p in e.files:
            if e.from_name is True:  # auto detection
                try:
                    # 20240828_160619.heic -> "20240828 160619" -> "28.8."
                    # IMG_20240101_010053.jpg -> "1.1."
                    dt = dateutil.parser.parse(p.stem.replace("IMG_", "").replace("_", " "))
                except ValueError:
                    print(f"Cannot auto detect the date format: {p}")
                    continue
            else:
                try:
                    dt = datetime.strptime(p.stem, e.from_name)
                except ValueError:
                    print(f"Does not match the format {e.from_name}: {p}")
                    continue
            timestamp = int(dt.timestamp())
            original = datetime.fromtimestamp(p.stat().st_mtime)
            utime(str(p), (timestamp, timestamp))
            print(f"Changed {original.isoformat()} → {dt.isoformat()}: {p}")

    def specific_time(self):
        e = self.m.env
        set_files_timestamp(e.date, e.time, e.files)

    def _exif(self):
        [subprocess.run(["jhead", "-ft", f]) for f in self.files]

    def relative_time(self):
        e = self.m.env
        quantity = e.shift
        if e.shift_action == "subtract":
            quantity *= -1
        touch_multiple(self.files, f"{quantity} {e.unit}")

    def fetch_exif(self):
        self.m.facet.set_title("")
        if self.m.is_yes("Fetches the times from the EXIF if the fails are JPGs."):
            self._exif()
        else:
            self.m.alert("Ok, exits")

    def referenced_shift(self):
        e = self.m.env
        reference = count_relative_shift(e.date, e.time, e.reference)

        # microsecond precision is neglected here, touch does not takes it
        touch_multiple(self.m.env.files, f"{reference.days} days {reference.seconds} seconds")

    def refresh_title(self, tag: Tag):
        if self._used_relative:
            self.do_refresh_title(tag)

    def do_refresh_title(self, tag: Tag):
        # NOTE this title should serve for "Relative with reference" section only to get rid of self._user_relative
        self._used_relative = True
        def r(d): return d.replace(microsecond=0)

        # e: Env = tag.facet._env
        e = self.m.env

        files = e.files
        dates = [get_date(p) for p in files]

        # if e.reference:
        shift = count_relative_shift(e.date, e.time, e.reference)

        tag.facet.set_title(f"Relative with reference preview"
                            f"\nCurrently, {len(files)} files have time span:"
                            f"\n{r(min(dates))} – {r(max(dates))}"
                            f"\nIt will be shifted by {shift} to:"
                            f"\n{r(shift+min(dates))} – {r(shift+max(dates))}")
        # else:
        # tag.facet.set_title("Touch")

        # NOTE: when mininterface allow form refresh, fetch the date and time from the newly-chosen anchor field
