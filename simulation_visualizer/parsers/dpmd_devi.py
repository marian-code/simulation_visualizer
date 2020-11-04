import re
from typing import IO, List, Optional

import pandas as pd
from simulation_progress.parser import FileParser

class DeepMDModelDeviationParser(FileParser):

    name = "DeepMD-model_deviation"
    header = re.compile(
        r"#\s*step\s*max_devi_e\s*min_devi_e\s*avg_devi_e\s*max_devi_f\s*"
        r"min_devi_f\s*avg_devi_f", re.I
    )

    @classmethod
    def extract_header(cls, path: str, host: str,
                       fileobj: Optional[IO] = None) -> List[str]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return re.sub(r"#\s*", "", line).split()
            else:
                raise ValueError("Unsupported header format")

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)
            f.seek(0)

            df = pd.read_table(f, sep=r"\s+", header=0, names=header,
                               comment="#", usecols=range(7))

        return df

if __name__ == "__main__":

    p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/cd/md.out"
    df = PlumedMetaDParser.extract_data(p, "kohn")
    print(df)
