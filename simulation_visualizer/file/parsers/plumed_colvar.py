import re
from typing import IO, TYPE_CHECKING, List, Optional, Tuple

import pandas as pd
from simulation_visualizer.file.parser_meta import FileParser

if TYPE_CHECKING:
    from simulation_visualizer.file.parser_meta import SUGGEST


class PlumedMetaDParser(FileParser):

    name = "Plumed-COLVAR"
    header = re.compile(r"#!\s*FIELDS\s*", re.I)
    expected_filename = "COLVAR"
    description = (
        "Extracts data from PLUMED COLVAR file. The file is rather easy to "
        "parse. First column contains time and the successive ones contain "
        "user defined quantities. The headed labels the columns accordingly."
    )

    @classmethod
    def extract_header(cls, path: str, host: str, fileobj: Optional[IO] = None
                       ) -> Tuple[List[str], "SUGGEST"]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return (
                    re.sub(r"#!\s*FIELDS\s*", "", line).split(),
                    cls._suggest_axis()
                )
            else:
                raise ValueError("Unsupported header format")

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)[0]
            f.seek(0)

            df = pd.read_table(f, sep=r"\s+", header=0, names=header,
                               comment="#")

        return df


if __name__ == "__main__":

    # p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/cd/COLVAR"
    p = ("/home/rynik/Raid/dizertacka/train_Si/NNP/MTD/"
         "MetaD-509pie4f-continue/COLVAR")
    df = PlumedMetaDParser.extract_data(p, "kohn")
    print(df)
