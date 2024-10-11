from typing import Annotated
from mininterface import Tag
from tyro.conf import Positional
from dataclasses import dataclass, field
from pathlib import Path

DateFormat = str  # Use type as of Python3.12


@dataclass
class Env:
    files: Positional[list[Path]] = field(default_factory=list)
    """ Files the modification date is to be changed. """
    # TODO filter only files/dir

    from_name: bool | DateFormat = False
    """
    Fetch the modification time from the file names stem. Set the format as for `datetime.strptime` like '%Y%m%d_%H%M%S'.
    If set to True, the format will be auto-detected.
    If a file name does not match the format or the format cannot be auto-detected, the file remains unchanged.

    Ex: `--from-name True 20240827_154252.heic` → modification time = 27.8.2024 15:42
    """
    # NOTE put into the GUI from_name

    # Specific time
    # NOTE program fails on wrong date in GUI
    date: str = ""
    """ Set specific date """
    time: str = ""
    """ Set specific time """
    # TODO allow time without date

    # Exif
    from_exif: bool = False

    # Relative time shift
    # NOTE: mininterface GUI works bad with negative numbers

    shift_action: Annotated[str, Tag(choices=["add", "subtract"], name="Action")] = "add"
    unit: Annotated[str, Tag(choices=["minutes", "hours"], name="Unit")] = "minutes"
    shift: Annotated[int, Tag(name="How many")] = 0
    # shift: Annotated[str, Tag(name="How many")] = ""
    # shift: int = 0
    # TODO když je tady ten Tag, nefetchne se tam nic!!!

    # TODO
    # if len(m.env.files) > 1:
    # form["Relative with anchor"] = {
    #     "Anchor": Tag(anchor, choices=m.env.files, on_change=refresh_relative,
    #                     description="Set the file to the specific date, then shift all the other relative to this"),
    #     "date": Tag(str(date.date()), on_change=refresh_relative, validation=lambda tag: str(tag.val).startswith("2")),
    #     "time": Tag(str(date.time()), on_change=refresh_relative),
    #     "Set": SubmitButton()
    # }

    reference: Path | None = None
    """ Relative shift with reference. The reference file is set to the specified date,
        and all other files are shifted by the same amount relative to this reference. """
