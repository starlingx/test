from optparse import OptionParser


class ConfigurationFileLocationsManager:
    """
    Class to hold all the file locations for different configs
    """

    def __init__(self):
        self.lab_config_file = None
        self.k8s_config_file = None
        self.logger_config_file = None
        self.docker_config_file = None
        self.web_config_file = None
        self.database_config_file = None
        self.rest_api_config_file = None

    def set_configs_from_pytest_args(self, session):
        """
        Sets the configs from pytest args
        Args:
            session (): the pytest session

        Returns:

        """
        lab_config_file = session.config.getoption('--lab_config_file')
        if lab_config_file:
            self.set_lab_config_file(lab_config_file)

        k8s_config_file = session.config.getoption('--k8s_config_file')
        if k8s_config_file:
            self.set_k8s_config_file(k8s_config_file)

        logger_config_file = session.config.getoption('--logger_config_file')
        if logger_config_file:
            self.set_logger_config_file(logger_config_file)

        docker_config_file = session.config.getoption('--docker_config_file')
        if docker_config_file:
            self.set_docker_config_file(docker_config_file)

        web_config_file = session.config.getoption('--web_config_file')
        if web_config_file:
            self.set_web_config_file(web_config_file)

        database_config_file = session.config.getoption('--database_config_file')
        if database_config_file:
            self.set_database_config_file(database_config_file)

        rest_api_config_file = session.config.getoption('--rest_api_config_file')
        if rest_api_config_file:
            self.set_rest_api_config_file(rest_api_config_file)

    def set_configs_from_options_parser(self, parser: OptionParser = None):
        """
        Sets the config files from options parser
        Args:
            parser - (optional) this is needed for the case where we have other command line options besides just config,
                     in these cases the parser will need to be instantiated and the other options added before passing to
                     config location manager.

        Returns:

        """

        options = self._add_options(parser)

        lab_config_file = options.lab_config_file
        if lab_config_file:
            self.set_lab_config_file(lab_config_file)

        k8s_config_file = options.k8s_config_file
        if k8s_config_file:
            self.set_k8s_config_file(k8s_config_file)

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

    def _add_options(self, parser: OptionParser):
        """
        Adds the command line options we can expect
        Returns:

        """
        if not parser:
            parser = OptionParser()

        parser.add_option(
            '--lab_config_file',
            action='store',
            type='str',
            dest='lab_config_file',
            help='the lab file used for scanning',
        )

        parser.add_option(
            '--k8s_config_file',
            action='store',
            type='str',
            dest='k8s_config_file',
            help='the k8s config file',
        )

        parser.add_option(
            '--logger_config_file',
            action='store',
            type='str',
            dest='logger_config_file',
            help='the logger config file',
        )

        parser.add_option(
            '--docker_config_file',
            action='store',
            type='str',
            dest='docker_config_file',
            help='the docker config file',
        )

        parser.add_option(
            '--web_config_file',
            action='store',
            type='str',
            dest='web_config_file',
            help='The Web config file',
        )

        parser.add_option(
            '--database_config_file',
            action='store',
            type='str',
            dest='database_config_file',
            help='The database config file',
        )

        parser.add_option(
            '--rest_api_config_file',
            action='store',
            type='str',
            dest='rest_api_config_file',
            help='The rest api config file',
        )

        options, args = parser.parse_args()

        return options

    def set_lab_config_file(self, lab_config_file):
        """
        Setter for lab config files
        Args:
            lab_config_file (): the location of the lab config file

        Returns:

        """
        self.lab_config_file = lab_config_file

    def get_lab_config_file(self) -> str:
        """
        Getter for lab config file
        Returns: the lab config file

        """
        return self.lab_config_file

    def set_k8s_config_file(self, k8s_config_file):
        """
        Setter for k8s config file
        Args:
            k8s_config_file (): the location of the k8s config file

        Returns:

        """
        self.k8s_config_file = k8s_config_file

    def get_k8s_config_file(self) -> str:
        """
        Getter for k8s config file
        Returns: the k8s config file

        """
        return self.k8s_config_file

    def set_logger_config_file(self, logger_config_file):
        """
        Setter for logger config file
        Args:
            logger_config_file (): the logger config file

        Returns:

        """
        self.logger_config_file = logger_config_file

    def get_logger_config_file(self) -> str:
        """
        Getter for logger config file
        Returns: the logger config file

        """
        return self.logger_config_file

    def set_docker_config_file(self, docker_config_file):
        """
        Setter for docker config file
        Args:
            docker_config_file (): the docker config file

        Returns:

        """
        self.docker_config_file = docker_config_file

    def get_docker_config_file(self) -> str:
        """
        Getter for docker config file
        Returns: the docker config file

        """
        return self.docker_config_file

    def set_web_config_file(self, web_config_file: str):
        """
        Setter for web config file
        Args:
            web_config_file (): the web config file

        Returns:

        """
        self.web_config_file = web_config_file

    def get_web_config_file(self) -> str:
        """
        Getter for web config file
        Returns: the web config file

        """
        return self.web_config_file

    def set_database_config_file(self, database_config_file: str):
        """
        Setter for database config file
        Args:
            database_config_file (): the database config file

        Returns:

        """
        self.database_config_file = database_config_file

    def get_database_config_file(self) -> str:
        """
        Getter for database config file
        Returns: the database config file

        """
        return self.database_config_file

    def set_rest_api_config_file(self, rest_api_config_file: str):
        """
        Setter for rest_api_config_file
        Args:
            rest_api_config_file (): the rest_api_config_file

        Returns:

        """
        self.rest_api_config_file = rest_api_config_file

    def get_rest_api_config_file(self) -> str:
        """
        Getter for rest_api_config_file
        Returns: the rest_api_config_file

        """
        return self.rest_api_config_file
    