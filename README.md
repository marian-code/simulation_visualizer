# Simulation visualizer

Has the ability to load and plot various data formats (depending on available plugins)
from any servers defined in `~/.ssh/config file`. Currently supported formats are:

- Plumed COLVAR
- DeepMD-kit training lcurve.out format
- LAMMPS log file with custom thermo style without multiline
- DeepMD-kit LAMMPS pair style model deviation output

# Example

![Alt Text](data/example_colvar.gif)

# Installation

* you have to generate file with user logins in data folder named `users.txt`.
The format is one `username:password` on each line.
* create self signed certificate files with openssl if you want to run in
production mode

```bash
# install
pip install git+https://github.com/marian-code/simulation-visualizer.git
# create password file
cd path/to/simulation_visualizer
cd data
touch users.txt
echo user1:password1 >> users.txt
echo user2:password2 >> users.txt
```

# Easy deployment:

## Simple debug server with add-hoc generated or no certificates

```bash
# run
visualizer -vvvv -e & # for full debug mode, run over https and leave it running in the background
```

## Simple production run with self-signed certificates:

```bash
cd data
# create certificate files in data folder
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
# run through gunicorn
gunicorn --certfile data/cert.pem --keyfile data/key.pem --bind 0.0.0.0:8050 visualize:server
```

## Systemd service with self-signed certificates

There is a systemd service file prepared for you to run the app as a service.

You have to create self signed certificates to run this app and output then to data
directory.

```bash
cd .../simulation_visualizer
openssl req -x509 -newkey rsa:4096 -keyout data/key.pem -out data/cert.pem -days 365
```
Then just run script that comes preinstalled with the package:

```bash
visualizer-conf
```

This will output reasonable service file configuration. Copy this into:
`/etc/systemd/system/sim_visualizer.service` file and then run:

```bash
systemctl start sim_viasualizer
systemctl enable sim_viasualizer
```

## Security in the above cases

The application runs securely over https but the certificates are generated
ad-hoc and sef-signed by Werkzeug so the app will appear as if its certificate
has expired although it is valid. This is meant to be so for simplicity and
will not be repaired! The app also requires login.

This option assumes that you have generated ssh keys for servers you will want
to access.

# Production run as apache2 wsgi app with certificates

## Install

First create virtual environment. You can do that with conda:

```bash
conda create -n visualize pip
```

activate environment

```bash
conda activate visualize
```

The install the app

```bash
pip install -e .
```

or do not use `-e` if you don't want editable mode

## SSL certificates

Now we need to obtain ssl certificates for the app:

Install [certbot](https://certbot.eff.org) by following the instructiions on website.
You have to have a distribution that supports snap. These are mainly Ubuntu/Debian.

Next you have to register some domain. certbot won't issue a certificate even for static
ip address. this also solves routing to dymaic dns. Recomended option is duckdns.org.
Or you can use noip.com which is slightly less convenient.

## apache2 preparation

These steps should be run while the environment is active

First install apache2 devel package which is necessary to compile `mod_wsgi`.
Use distribuion specific commands, this is valid for Ubuntu/Debian

```bash
sudo apt install apache2-dev
```

Now we can install `mod_wsgi` from pip. Avoid distribution specific version these
are for python **2.7** or **3.5**. Refer to https://pypi.org/project/mod-wsgi/ for correct version for your system.

```bash
pip install mod_wsgi
```

Enable needed mods:

```bash
sudo a2enmod mod_wsgi mod_headers
```

Now run:

```bash
mod_wsgi-express module-config
```

This will output paths that should be pasted in apache2 configuration files in:

```bash
/etc/apache2/mods-available/wsgi.load
```

Edit the `apache2_wsgi.conf.tempate` file and copy it to the right directory, which is:

```bash
cp apache2_wsgi.conf.tempate /etc/apache2/sites-available/apache2_wsgi.conf
```

for Ubuntu/Debian systems. To generate reasonable default telpate you can use
visualizer-conf script that will be installed along with the package. You should merge
this file with one created by certbot which will output something like:
`/etc/apache2/sites-available/000-default-le-ssl.conf`.

Add user that will run the app to `www-data` group that runs the apache2

```bash
sudo usermod -a -G examplegroup exampleusername
```

Now you can enable site and reload apache server

```bash
sudo a2ensite apache2_wsgi
sudo service apache2 reload
```

# Writing new parsers

Writing new plugin to handle arbitrary data format is rather easy. One must follow
few simple rules:
* The parser must be self contained in one file
* Parser class must inherit from [`FileParser`](https://github.com//marian-code/simulation-visualizer/blob/9b37c9382200df023bbd2e126b018ecd12319054/simulation_visualizer/parser.py#L51)
base class which defines parser API and takes care of auto plugin loading through
metaclass magic.
* each parser must override `FileParser` abstract methods and optionally
* New plugins can be added to running server which will auto-load them on the fly.
* All parser methods must be class methods, the parser will not be instantiated!

There is an [example file](simulation_visualizer/parsers/example_plugin.py) prepared for convenience which should help you
write a plugin in no time. 


# TODO

- add progressbar when loading large files
- clearer error messages showing as detailed report as possible
- repair server sometimes spontaneously reloading
- configure log path, maybe in code!!!!

