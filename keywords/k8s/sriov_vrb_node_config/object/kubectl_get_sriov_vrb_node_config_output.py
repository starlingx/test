from typing import List

from keywords.k8s.sriov_vrb_node_config.object.kubectl_get_sriov_vrb_node_config_table_parser import KubectlGetSriovVrbNodeConfigTableParser
from keywords.k8s.sriov_vrb_node_config.object.kubectl_sriov_vrb_node_config_object import KubectlSriovVrbNodeConfigObject


class KubectlGetSriovVrbNodeConfigOutput:
    """Class for 'kubectl get sriovvrbnodeconfigs.sriovvrb.intel.com' output."""

    def __init__(self, kubectl_get_sriov_vrb_node_config_output: List[str]):
        """Constructor.

        Args:
            kubectl_get_sriov_vrb_node_config_output (List[str]): Raw output lines from running the kubectl get command.
        """
        self.sriov_vrb_node_configs: List[KubectlSriovVrbNodeConfigObject] = []
        table_parser = KubectlGetSriovVrbNodeConfigTableParser(kubectl_get_sriov_vrb_node_config_output)
        output_values_list = table_parser.get_output_values_list()

        for config_dict in output_values_list:

            if "NAME" not in config_dict:
                raise ValueError(f"There is no NAME associated with the SriovVrbNodeConfig: {config_dict}")

            config = KubectlSriovVrbNodeConfigObject(config_dict["NAME"])

            if "CONFIGURED" in config_dict:
                config.set_configured(config_dict["CONFIGURED"])

            self.sriov_vrb_node_configs.append(config)

    def get_sriov_vrb_node_configs(self) -> List[KubectlSriovVrbNodeConfigObject]:
        """Return the list of all SriovVrbNodeConfigs.

        Returns:
            List[KubectlSriovVrbNodeConfigObject]: List of SriovVrbNodeConfig objects.
        """
        return self.sriov_vrb_node_configs

    def get_sriov_vrb_node_config_by_name(self, name: str) -> KubectlSriovVrbNodeConfigObject:
        """Return a SriovVrbNodeConfig with the specified name.

        Args:
            name (str): The name of the SriovVrbNodeConfig to retrieve.

        Returns:
            KubectlSriovVrbNodeConfigObject: The SriovVrbNodeConfig object with the specified name.

        Raises:
            ValueError: If no SriovVrbNodeConfig with the specified name is found.
        """
        for config in self.sriov_vrb_node_configs:
            if config.get_name() == name:
                return config
        raise ValueError(f"SriovVrbNodeConfig '{name}' not found")
