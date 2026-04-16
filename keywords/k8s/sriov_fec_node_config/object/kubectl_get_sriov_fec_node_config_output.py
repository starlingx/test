from typing import List

from keywords.k8s.sriov_fec_node_config.object.kubectl_get_sriov_fec_node_config_table_parser import KubectlGetSriovFecNodeConfigTableParser
from keywords.k8s.sriov_fec_node_config.object.kubectl_sriov_fec_node_config_object import KubectlSriovFecNodeConfigObject


class KubectlGetSriovFecNodeConfigOutput:
    """Class for 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com' output."""

    def __init__(self, kubectl_get_sriov_fec_node_config_output: List[str]):
        """Constructor.

        Args:
            kubectl_get_sriov_fec_node_config_output (List[str]): Raw output lines from running the kubectl get command.
        """
        self.sriov_fec_node_configs: List[KubectlSriovFecNodeConfigObject] = []
        table_parser = KubectlGetSriovFecNodeConfigTableParser(kubectl_get_sriov_fec_node_config_output)
        output_values_list = table_parser.get_output_values_list()

        for config_dict in output_values_list:

            if "NAME" not in config_dict:
                raise ValueError(f"There is no NAME associated with the SriovFecNodeConfig: {config_dict}")

            config = KubectlSriovFecNodeConfigObject(config_dict["NAME"])

            if "CONFIGURED" in config_dict:
                config.set_configured(config_dict["CONFIGURED"])

            self.sriov_fec_node_configs.append(config)

    def get_sriov_fec_node_configs(self) -> List[KubectlSriovFecNodeConfigObject]:
        """Return the list of all SriovFecNodeConfigs.

        Returns:
            List[KubectlSriovFecNodeConfigObject]: List of SriovFecNodeConfig objects.
        """
        return self.sriov_fec_node_configs

    def get_sriov_fec_node_config_by_name(self, name: str) -> KubectlSriovFecNodeConfigObject:
        """Return a SriovFecNodeConfig with the specified name.

        Args:
            name (str): The name of the SriovFecNodeConfig to retrieve.

        Returns:
            KubectlSriovFecNodeConfigObject: The SriovFecNodeConfig object with the specified name.

        Raises:
            ValueError: If no SriovFecNodeConfig with the specified name is found.
        """
        for config in self.sriov_fec_node_configs:
            if config.get_name() == name:
                return config
        raise ValueError(f"SriovFecNodeConfig '{name}' not found")

    def has_sriov_fec_node_config(self, name: str) -> bool:
        """Check if a SriovFecNodeConfig with the specified name exists.

        Args:
            name (str): The name of the SriovFecNodeConfig to check.

        Returns:
            bool: True if the SriovFecNodeConfig exists, False otherwise.
        """
        for config in self.sriov_fec_node_configs:
            if config.get_name() == name:
                return True
        return False
