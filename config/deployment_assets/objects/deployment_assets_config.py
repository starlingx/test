import json5

from config.deployment_assets.objects.deployment_assets import DeploymentAssets


class DeploymentAssetsConfig:
    """
    Class to hold configuration for Deployment Assets
    """

    def __init__(self, config):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the Deployment Assets config file: {config}")
            raise

        deployment_assets_dict = json5.load(json_data)
        controller_name, dep_assets_dict = deployment_assets_dict["controller"].popitem()
        self.controller_deployment_assets = DeploymentAssets(controller_name, dep_assets_dict)

        self.subclouds_deployment_assets = {}
        if "subclouds" in deployment_assets_dict:
            subclouds_dict = deployment_assets_dict["subclouds"]
            for subcloud_name in subclouds_dict.keys():
                self.subclouds_deployment_assets[subcloud_name] = DeploymentAssets(None, subclouds_dict[subcloud_name])

    def get_controller_deployment_assets(self) -> DeploymentAssets:
        """
        Getter for the controller deployment assets

        Returns:
            DeploymentAssets:

        """
        return self.controller_deployment_assets

    def get_subcloud_deployment_assets(self, subcloud_name: str) -> DeploymentAssets:
        """
        Getter for the deployment assets associated with the specified subcloud.

        Args:
            subcloud_name (str): Name of the subcloud.

        Returns:
            DeploymentAssets:

        """
        if subcloud_name not in self.subclouds_deployment_assets:
            raise Exception(f"There is no DeploymentAssets configuration set for {subcloud_name}")
        return self.subclouds_deployment_assets[subcloud_name]
