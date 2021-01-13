import re
from typing import IO, TYPE_CHECKING, List, Optional, Tuple

import pandas as pd
from simulation_visualizer.parser import FileParser

if TYPE_CHECKING:
    from simulation_visualizer.parser import SUGGEST

class DeepMDModelDeviationParser(FileParser):

    name = "DeepMD-model_deviation"
    header = re.compile(
        r"#\s*step\s*max_devi_e\s*min_devi_e\s*avg_devi_e\s*max_devi_f\s*"
        r"min_devi_f\s*avg_devi_f", re.I
    )
    description = (
        "Exctracts data that deepmd pair style in LAMMPS outputs throughtout "
        "the simulation. This is a fixed format file with 1-st column that "
        "records time and 6 other columns representing various error "
        "evolution with time. After these columns when keyword atomic is set "
        "there will be another 3N columns with individual force components "
        "acting on each atom, these are not read!"
    )

    @staticmethod
    def _suggest_axis() -> "SUGGEST":
        return {"x": [0], "y": [1, 3, 4, 6], "z": [-1]}

    @classmethod
    def extract_header(cls, path: str, host: str, fileobj: Optional[IO] = None
                       ) -> Tuple[List[str], "SUGGEST"]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                return re.sub(r"#\s*", "", line).split(), cls._suggest_axis()
            else:
                raise ValueError("Unsupported header format")

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)[0]
            f.seek(0)

            df = pd.read_table(f, sep=r"\s+", header=0, names=header,
                               comment="#", usecols=range(7))

        return df

if __name__ == "__main__":

    p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/cd/md.out"
    df = PlumedMetaDParser.extract_data(p, "kohn")
    print(df)
