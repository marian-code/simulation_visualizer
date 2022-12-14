# ! this will prevent module from being imported, must be on top!
raise ImportError("Module not yet ready for production")

import re
from typing import IO, TYPE_CHECKING, List, Optional, Tuple

import pandas as pd

if TYPE_CHECKING:
    from simulation_visualizer.parser import SUGGEST

# add FileParser to path by manipulating sys path if you are not working
# directly in package dir
# import sys
# sys.path.append("/path/to/FileParser")
from simulation_visualizer.parser import FileParser


# all plugin parsers must be subclasses of FileParser and override its two
# abstract methods, extract_header() and extract_data() overiding other
# methods is optional
class ExampleParser(FileParser):

    # name is arbitrarry, but should be unique to parser
    name = "Example-file"
    # header should uniquelly define each type of file,
    # based on this re pattern can_handle() method in base class will decide
    # if this parser is suitable for suplied type of file
    header = re.compile(r"#!\s*FIELDS\s*", re.I)

    # short description ofh the parser
    description = (
        "Here should be some consise description of the parser which will be "
        "displayed in webpage."
    )

    # Or you can always override can_handle method for this subclass and define
    # your own criteria, but the header method should suffice for most cases
    # and has the advantage of being fast, any criteria you define must be
    # unique and filter only the types of files this class is able to parse
    @classmethod
    def can_handle(cls, path: str, host: str) -> bool:
        # here should follow some of your custom criteria if you don't
        # want to use the header method defined in base
        # this should run as fast as possible, keep that in mind!
        return False

    # suggest which label should be preset for which axis. Does not have to be
    # overridden, you can use default implementation
    @staticmethod
    def _suggest_axis() -> "SUGGEST":
        return {"x": [0], "y": [1], "z": [2]}

    # this method should extract file header, or whatever part of the file that
    # defines names of data columns, this will be displayed in gui for user to
    # assign to axes, after that data from selected columns will be read and
    # plotted
    @classmethod
    def extract_header(cls, path: str, host: str, fileobj: Optional[IO] = None
                       ) -> Tuple[List[str], "SUGGEST"]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return re.sub(r"#!\s*FIELDS\s*", "", line).split(), cls._suggest_axis()
            else:
                raise ValueError("Unsupported header format")

    # extract actual data, here you can take any approach you deem necessary
    # take a look at ssh_utilities it has methods to copy individual files,
    # lists of files, even whole directory trees, you can also execute commands
    # on remote.
    # However it is not advisable to parse data from more files since you
    # can only pass in one file to the function and infering other file names
    # from the name of passed in file will always be fragile and prone to
    # errors
    # always keep in mind that if you do not use builtin _file_opener method
    # you have to clean up any copied data on method exit, to prevent
    # cluttering of HDD. To this end you can use python tempfile module to
    # create temporary directory context which will delete the created
    # directory on exit.
    # You can even access all other available parsers through cls.parsers
    # attribute as this class inherits ParserMount metaclass!!!
    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        # the copy method is significntly faster for larger files
        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)[0]
            f.seek(0)

            df = pd.read_table(f, sep=r"\s+", header=0, names=header,
                               comment="#")

        return df

# test your plugin before deployment
if __name__ == "__main__":

    # p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/cd/COLVAR"
    p = ("/home/rynik/Raid/dizertacka/train_Si/NNP/MTD/"
         "MetaD-509pie4f-continue/COLVAR")
    df = ExampleParser.extract_data(p, "kohn")
    print(df)
