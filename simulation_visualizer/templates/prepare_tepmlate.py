from ..utils import get_python
from pathlib import Path
from getpass import getuser


def main():

    HERE = Path(__file__).parent
    PACKAGE = HERE.parent
    DATA = PACKAGE / "data"
    # gets python ececutable, decend two levels to get environment root
    BIN = get_python().parent
    ENV = BIN.parent

    # first set apache config file
    a2_conf = (HERE / "apache2_wsgi.conf.template").read_text()
    a2_conf = a2_conf.replace("$PACKAGE$", str(PACKAGE))
    a2_conf = a2_conf.replace("$USER$", getuser())
    a2_conf = a2_conf.replace("$ENV$", str(ENV))

    MAIL = input("Input server admin mail: ")
    a2_conf = a2_conf.replace("$MAIL$", MAIL)

    DOMAIN = input("Input server domain name: ")
    a2_conf = a2_conf.replace("$DOMAIN$", DOMAIN)

    print("Use this to create a site in /etc/apache2/sites-available")
    print("---------------------------------------------------------")
    print(a2_conf)
    print("---------------------------------------------------------\n")

    # edit linux service file
    service_conf = (HERE / "sim_visualizer.service.template").read_text()
    service_conf = service_conf.replace("$BIN$", str(BIN))
    service_conf = service_conf.replace("$DATA$", str(DATA))
    service_conf = service_conf.replace("$USER$", getuser())
    service_conf = service_conf.replace("$PACKAGE$", str(PACKAGE))

    print("Use this to create a site in /etc/systemd/system")
    print("---------------------------------------------------------")
    print(service_conf)
    print("---------------------------------------------------------\n")

