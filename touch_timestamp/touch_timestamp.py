#!/usr/bin/env python3
from dataclasses import MISSING
from pathlib import Path

from mininterface import Tag, run
from mininterface.form_dict import TagDict, dataclass_to_tagdict
from mininterface.validators import not_empty


from .controller import Controller
from .env import Env
from .utils import get_date

# TODO update docs, add tests


def main():
    # NOTE TUI is not great due to the Mininterface sections mostly ignored
    # It does not end after a button is clicked.
    m = run(Env, prog="Touch")

    if m.env.files is MISSING or not len(m.env.files):
        m.env.files = m.form({"Choose files": Tag("", annotation=list[Path], validation=not_empty)})

    reference = m.env.files[0]
    if len(m.env.files) > 1:
        title = f"Touch {len(m.env.files)} files"
    else:
        title = f"Touch {reference.name}"

    # with m:
    m.title = title  # NOTE: Changing window title does not work
    date = get_date(reference)
    controller = Controller(m)
    if not controller.process_cli():
        # Since we want the UI to appear completely differently than CLI, we redefine whole form.
        # However, we fetch the tags in order to i.e. preserve the description texts.
        d: TagDict = dataclass_to_tagdict(m.env)[""]
        form = {
            "Specific time": {
                # NOTE program fails on wrong date
                "date": Tag(d["date"].set_val(date.date()), on_change=controller.refresh_title),
                "time": Tag(d["time"].set_val(date.time()), on_change=controller.refresh_title),
                "Set": controller.specific_time
            },
            "From exif": {
                "Fetch...": controller.fetch_exif
            }, "Relative time": {
                # NOTE: mininterface GUI works bad with negative numbers, hence we use shift_action
                **{d[t].name: d[t] for t in ("shift_action", "unit", "shift")},
                "Shift": controller.relative_time
            },
            "From name": {
                "Autodetect format": controller.from_name_helper
            }
        }

        if len(m.env.files) > 1:
            form["Relative with reference"] = {
                "Reference": Tag(d["reference"].set_val(reference), choices=m.env.files, on_change=controller.do_refresh_title),
                "Set": controller.referenced_shift
            }

        # TODO hide submit button, so that enter submits current button
        m.form(form, title)


if __name__ == "__main__":
    main()
