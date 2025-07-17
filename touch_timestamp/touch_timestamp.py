#!/usr/bin/env python3
from mininterface import run
from mininterface.cli import SubcommandPlaceholder

from .app import Metadata, FromName, RelativeToReference, Set, Shift

# NOTE add tests for CLI flags


def main():
    run(
        [Set, Metadata, FromName, Shift, RelativeToReference, SubcommandPlaceholder],
        title="Touch",
    )


if __name__ == "__main__":
    main()
