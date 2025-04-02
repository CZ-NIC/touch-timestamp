from mininterface import Tag

from .utils import count_relative_shift, get_date


class Controller:
    def __init__(self):
        self._used_relative = False

    def refresh_title(self, tag: Tag):
        if self._used_relative:
            self.do_refresh_title(tag)

    def do_refresh_title(self, tag: Tag):
        # NOTE this title should serve for "Relative with reference" section only to get rid of self._user_relative
        self._used_relative = True
        def r(d): return d.replace(microsecond=0)

        form = tag.facet._form
        e = form["RelativeToReference"][""]  # NOTE this is awful. How to access them better?

        files = form["files"].val
        dates = [get_date(p) for p in files]

        shift = count_relative_shift(e["date"].val, e["reference"].val)

        tag.facet.set_title(f"Relative with reference preview"
                            f"\nCurrently, {len(files)} files have time span:"
                            f"\n{r(min(dates))} – {r(max(dates))}"
                            f"\nIt will be shifted by {shift} to:"
                            f"\n{r(shift+min(dates))} – {r(shift+max(dates))}")

        # NOTE: when mininterface allow form refresh, fetch the date and time from the newly-chosen anchor field
