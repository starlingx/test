from optparse import OptionParser

from _pytest.main import Session

from framework.options.safe_option_parser import SafeOptionParser


class ConfigurationFileLocationsManager:
    """
    Class to hold all the file locations for different configs.
    """

    def __init__(self):
        self.lab_config_file = None
        self.deployment_assets_config_file = None
        self.k8s_config_file = None
        self.ptp_config_file = None
        self.logger_config_file = None
        self.docker_config_file = None
        self.web_config_file = None
        self.database_config_file = None
        self.rest_api_config_file = None
        self.security_config_file = None
        self.snmp_config_file = None
        self.usm_config_file = None
        self.app_config_file = None
        self.openstack_config_file = None

    def set_configs_from_pytest_args(self, session: Session):
        """
        Sets the configs from pytest args.

        Args:
            session (Session): the pytest session

        """
        lab_config_file = session.config.getoption("--lab_config_file")
        if lab_config_file:
            self.set_lab_config_file(lab_config_file)

        deployment_assets_config_file = session.config.getoption("--deployment_assets_config_file")
        if deployment_assets_config_file:
            self.set_deployment_assets_config_file(deployment_assets_config_file)

        k8s_config_file = session.config.getoption("--k8s_config_file")
        if k8s_config_file:
            self.set_k8s_config_file(k8s_config_file)

        ptp_config_file = session.config.getoption("--ptp_config_file")
        if ptp_config_file:
            self.set_ptp_config_file(ptp_config_file)

        logger_config_file = session.config.getoption("--logger_config_file")
        if logger_config_file:
            self.set_logger_config_file(logger_config_file)

        docker_config_file = session.config.getoption("--docker_config_file")
        if docker_config_file:
            self.set_docker_config_file(docker_config_file)

        web_config_file = session.config.getoption("--web_config_file")
        if web_config_file:
            self.set_web_config_file(web_config_file)

        database_config_file = session.config.getoption("--database_config_file")
        if database_config_file:
            self.set_database_config_file(database_config_file)

        rest_api_config_file = session.config.getoption("--rest_api_config_file")
        if rest_api_config_file:
            self.set_rest_api_config_file(rest_api_config_file)

        security_config_file = session.config.getoption("--security_config_file")
        if security_config_file:
            self.set_security_config_file(security_config_file)

        snmp_config_file = session.config.getoption("--snmp_config_file")
        if snmp_config_file:
            self.set_snmp_config_file(snmp_config_file)

        usm_config_file = session.config.getoption("--usm_config_file")
        if usm_config_file:
            self.set_usm_config_file(usm_config_file)

        app_config_file = session.config.getoption("--app_config_file")
        if app_config_file:
            self.set_app_config_file(app_config_file)

        openstack_config_file = session.config.getoption("--openstack_config_file")
        if openstack_config_file:
            self.set_openstack_config_file(openstack_config_file)

    def set_configs_from_options_parser(self, parser: OptionParser = None):
        """
        Sets the config files from options parser.

        Args:
            parser (OptionParser): This is needed for the case where we have other command line options besides just config,
                     in these cases the parser will need to be instantiated and the other options added before passing to
                     config location manager.

        Returns: None

        """
        safe_option_parser = SafeOptionParser(parser)
        self.add_options(safe_option_parser)
        options, args = parser.parse_args()

        lab_config_file = options.lab_config_file
        if lab_config_file:
            self.set_lab_config_file(lab_config_file)

        deployment_assets_config_file = options.deployment_assets_config_file
        if deployment_assets_config_file:
            self.set_deployment_assets_config_file(deployment_assets_config_file)

        k8s_config_file = options.k8s_config_file
        if k8s_config_file:
            self.set_k8s_config_file(k8s_config_file)

        ptp_config_file = options.ptp_config_file
        if ptp_config_file:
            self.set_ptp_config_file(ptp_config_file)

        logger_config_file = options.logger_config_file
        if logger_config_file:
            self.set_logger_config_file(logger_config_file)

        docker_config_file = options.docker_config_file
        if docker_config_file:
            self.set_docker_config_file(docker_config_file)

        web_config_file = options.web_config_file
        if web_config_file:
            self.set_web_config_file(web_config_file)

        database_config_file = options.database_config_file
        if database_config_file:
            self.set_database_config_file(database_config_file)

        rest_api_config_file = options.rest_api_config_file
        if rest_api_config_file:
            self.set_rest_api_config_file(rest_api_config_file)

        security_config_file = options.security_config_file
        if security_config_file:
            self.set_security_config_file(security_config_file)

        snmp_config_file = options.snmp_config_file
        if snmp_config_file:
            self.set_snmp_config_file(snmp_config_file)

        usm_config_file = options.usm_config_file
        if usm_config_file:
            self.set_usm_config_file(usm_config_file)

        app_config_file = options.app_config_file
        if app_config_file:
            self.set_app_config_file(app_config_file)

        openstack_config_file = options.openstack_config_file
        if openstack_config_file:
            self.set_openstack_config_file(openstack_config_file)

    @staticmethod
    def add_options(safe_parser: SafeOptionParser):
        """
        This function will add the configuration file locations options to the safe_parser passed in.

        Args:
            safe_parser (SafeOptionParser): The SafeOptionParser

        """
        safe_parser.add_option("--lab_config_file", action="store", dest="lab_config_file", help="the lab file used for scanning")
        safe_parser.add_option("--deployment_assets_config_file", action="store", dest="deployment_assets_config_file", help="The location of the files used to deploy the lab")
        safe_parser.add_option("--k8s_config_file", action="store", dest="k8s_config_file", help="the k8s config file")
        safe_parser.add_option("--ptp_config_file", action="store", dest="ptp_config_file", help="the PTP config file")
        safe_parser.add_option("--logger_config_file", action="store", dest="logger_config_file", help="the logger config file")
        safe_parser.add_option("--docker_config_file", action="store", dest="docker_config_file", help="the docker config file")
        safe_parser.add_option("--web_config_file", action="store", dest="web_config_file", help="The Web config file")
        safe_parser.add_option("--database_config_file", action="store", dest="database_config_file", help="The database config file")
        safe_parser.add_option("--rest_api_config_file", action="store", dest="rest_api_config_file", help="The rest api config file")
        safe_parser.add_option("--security_config_file", action="store", dest="security_config_file", help="The security config file")
        safe_parser.add_option("--snmp_config_file", action="store", dest="snmp_config_file", help="The SNMP config file")
        safe_parser.add_option("--usm_config_file", action="store", dest="usm_config_file", help="The USM config file")
        safe_parser.add_option("--app_config_file", action="store", dest="app_config_file", help="The app config file")
        safe_parser.add_option("--openstack_config_file", action="store", dest="openstack_config_file", help="The openstack config file")

    def set_lab_config_file(self, lab_config_file: str):
        """
        Setter for lab config files.

        Args:
            lab_config_file (str): the location of the lab config file

        Returns: None

        """
        self.lab_config_file = lab_config_file

    def get_lab_config_file(self) -> str:
        """
        Getter for lab config file.

        Returns: the lab config file

        """
        return self.lab_config_file

    def set_deployment_assets_config_file(self, deployment_assets_config_file: str):
        """
        Setter for deployment assets config file.

        Args:
            deployment_assets_config_file (str): the location of the deployment assets config file

        Returns: None

        """
        self.deployment_assets_config_file = deployment_assets_config_file

    def get_deployment_assets_config_file(self) -> str:
        """
        Getter for deployment assets config file.

        Returns: the deployment assets config file.

        """
        return self.deployment_assets_config_file

    def set_k8s_config_file(self, k8s_config_file: str):
        """
        Setter for k8s config file.

        Args:
            k8s_config_file (str): the location of the k8s config file

        Returns: None

        """
        self.k8s_config_file = k8s_config_file

    def get_k8s_config_file(self) -> str:
        """
        Getter for k8s config file.

        Returns: the k8s config file

        """
        return self.k8s_config_file

    def set_ptp_config_file(self, ptp_config_file: str):
        """
        Setter for ptp config file.

        Args:
            ptp_config_file (str): the location of the ptp config file

        Returns: None

        """
        self.ptp_config_file = ptp_config_file

    def get_ptp_config_file(self) -> str:
        """
        Getter for ptp config file.

        Returns: the ptp config file

        """
        return self.ptp_config_file

    def set_logger_config_file(self, logger_config_file: str):
        """
        Setter for logger config file.

        Args:
            logger_config_file (str): the logger config file

        Returns: None

        """
        self.logger_config_file = logger_config_file

    def get_logger_config_file(self) -> str:
        """
        Getter for logger config file.

        Returns: the logger config file

        """
        return self.logger_config_file

    def set_docker_config_file(self, docker_config_file: str):
        """
        Setter for docker config file.

        Args:
            docker_config_file (str): the docker config file

        Returns: None

        """
        self.docker_config_file = docker_config_file

    def get_docker_config_file(self) -> str:
        """
        Getter for docker config file.

        Returns: the docker config file

        """
        return self.docker_config_file

    def set_web_config_file(self, web_config_file: str):
        """
        Setter for web config file.

        Args:
            web_config_file (str): the web config file

        Returns: None

        """
        self.web_config_file = web_config_file

    def get_web_config_file(self) -> str:
        """
        Getter for web config file.

        Returns: the web config file

        """
        return self.web_config_file

    def set_database_config_file(self, database_config_file: str):
        """
        Setter for database config file.

        Args:
            database_config_file (str): the database config file

        Returns: None

        """
        self.database_config_file = database_config_file

    def get_database_config_file(self) -> str:
        """
        Getter for database config file.

        Returns: the database config file

        """
        return self.database_config_file

    def set_rest_api_config_file(self, rest_api_config_file: str):
        """
        Setter for rest_api_config_file.

        Args:
            rest_api_config_file (str): the rest_api_config_file

        Returns: None

        """
        self.rest_api_config_file = rest_api_config_file

    def get_rest_api_config_file(self) -> str:
        """
        Getter for rest_api_config_file.

        Returns: the rest_api_config_file

        """
        return self.rest_api_config_file

    def get_security_config_file(self) -> str:
        """
        Getter for security config file

        Returns:
            str: the security config file

        """
        return self.security_config_file

    def set_security_config_file(self, security_config_file: str):
        """
        Setter for security config file

        Args:
            security_config_file (str): the security config file

        """
        self.security_config_file = security_config_file

    def get_snmp_config_file(self) -> str:
        """
        Getter for snmp config file

        Returns:
            str: the snmp config file

        """
        return self.snmp_config_file

    def set_snmp_config_file(self, snmp_config_file: str):
        """
        Setter for snmp config file

        Args:
            snmp_config_file (str): the snmp config file

        """
        self.snmp_config_file = snmp_config_file

    def get_usm_config_file(self) -> str:
        """
        Getter for usm config file

        Returns:
            str: the usm config file

        """
        return self.usm_config_file

    def set_usm_config_file(self, usm_config_file: str):
        """
        Setter for usm config file

        Args:
            usm_config_file (str): the usm config file

        """
        self.usm_config_file = usm_config_file

    def get_app_config_file(self) -> str:
        """
        Getter for app config file

        Returns:
            str: the app config file
        """
        return self.app_config_file

    def set_app_config_file(self, app_config_file: str):
        """
        Setter for app config file

        Args:
            app_config_file (str): the app config file

        """
        self.app_config_file = app_config_file

    def get_openstack_config_file(self) -> str:
        """
        Getter for openstack config file

        Returns:
            str: the openstack config file
        """
        return self.openstack_config_file

    def set_openstack_config_file(self, openstack_config_file: str):
        """
        Setter for app config file

        Args:
            openstack_config_file (str): the app config file

        """
        self.openstack_config_file = openstack_config_file
