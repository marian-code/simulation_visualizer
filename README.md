<h2>
  <a
    target="_blank"
    href="https://158.195.19.213:8050"
  >
    Try Me!
  </a>
</h2>

# Simulation visualizer

Has the ability to load and plot various data formats (depending on available plugins)
from any servers defined in` ~/.ssh/config file`. Currently supported formats are:

- Plumed COLVAR
- DeepMD-kit training lcurve.out format
- LAMMPS log file with custom thermo style without multiline
- DeepMD-kit LAMMPS pair style model deviation output

# Security

The application runs securely over https but the certificates are generated
ad-hoc and sef-sighed by Werkzeug so the app will appear as if its certificate
has expired although it is valid. This is meant to be so for simplicity and
will not be repaired! The app also requires login. As of now only admin
specified users are allowed to login. The login credentials are your
**...@fmph.uniba.sk** mail address and **password** is same as on **DEP2C**.
# Deploy

There are two options. You can use already running version which is hosted on
[Dusanko](https://158.195.19.213:8050) this should be always up and running. It
has defined keys for all available machines (Kohn, Hartree, Fock, Schrodinger,
Landau, Aurel) The only problem you could possibly encounter is related to file
access privilages. As the server runs on `Dusanko` it logs in as user `rynik` so
this might stop the server from accessing some files. It happens sometimes mostly
with files written by programs that where run through PBS job manager. This problem
can simply be prevented by adding this line to PBS script: `#PBS -W umask=0022` or
by changing privilages with `chmod`

The second option is to deploy locally:

First you have to generate file with user logins in data folder named `users.txt`.
The format is one `username:password` on each line.

```bash
# install
pip install git+https://github.com/ftl-fmfi/simulation-visualizer.git
# create password file
cd path/to/simulation_visualizer
cd data
touch users.txt
echo user1:password1 >> users.txt
echo user2:password2 >> users.txt
# run
visualizer -vvvv -e & # for full debug mode, run over https and leave it running in the background
```

This option assumes that you have generated ssh keys for servers you will want
to access.

# Writing new parsers

Writing new plugin to handle arbitrary data format is rather easy. One must follow
few simple rules:
* The parser must be self contained in one file
* Parser class must inherit from [`FileParser`](https://github.com/ftl-fmfi/simulation-visualizer/blob/9b37c9382200df023bbd2e126b018ecd12319054/simulation_visualizer/parser.py#L51)
base class which defines parser API and takes care of auto plugin loading through
metaclass magic.
* each parser must override `FileParser` abstract methods and optionally
* New plugins can be added to running server which will auto-load them on the fly.
* All parser methods must be class methods, the parser will not be instantiated!

There is an [example file](simulation_visualizer/parsers/example_plugin.py) prepared for convenience which should help you
write a plugin in no time. 


# Example

![Alt Text](data/example_colvar.gif)

# TODO

- add progressbar when loading large files
- clearer error messages showing as detailed report as possible
- repair server sometimes spontaneously reloading
