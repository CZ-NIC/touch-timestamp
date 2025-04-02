import subprocess
from dataclasses import MISSING, dataclass, field
from datetime import datetime
from os import utime
from pathlib import Path
from typing import Annotated, get_args

import dateutil
from mininterface import Tag
from mininterface.exceptions import ValidationFail
from mininterface.subcommands import Command
from mininterface.types import EnumTag
from tyro.conf import Positional

from .controller import Controller
from .utils import (count_relative_shift, get_date, set_files_timestamp,
                    touch_multiple)

DateFormat = str  # Use type as of Python3.12

c = Controller()


@dataclass
class App(Command):
    # NOTE tyro does not work if a required positional is missing tyro.cli() returns just NonpropagatingMissingType.
    # If this is supported, I might set other attributes like required (date, time).
    # files: Positional[list[Path]]
    files: Positional[list[Path]] = field(default_factory=list)
    """ Files the modification date is to be changed. """

    def init(self):
        if self.files is MISSING or not len(self.files):
            # self.files = m.form({"Choose files": Tag("", annotation=list[Path], validation=not_empty)})
            self.ref = None
            self.ref_date = None
            return

        self.ref = self.files[0]
        if len(self.files) > 1:
            title = f"Touch {len(self.files)} files"
        else:
            title = f"Touch {self.ref.name}"

        # NOTE should exist self._facet.set_window_title(title) instead of this workaround
        if hasattr(self._facet.adaptor, "title"):
            self._facet.adaptor.title(title)

        self.ref_date = get_date(self.ref)


@dataclass
class Set(App):
    """ Set to a specific time """

    date: Annotated[datetime, Tag(on_change=c.refresh_title)] = datetime.now()
    """ Set specific date """

    def init(self):
        super().init()
        # NOTE program fails on wrong date in GUI
        if self.ref_date:
            self.date = self.ref_date

    def run(self):
        set_files_timestamp(self.date, self.files)


@dataclass
class Exif(App):
    """ Read JPEG EXIF metadata with jhead """

    def run(self):
        [subprocess.run(["jhead", "-ft", f]) for f in self.files]


@dataclass
class FromName(App):
    """ Autodetect format"""

    # NOTE: this is not supported by mininiterface
    # format: Literal[True] | DateFormat = True
    format: bool | DateFormat = True
    """
        Fetch the modification time from the file names stem. Set the format as for `datetime.strptime` like '%Y%m%d_%H%M%S'.
        If set to True, the format will be auto-detected.
        If a file name does not match the format or the format cannot be auto-detected, the file remains unchanged.

        Ex: `--from-name True 20240827_154252.heic` → modification time = 27.8.2024 15:42
        """
    # NOTE put into the GUI from_name, now the GUI does not allow to set the format

    def run(self):
        for p in self.files:
            if self.format is True:  # auto detection
                try:
                    # 20240828_160619.heic -> "20240828 160619" -> "2024-08-28 16:06:19"
                    # IMG_20240101_010053.jpg -> "2024-01-01 01:00:53"
                    dt = dateutil.parser.parse(p.stem.replace("IMG_", "").replace("_", " "))
                except ValueError:
                    print(f"Cannot auto detect the date format: {p}")
                    continue
            else:
                try:
                    dt = datetime.strptime(p.stem, self.format)
                except ValueError:
                    print(f"Does not match the format {self.format}: {p}")
                    continue
            timestamp = int(dt.timestamp())
            original = datetime.fromtimestamp(p.stat().st_mtime)
            utime(str(p), (timestamp, timestamp))
            print(f"Changed {original.isoformat()} → {dt.isoformat()}: {p}")


@dataclass
class Shift(App):
    unit: Annotated[str, EnumTag(choices=["minutes", "hours"], name="Unit")] = "minutes"
    shift: Annotated[str, Tag(name="How many")] = "0"
    # NOTE: mininterface GUI works bad with negative numbers, hence we use str

    def run(self):
        try:
            quantity = int(self.shift)
        except:
            raise ValidationFail(f"Invalid number for shift: {self.shift}")
        touch_multiple(self.files, f"{quantity} {self.unit}")


@dataclass
class RelativeToReference(Set):

    reference: Annotated[str | None, EnumTag(on_change=c.do_refresh_title)] = None
    """ Relative shift with reference. The reference file is set to the specified date,
            and all other files are shifted by the same amount relative to this reference.
            If not set, the first of the files is used."""

    def init(self):
        super().init()
        if self.reference is None and self.ref:
            self.reference = self.ref

        # NOTE this is not nice. It changes the annotation of the whole dataclass.
        # Mininterface should provide a clear init callback so that we might change the values
        # at the beginning and once the self.files changes.
        get_args(self.__annotations__["reference"])[1].choices = self.files

    def run(self):
        reference = count_relative_shift(self.date, self.reference)

        # microsecond precision is neglected here, touch does not takes it
        touch_multiple(self.files, f"{reference.days} days {reference.seconds} seconds")
