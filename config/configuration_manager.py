from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.database.objects.database_config import DatabaseConfig
from config.docker.objects.docker_config import DockerConfig
from config.k8s.objects.k8s_config import K8sConfig
from config.lab.objects.lab_config import LabConfig
from config.logger.objects.logger_config import LoggerConfig
from config.ptp.objects.ptp_config import PTPConfig
from config.rest_api.objects.rest_api_config import RestAPIConfig
from config.web.objects.web_config import WebConfig
from framework.resources.resource_finder import get_stx_resource_path


class ConfigurationManagerClass:
    """
    Singleton class for loading and storing configs.
    """

    def __init__(self):
        self.loaded = False
        self.lab_config: LabConfig = None
        self.k8s_config: K8sConfig = None
        self.ptp_config: PTPConfig = None
        self.logger_config: LoggerConfig = None
        self.docker_config: DockerConfig = None
        self.web_config: WebConfig = None
        self.database_config: DatabaseConfig = None
        self.rest_api_config: RestAPIConfig = None
        self.configuration_locations_manager = None

    def is_config_loaded(self) -> bool:
        """
        This function will return true if the configurations are already loaded.

        Returns (bool):

        """
        return self.loaded

    def load_configs(self, config_file_locations: ConfigurationFileLocationsManager):
        """
        This function will load all the config files.

        By default, the default.json5 files in each configuration folder will get loaded.
        If a config_file parameter is specified, that file will be used instead for that config.

        Args:
            config_file_locations (ConfigurationFileLocationsManager): class with all the config file locations

        """
        self.configuration_locations_manager = config_file_locations

        lab_config_file = config_file_locations.get_lab_config_file()
        if not lab_config_file:
            lab_config_file = get_stx_resource_path("config/lab/files/default.json5")

        k8s_config_file = config_file_locations.get_k8s_config_file()
        if not k8s_config_file:
            k8s_config_file = get_stx_resource_path("config/k8s/files/default.json5")

        ptp_config_file = config_file_locations.get_ptp_config_file()
        if not ptp_config_file:
            ptp_config_file = get_stx_resource_path("config/ptp/files/default.json5")

        logger_config_file = config_file_locations.get_logger_config_file()
        if not logger_config_file:
            logger_config_file = get_stx_resource_path("config/logger/files/default.json5")

        docker_config_file = config_file_locations.get_docker_config_file()
        if not docker_config_file:
            docker_config_file = get_stx_resource_path("config/docker/files/default.json5")

        web_config_file = config_file_locations.get_web_config_file()
        if not web_config_file:
            web_config_file = get_stx_resource_path("config/web/files/default.json5")

        database_config_file = config_file_locations.get_database_config_file()
        if not database_config_file:
            database_config_file = get_stx_resource_path("config/database/files/default.json5")

        rest_api_config_file = config_file_locations.get_rest_api_config_file()
        if not rest_api_config_file:
            rest_api_config_file = get_stx_resource_path("config/rest_api/files/default.json5")

        if not self.loaded:
            try:
                self.lab_config = LabConfig(lab_config_file)
                self.k8s_config = K8sConfig(k8s_config_file)
                self.ptp_config = PTPConfig(ptp_config_file)
                self.logger_config = LoggerConfig(logger_config_file)
                self.docker_config = DockerConfig(docker_config_file)
                self.web_config = WebConfig(web_config_file)
                self.database_config = DatabaseConfig(database_config_file)
                self.rest_api_config = RestAPIConfig(rest_api_config_file)
                self.loaded = True
            except FileNotFoundError as e:
                print(f"Unable to load the config using file: {str(e.filename)} ")
                raise

    def get_lab_config(self) -> LabConfig:
        """
        Getter for lab config.

        Returns (LabConfig): lab config

        """
        return self.lab_config

    def set_lab_config(self, lab_config: LabConfig):
        """
        Setter for lab config.

        Args:
            lab_config (LabConfig): the lab config object representing the content of the lab config file.

        """
        self.lab_config = lab_config

    def get_k8s_config(self) -> K8sConfig:
        """
        Getter for k8s config.

        Returns (K8sConfig): k8s config

        """
        return self.k8s_config

    def get_ptp_config(self) -> PTPConfig:
        """
        Getter for ptp config.

        Returns (PTPConfig): ptp config

        """
        return self.ptp_config

    def get_logger_config(self) -> LoggerConfig:
        """
        Getter for logger config.

        Returns (LoggerConfig): logger config

        """
        return self.logger_config

    def get_docker_config(self) -> DockerConfig:
        """
        Getter for docker config.

        Returns (DockerConfig): the docker config

        """
        return self.docker_config

    def get_web_config(self) -> WebConfig:
        """
        Getter for web config.

        Returns (WebConfig): the web config

        """
        return self.web_config

    def get_database_config(self) -> DatabaseConfig:
        """
        Getter for database config.

        Returns (DatabaseConfig): the database config

        """
        return self.database_config

    def get_rest_api_config(self) -> RestAPIConfig:
        """
        Getter for rest api config.

        Returns (RestAPIConfig): the rest api config

        """
        return self.rest_api_config

    def get_config_pytest_args(self) -> [str]:
        """
        Returns the configuration file locations as pytest args.

        Returns ([str]):

        """
        pytest_config_args = []

        if self.configuration_locations_manager.get_lab_config_file():
            pytest_config_args.append(f"--lab_config_file={self.configuration_locations_manager.get_lab_config_file()}")
        if self.configuration_locations_manager.get_k8s_config_file():
            pytest_config_args.append(f"--k8s_config_file={self.configuration_locations_manager.get_k8s_config_file()}")
        if self.configuration_locations_manager.get_ptp_config_file():
            pytest_config_args.append(f"--ptp_config_file={self.configuration_locations_manager.get_ptp_config_file()}")
        if self.configuration_locations_manager.logger_config_file:
            pytest_config_args.append(f"--logger_config_file{self.configuration_locations_manager.get_logger_config_file()}")
        if self.configuration_locations_manager.docker_config_file:
            pytest_config_args.append(f"--docker_config_file={self.configuration_locations_manager.get_docker_config_file()}")
        if self.configuration_locations_manager.web_config_file:
            pytest_config_args.append(f"--web_config_file={self.configuration_locations_manager.get_web_config_file()}")
        if self.configuration_locations_manager.database_config_file:
            pytest_config_args.append(f"--database_config_file={self.configuration_locations_manager.get_database_config_file()}")
        if self.configuration_locations_manager.rest_api_config_file:
            pytest_config_args.append(f"--rest_api_config_file={self.configuration_locations_manager.get_rest_api_config_file()}")

        return pytest_config_args


ConfigurationManager = ConfigurationManagerClass()
