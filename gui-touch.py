from os import utime
from pathlib import Path
from sys import argv

import dateutil.parser
from eel import expose, init, start

files = [Path(p) for p in argv[1:]]

@expose
def get_len_files():
    return len(files)

@expose
def get_first_file_date():
    return Path(files[0]).stat().st_mtime

@expose
def set_timestamp(date, time):
    print("Touching files", date, time)
    print(", ".join(str(f) for f in files))
    if date and time:
        time = dateutil.parser.parse(date + " " + time).timestamp()
        [utime(f, (time, time)) for f in files]
        return True


init(Path(__file__).absolute().parent.joinpath('static'))
start('index.html', size=(330, 30), port=0, block=True)
