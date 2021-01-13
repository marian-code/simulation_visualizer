import re
import warnings
from typing import IO, TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd
from simulation_visualizer.parser import FileParser

if TYPE_CHECKING:
    from simulation_visualizer.parser import SUGGEST


class LammpsMetaDParser(FileParser):

    name = "LAMMPS-MetaD"
    header = re.compile(r"LAMMPS\s*\(\S*\s*\S*\s*\S*\)")
    description = (
        "Extracts data from LAMMPS log file. This is not a fixes format and "
        "paser could break if the lammps log file format is changed. LAMMPS "
        "log files can have broad range of possible formats. So naturally "
        "some limitations apply. If more 'run' commands are present only the "
        "output of hte first one will be extracted. 'thermo_style' must be "
        "set to custom and 'thermo_modify' cannot be multiline."
    )

    @classmethod
    def extract_header(cls, path: str, host: str, fileobj: Optional[IO] = None
                       ) -> Tuple[List[str], "SUGGEST"]:

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

        return header, cls._suggest_axis()

    @classmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:

            header = cls.extract_header(host, path, f)[0]

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
