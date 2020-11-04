import re
from typing import IO, List, Optional

import pandas as pd
from simulation_visualizer.parser import FileParser


class PlumedMetaDParser(FileParser):

    name = "Plumed-COLVAR"
    header = re.compile(r"#!\s*FIELDS\s*", re.I)

    @classmethod
    def extract_header(cls, path: str, host: str,
                       fileobj: Optional[IO] = None) -> List[str]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return re.sub(r"#!\s*FIELDS\s*", "", line).split()
            else:
                raise ValueError("Unsupported header format")

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)
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
