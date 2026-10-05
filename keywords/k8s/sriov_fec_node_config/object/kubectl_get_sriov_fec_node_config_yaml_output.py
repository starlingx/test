from typing import Dict, List, Optional, Union

import yaml


class KubectlGetSriovFecNodeConfigYamlOutput:
    """Class for 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com -o yaml' output.

    Parses the YAML output of a single SriovFecNodeConfig resource and provides
    methods to query its spec and status sections.
    """

    def __init__(self, kubectl_get_sriov_fec_node_config_yaml_output: Union[str, List[str]]):
        """Constructor.

        Args:
            kubectl_get_sriov_fec_node_config_yaml_output (Union[str, List[str]]): Raw YAML output
                from running 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com <name> -o yaml'.
        """
        if isinstance(kubectl_get_sriov_fec_node_config_yaml_output, list):
            self.raw_output = kubectl_get_sriov_fec_node_config_yaml_output
            yaml_str = "\n".join(kubectl_get_sriov_fec_node_config_yaml_output)
        else:
            self.raw_output = kubectl_get_sriov_fec_node_config_yaml_output.splitlines()
            yaml_str = kubectl_get_sriov_fec_node_config_yaml_output

        self.parsed: Dict = yaml.safe_load(yaml_str) or {}
        self.spec: Dict = self.parsed.get("spec", {})
        self.status: Dict = self.parsed.get("status", {})

    def get_spec(self) -> Dict:
        """Get the spec section of the SriovFecNodeConfig.

        Returns:
            Dict: The spec section as a dictionary.
        """
        return self.spec

    def get_status(self) -> Dict:
        """Get the status section of the SriovFecNodeConfig.

        Returns:
            Dict: The status section as a dictionary.
        """
        return self.status

    def get_physical_functions(self) -> List[Dict]:
        """Get the list of physical functions from the spec section.

        Returns:
            List[Dict]: List of physical function configurations.
        """
        return self.spec.get("physicalFunctions", [])

    def has_physical_functions(self) -> bool:
        """Check if the SriovFecNodeConfig has active physical functions configured.

        Returns:
            bool: True if physical functions are configured and non-empty.
        """
        physical_functions = self.get_physical_functions()
        return len(physical_functions) > 0

    def get_name(self) -> Optional[str]:
        """Get the name of the SriovFecNodeConfig from metadata.

        Returns:
            Optional[str]: The name of the resource, or None if not found.
        """
        metadata = self.parsed.get("metadata", {})
        return metadata.get("name")

    def get_namespace(self) -> Optional[str]:
        """Get the namespace of the SriovFecNodeConfig from metadata.

        Returns:
            Optional[str]: The namespace of the resource, or None if not found.
        """
        metadata = self.parsed.get("metadata", {})
        return metadata.get("namespace")

    def get_raw_output(self) -> List[str]:
        """Get the raw YAML output as a list of lines.

        Returns:
            List[str]: The raw YAML output lines.
        """
        return self.raw_output

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the SriovFecNodeConfig YAML output.
        """
        name = self.get_name() or "unknown"
        has_pf = self.has_physical_functions()
        return f"KubectlGetSriovFecNodeConfigYamlOutput(name={name}, has_physical_functions={has_pf})"
