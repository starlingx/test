from typing import Dict


class DeploymentAssets:
    """
    Class for DeploymentAssets object
    """

    def __init__(self, controller_name: str, deployment_assets_dict: Dict[str, str]):
        """
        Constructor

        Args:
            controller_name (str): name of the controller where file is present
            deployment_assets_dict (Dict[str, str]): Dictionary version of the deployment_assets config for controllers or a given subcloud.
        """
        self.controller_name = controller_name

        self.bootstrap_file = None
        if "bootstrap_file" in deployment_assets_dict:
            self.bootstrap_file = deployment_assets_dict["bootstrap_file"]

        self.deployment_config_file = None
        if "deployment_config_file" in deployment_assets_dict:
            self.deployment_config_file = deployment_assets_dict["deployment_config_file"]

        self.install_file = None
        if "install_file" in deployment_assets_dict:
            self.install_file = deployment_assets_dict["install_file"]

        self.docker_ca_file = None
        if "docker_ca_file" in deployment_assets_dict:
            self.docker_ca_file = deployment_assets_dict["docker_ca_file"]

    def get_bootstrap_file(self) -> str:
        """
        Getter for the boostrap_file

        Returns (str): boostrap_file
        """
        return self.bootstrap_file.strip() if self.bootstrap_file else self.bootstrap_file

    def get_deployment_config_file(self) -> str:
        """
        Getter for the deployment_config_file

        Returns (str): deployment_config_file
        """
        return self.deployment_config_file.strip()

    def get_install_file(self) -> str:
        """
        Getter for the install_file

        Returns (str): install_file
        """
        return self.install_file.strip()

    def get_docker_ca_file(self) -> str:
        """
        Getter for the docker_ca_file

        Returns (str): docker_ca_file
        """
        return self.docker_ca_file.strip()

    def get_controller_name(self) -> str:
        """
        Getter for the controller_name

        Returns (str): controller_name
        """
        return self.controller_name
