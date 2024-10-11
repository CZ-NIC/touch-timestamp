import subprocess
from mininterface import Mininterface, Tag

from .env import Env

from .utils import count_relative_shift, set_files_timestamp, touch_multiple


class Controller:
    def __init__(self, m: Mininterface[Env]):
        self.m = m
        self.files = m.env.files

    def process_cli(self):
        env = self.m.env
        # Immediately process CLI
        if env.date and env.time:  # TODO allow only time change
            if env.reference:
                self.referenced_shift()
            else:
                self.specific_time()
        elif env.from_exif:
            self._exif()
        elif env.shift:
            self.relative_time()
        else:
            return False
        return True  # something has been processed

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

    # def referenced_shift_custom_dates(self):

    def referenced_shift(self):
        e = self.m.env
        # if len(m.env.files) > 1: TODO
        # pass
        reference = count_relative_shift(e.date, e.time, e.reference)

        # microsecond precision is neglected here, touch does not takes it
        touch_multiple(self.m.env.files, f"{reference.days} days {reference.seconds} seconds")
