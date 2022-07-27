import logging
import re
import warnings
from typing import IO, TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd
from simulation_visualizer.file.parser_meta import FileParser

if TYPE_CHECKING:
    from simulation_visualizer.file.parser_meta import SUGGEST


log = logging.getLogger(__name__)


class LammpsMetaDParser(FileParser):

    name = "LAMMPS-MetaD"
    header = re.compile(r"LAMMPS\s*\(\S*\s*\S*\s*\S*\)")
    expected_filename = "log.lammps"
    description = (
        "Extracts data from LAMMPS log file. This is not a fixes format and "
        "paser could break if the lammps log file format is changed. LAMMPS "
        "log files can have broad range of possible formats. So naturally "
        "some limitations apply. If more 'run' commands are present only the "
        "output of the first one will be extracted. There can be however any number of "
        "relaxations before the md run 'thermo_style' must be "
        "set to custom and 'thermo_modify' cannot be multiline."
    )

    @classmethod
    def extract_header(
        cls, path: str, host: str, fileobj: Optional[IO] = None
    ) -> Tuple[List[str], "SUGGEST"]:

        with cls._file_opener(host, path, fileobj) as f:
            cls._find_iter(f)
            return f.readline().split(), cls._suggest_axis()

    @classmethod
    def extract_data(
        cls, path: str, host: str, fileobj: Optional[IO] = None
    ) -> pd.DataFrame:

        with cls._file_opener(host, path, fileobj, copy_method=True) as f:
            header = cls.extract_header(host, path, f)[0]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = np.genfromtxt(f, comments="#", invalid_raise=False)

            # convert to dataframe
            return pd.DataFrame(data=data, columns=header)

    @staticmethod
    def _find_iter(f: IO):
        """Moves file pointer to the start of thermo output."""
        # this is to avoid reading relaxations, we start searching for start
        # only after passing run command
        msg = "Could not find start of MD run"
        for i, line in enumerate(f):
            if re.match(r"\s*run\s+\d+", line, re.I):
                break
            if i > 500:
                raise TypeError(msg)
        else:
            raise TypeError(msg)

        # continue to search for start of thermo output
        msg = "Couldn't find start of thermo output"
        for i, line in enumerate(f):
            if "Per MPI rank memory allocation" in line:
                # now file iterator is set to start of thermo output
                break
            if i > 100:
                raise TypeError(msg)
        else:
            raise ValueError(msg)


if __name__ == "__main__":

    p = "/home/rynik/ace/batch_jusuf_medium/4-5_step_12_0GPa_300.0K-lg2q7iep/log.lammps"
    print(LammpsMetaDParser.extract_data(p, "dusanko"))

    #p = "/home/rynik/ace/batch_45/4-5_step_1_0GPa_300.0K-eefaybyf/output.txt"
    #print(LammpsMetaDParser.extract_header(p, "wigner"))
    assert False

    header = LammpsMetaDParser.extract_header(p, "hydra")

    p = "/home/rynik/Raid/dizertacka/train_Si/ge_DPMD/metad/btin_3Gpa/log.lammps"
    LammpsMetaDParser.extract_data(p, "kohn", "")

    p = "/zfs/hybrilit.jinr.ru/user/r/rynik/clathrate_x2x2x2/log.lammps"
    print(LammpsMetaDParser.can_handle(p, "hydra"))

    header = LammpsMetaDParser.extract_header(p, "hydra")
    print(header)

    df = LammpsMetaDParser.extract_data(p, "hydra")
    print(df)
