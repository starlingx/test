import yaml


class DeploymentAssetsHandler:
    """
    A class for processing YAML files, including reading, writing, and updating values.
    """

    def __init__(self, local_file_yaml: str):
        """Initializes the YamlProcessor.

        Args:
            local_file_yaml (str): yaml file path
        """
        self.local_file = local_file_yaml
        self.data = self._read_yaml()

    def _read_yaml(self) -> None:
        """Reads the YAML file from the local file."""
        try:
            with open(self.local_file, "r") as local_file_st:
                data = yaml.safe_load(local_file_st)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found locally: {self.local_file}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML from local file: {e}")
        return data

    def write_yaml(self):
        """Write the YAML to the local file."""
        try:
            # Write to local file
            with open(self.local_file, "w") as local_file_st:
                yaml.dump(self.data, local_file_st, indent=2)
        except Exception as e:
            raise Exception(f"Error writing YAML file: {e}")

    def inject_wrong_bootstrap_value(self):
        """Inject a wrong docker registry URL to force bootstrap failure.

        Corrupts the registry.k8s.io URL since core Kubernetes components
        (kube-apiserver, etcd, coredns, etc.) are pulled from there during bootstrap.

        Raises:
            KeyError: If docker_registries or registry.k8s.io key is not found.
        """
        if "docker_registries" not in self.data:
            raise KeyError("'docker_registries' key not found in bootstrap YAML")

        registries = self.data["docker_registries"]

        if "registry.k8s.io" not in registries:
            raise KeyError("'registry.k8s.io' key not found in docker_registries")

        original_url = registries["registry.k8s.io"]["url"]
        registries["registry.k8s.io"]["url"] = f"{original_url}.wrong"
        self.write_yaml()

    def modify_management_end_address(self) -> None:
        """Modify management_end_address to a valid but different value for bootstrap replay.

        Decrements the final hextet of an IPv6 management_end_address by one
        (e.g. ...ffff -> ...fffe). The resulting address is still valid, so an
        initial bootstrap succeeds; changing it forces a genuine bootstrap replay
        with an altered configuration value.

        Raises:
            KeyError: If management_end_address key is not found.
            ValueError: If management_end_address cannot be adjusted to a distinct value.
        """
        if "management_end_address" not in self.data:
            raise KeyError("'management_end_address' key not found in bootstrap YAML")

        original_address = self.data["management_end_address"]
        prefix, _, last_hextet = str(original_address).rpartition(":")
        if not prefix:
            raise ValueError(f"Unexpected management_end_address format: '{original_address}'")

        current_value = int(last_hextet, 16)
        new_value = current_value - 1 if current_value > 0 else current_value + 1
        modified_address = f"{prefix}:{new_value:x}"
        if modified_address == original_address:
            raise ValueError(f"Failed to produce a distinct management_end_address from '{original_address}'")

        self.data["management_end_address"] = modified_address
        self.write_yaml()
