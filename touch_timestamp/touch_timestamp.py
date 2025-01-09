#!/usr/bin/env python3
from mininterface import run
from mininterface.subcommands import SubcommandPlaceholder

from .app import Exif, FromName, RelativeToReference, Set, Shift

# NOTE add tests for CLI flags


def main():
    run([Set, Exif, FromName, Shift, RelativeToReference, SubcommandPlaceholder], title="Touch")


if __name__ == "__main__":
    main()
