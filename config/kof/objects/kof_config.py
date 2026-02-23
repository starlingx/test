import json5


class KofConfig:
    """Class to hold configuration of Kubernetes Operator Framework applications."""

    def __init__(self, config):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the kof config file: {config}")
            raise

        kof_dict = json5.load(json_data)
        self.kmm_builder_image = kof_dict["kmm_builder_image"]
        self.kmm_container_image_registry = kof_dict["kmm_container_image_registry"]

    def get_kmm_builder_image(self) -> str:
        """Getter for KMM builder image.

        Returns:
            str: the KMM builder image

        """
        return self.kmm_builder_image

    def get_kmm_container_image_registry(self) -> str:
        """Getter for KMM container image registry.

        Returns:
            str: the KMM container image registry

        """
        return self.kmm_container_image_registry
