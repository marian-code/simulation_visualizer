import re
from typing import IO, List, Optional

import pandas as pd
from simulation_visualizer.parser import FileParser


class DeepMDTrainParser(FileParser):

    name = "DeepMD-lcurve"
    header = re.compile(
        r"#\s*batch\s*l2_tst\s*l2_trn\s*l2_e_tst\s*l2_e_trn\s*"
        r"l2_f_tst  l2_f_trn\s*l2_v_tst\s*l2_v_trn\s*lr", re.I
    )

    @classmethod
    def extract_header(cls, path: str, host: str,
                       fileobj: Optional[IO] = None) -> List[str]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return line.split()
            else:
                raise ValueError("Unsupported header format")

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:
            df = pd.read_table(f, sep=r"\s+")

        return df


if __name__ == "__main__":

    #p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/train/lcurve.out"
    #p = "/zfs/hybrilit.jinr.ru/user/r/rynik/dpmd_test/lcurve.out"
    p = "/home/toth/toth/deepmd/Ge/lcurve.out"
    df = DeepMDTrainParser.extract_data(p, "kohn")
    print(df)
