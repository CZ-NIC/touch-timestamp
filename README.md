[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Change files timestamp with a dialog window.

![Gui window](asset/mininterface-gui.avif "Graphical interface")

GUI automatically fallback to a text interface when display is not available.

![Text interface](asset/textual.avif "Runs in the terminal")


# Installation

Install with a single command from [PyPi](https://pypi.org/project/touch-timestamp/).

```bash
pip install touch-timestamp
touch-timestamp --integrate-to-system  # bash completion wizzard
```

# Docs

## Methods to set the date

When invoked with file paths, you choose whether to set their modification times
* to the specified time
* to the date from the Exif through [jhead](https://github.com/Matthias-Wandel/jhead)
* to a name auto-detected from the file name, ex: `IMG_20240101_010053.jpg` → `2024-01-01 01:00:53`
* to a relative time
* to the specific time, set for a file, then shifts all the other relative to this

![Gui window](asset/mininterface-gui-full.avif "Graphical interface")


## Full help

Everything can be achieved via CLI flag. See the `--help`.

Let's take fetching the time from the file name as an example.

Should you end up with files that keep the date in the file name, use the `from-name` command. In the help, you see that without setting format, it triggers an automatic detection of the time and date format.

```bash
$ touch-timestamp from-name 20240828_160619.heic
Changed 2001-01-01T12:00:00 → 2024-08-28T16:06:19: 20240828_160619.heic
```


## Krusader user action

To change the file timestamps easily from Krusader, import this [user action](extra/touch-timestamp-krusader-useraction.xml): `touch-timestamp subcommand %aList("Selected")%`