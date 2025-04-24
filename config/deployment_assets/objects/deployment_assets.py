from typing import Dict


class DeploymentAssets:
    """
    Class for DeploymentAssets object
    """

    def __init__(self, deployment_assets_dict: Dict[str, str]):
        """
        Constructor

        Args:
            deployment_assets_dict (Dict[str, str]): Dictionary version of the deployment_assets config for controllers or a given subcloud.
        """
        self.bootstrap_file = None
        if "bootstrap_file" in deployment_assets_dict:
            self.bootstrap_file = deployment_assets_dict["bootstrap_file"]

        self.deployment_config_file = None
        if "deployment_config_file" in deployment_assets_dict:
            self.deployment_config_file = deployment_assets_dict["deployment_config_file"]

        self.install_file = None
        if "install_file" in deployment_assets_dict:
            self.install_file = deployment_assets_dict["install_file"]

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
