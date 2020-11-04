# Simulation visualizer

Has the ability to load and plot various data formats (depending on available plugins)
from any servers defined in` ~/.ssh/config file`. Currently supported formats are:

- Plumed COLVAR
- DeepMD-kit training lcurve.out format
- LAMMPS log file with custom thermo style without multiline
- DeepMD-kit LAMMPS pair style model deviation output

There is also one example plugin in `parsers` directory showing how should new
plugins be implemented

# TODO

- add progressbar when loading large files