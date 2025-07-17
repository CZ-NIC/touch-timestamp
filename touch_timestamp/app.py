import json
import subprocess
from dataclasses import MISSING, dataclass, field
from datetime import datetime
from os import utime
from pathlib import Path
from typing import Annotated, get_args
from datetime import datetime

import dateutil.parser
from mininterface import Tag
from mininterface.exceptions import ValidationFail
from mininterface.cli import Command
from mininterface.tag import SelectTag
from tyro.conf import Positional
import pydash

from .controller import Controller
from .utils import count_relative_shift, get_date, set_files_timestamp, touch_multiple

DateFormat = str  # Use type as of Python3.12

c = Controller()


@dataclass
class App(Command):
    files: Positional[list[Path]]
    """ Files the modification date is to be changed. """

    def init(self):
        if not self.files:
            self.ref = None
            self.ref_date = None
            return

        self.ref = self.files[0]
        if len(self.files) > 1:
            title = f"Touch {len(self.files)} files"
        else:
            title = f"Touch {self.ref.name}"

        # NOTE should exist self._facet.set_window_title(title) instead of this workaround
        if hasattr(self.facet.adaptor, "title"):
            self.facet.adaptor.title(title)

        self.ref_date = get_date(self.ref)


@dataclass
class Set(App):
    """Set to a specific time"""

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
class Metadata(App):
    """Read media metadata (EXIF/FFMPEG)"""

    def run(self):
        from PIL import Image

        heic_registered = False
        VIDEO_EXTENSIONS = {
            ".mp4",
            ".mov",
            ".avi",
            ".mkv",
            ".flv",
            ".webm",
            ".wmv",
            ".m4v",
            ".3gp",
            ".ts",
            ".mts",
            ".m2ts",
        }

        for f in self.files:
            sf = f.suffix.lower()
            match sf:
                case ".jpg" | ".jpeg" | ".jpe" | ".jif" | ".jfif":
                    from PIL.ExifTags import TAGS

                    image = Image.open(f)
                    try:
                        exif_data = image._getexif()
                        exif = {
                            TAGS.get(tag_id, tag_id): value
                            for tag_id, value in exif_data.items()
                        }
                        dt = datetime.strptime(
                            exif.get("DateTimeOriginal"), "%Y:%m:%d %H:%M:%S"
                        )
                    except:
                        print(f"Could not load exif from {f}")
                    else:
                        set_files_timestamp(dt, [f])

                case ".heic":
                    if not heic_registered:
                        import pillow_heif

                        pillow_heif.register_heif_opener()
                        heic_registered = True
                    image = Image.open(f)
                    exif_data = image.getexif()
                    dt = datetime.strptime(exif_data.get(306), "%Y:%m:%d %H:%M:%S")
                    set_files_timestamp(dt, [f])
                case ext if ext in VIDEO_EXTENSIONS:
                    result = subprocess.run(
                        [
                            "ffprobe",
                            "-v",
                            "quiet",
                            "-print_format",
                            "json",
                            "-show_format",
                            f,
                        ],
                        stdout=subprocess.PIPE,
                    )
                    metadata = json.loads(result.stdout)
                    date = pydash.get(
                        metadata, ["format", "tags", "com.apple.quicktime.creationdate"]
                    )
                    if not date:
                        date = pydash.get(metadata, "format.tags.creation_time")
                    if dt := datetime.fromisoformat(date):
                        set_files_timestamp(dt, [f])
                case _:
                    print("Do not know how to fetch exif", f.name)


@dataclass
class FromName(App):
    """Autodetect format"""

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
        fails = []
        for p in self.files:
            if self.format is True:  # auto detection
                try:
                    # 20240828_160619.heic -> "20240828 160619" -> "2024-08-28 16:06:19"
                    # IMG_20240101_010053.jpg -> "2024-01-01 01:00:53"
                    dt = dateutil.parser.parse(
                        p.stem.replace("IMG_", "").replace("VID_", "").replace("_", " ")
                    )
                except ValueError:
                    print(f"Cannot auto detect the date format: {p}")
                    fails.append(p)
                    continue
            else:
                try:
                    dt = datetime.strptime(p.stem, self.format)
                except ValueError:
                    print(f"Does not match the format {self.format}: {p}")
                    fails.append(p)
                    continue
            original = datetime.fromtimestamp(p.stat().st_mtime)
            if original == dt:
                print(f"Already has the date {dt.isoformat()}: {p}")
                continue
            timestamp = int(dt.timestamp())
            utime(str(p), (timestamp, timestamp))
            print(f"Changed {original.isoformat()} → {dt.isoformat()}: {p}")

        # NOTE I'd like to see the process displayed in the application. Now, it's only printed to terminal.
        self.files.clear()
        self.files.extend(fails)
        if self.files:
            raise ValidationFail(
                f"Number of files that could not be set: {len(self.files)}"
            )


@dataclass
class Shift(App):
    unit: Annotated[str, SelectTag(options=["minutes", "hours"], label="Unit")] = (
        "minutes"
    )
    shift: Annotated[str, Tag(label="How many")] = "0"
    # NOTE: mininterface GUI works bad with negative numbers, hence we use str

    def run(self):
        try:
            quantity = int(self.shift)
        except:
            raise ValidationFail(f"Invalid number for shift: {self.shift}")
        touch_multiple(self.files, f"{quantity} {self.unit}")


@dataclass
class RelativeToReference(Set):

    reference: Annotated[str | None, SelectTag(on_change=c.do_refresh_title)] = None
    """ Relative shift with reference. The reference file is set to the specified date,
            and all other files are shifted by the same amount relative to this reference.
            If not set, the first of the files is used."""

    def init(self):
        super().init()
        if not self.reference:
            if self.ref:
                self.reference = self.ref

        # NOTE This is not nice. It changes the annotation of the whole dataclass.
        # Plus, when user adds a file to the common field self.files, the references will stay the same,
        # the new file cannot serve as a reference.
        #
        # Mininterface should provide a clear init callback so that we might change the values
        # at the beginning and once the self.files changes. Or we might link common self.files object
        # to update SelectTag.options. This is a tough task as
        # I don't know whether to access the created tagdict or the class annotation,
        # we have to take into consideration common field self.files will be poped out from the dataclasses
        # to the common base, and that currently, updating with a list will create a new object
        # instead of changing the original list.
        opt_list: SelectTag = get_args(self.__annotations__["reference"])[1]
        opt_list.options = self.files

    def run(self):
        reference = count_relative_shift(self.date, self.reference)

        # microsecond precision is neglected here, touch does not take it
        touch_multiple(self.files, f"{reference.days} days {reference.seconds} seconds")
