import re
from typing import IO, List, Optional

import numpy as np
import pandas as pd
from simulation_visualizer.parser import FileParser
import warnings


class LammpsMetaDParser(FileParser):

    name = "LAMMPS-MetaD"
    header = re.compile(r"LAMMPS\s*\(\S*\s*\S*\s*\S*\)")

    @classmethod
    def extract_header(cls, path: str, host: str,
                       fileobj: Optional[IO] = None) -> List[str]:

        with cls._file_opener(host, path, fileobj) as f:
            line = f.readline()

            if cls.header.match(line):
                f.seek(0)
            else:
                raise ValueError("Unsupported header format")

            header = []
            for line in f:
                style_pattern = r"thermo_style\s*custom\s*"
                if re.match(style_pattern, line, re.I):
                    header = re.sub(style_pattern, "", line).split()
                    break

        return header

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)

            # continue to search fro start of thermo output
            for line in f:
                if "Per MPI rank memory allocation" in line:
                    # now file iterator is set to start of thermo output
                    f.readline()
                    break
            else:
                raise ValueError(f"couldn't find start of thermo output "
                                 f"in lammps file: {path}")

            # load to numpy array
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = np.genfromtxt(f, comments="#", invalid_raise=False)
                        
            # convert to dataframe
            df = pd.DataFrame(data=data, columns=header)

        return df

if __name__ == "__main__":

    p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/btin_3Gpa/log.lammps"
    LammpsMetaDParser.extract_data(p, "kohn", "")

    p = "/zfs/hybrilit.jinr.ru/user/r/rynik/clathrate_x2x2x2/log.lammps"
    print(LammpsMetaDParser.can_handle(p, "hydra"))

    header = LammpsMetaDParser.extract_header(p, "hydra")
    print(header)

    df = LammpsMetaDParser.extract_data(p, "hydra")
    print(df)
