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
        """Function to change docker registry value"""
        # inject wrong values in Bootstrap values
        self.data["docker_registries"]["k8s.gcr.io"]["url"] = "registry.central:9001/k8s.gcr.io.wrong"
        self.write_yaml()
