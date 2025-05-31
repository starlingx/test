from typing import List

import json5

from config.docker.objects.registry import Registry


class DockerConfig:
    """
    Holds configuration for Docker registries and image sync manifests.

    This class parses the contents of a Docker config JSON5 file, exposing registry
    definitions and optional image manifest paths for use by automation keywords.
    """

    def __init__(self, config: str):
        """
        Initializes the DockerConfig object by loading the specified config file.

        Args:
            config (str): Path to the Docker configuration file (e.g., default.json5).

        Raises:
            FileNotFoundError: If the file is not found.
            ValueError: If the config is missing required fields.
        """
        self.registry_list: List[Registry] = []

        try:
            with open(config) as f:
                self._config_dict = json5.load(f)
        except FileNotFoundError:
            print(f"Could not find the Docker config file: {config}")
            raise

        for registry_key in self._config_dict.get("registries", {}):
            registry_dict = self._config_dict["registries"][registry_key]
            reg = Registry(registry_name=registry_dict["registry_name"], registry_url=registry_dict["registry_url"], user_name=registry_dict["user_name"], password=registry_dict["password"])
            self.registry_list.append(reg)

    def get_registry(self, registry_name: str) -> Registry:
        """
        Retrieves a registry object by logical name.

        Args:
            registry_name (str): Logical name (e.g., 'dockerhub', 'local_registry').

        Returns:
            Registry: Matching registry object.

        Raises:
            ValueError: If the registry name is not found.
        """
        registries = list(filter(lambda r: r.get_registry_name() == registry_name, self.registry_list))
        if not registries:
            raise ValueError(f"No registry with the name '{registry_name}' was found")
        return registries[0]

    def get_image_manifest_files(self) -> List[str]:
        """
        Returns the list of image manifest file paths defined in the config.

        Returns:
            List[str]: List of paths to manifest YAML files.

        Raises:
            ValueError: If the value is neither a string nor a list.
        """
        manifests = self._config_dict.get("image_manifest_files", [])
        if isinstance(manifests, str):
            return [manifests]
        if not isinstance(manifests, list):
            raise ValueError("image_manifest_files must be a string or list of strings")
        return manifests

    def get_default_source_registry_name(self) -> str:
        """
        Returns the default source registry name defined in config (if any).

        Returns:
            str: Logical registry name (e.g., 'dockerhub'), or empty string.
        """
        return self._config_dict.get("default_source_registry", "")

    def get_registry_for_manifest(self, manifest_path: str) -> str:
        """
        Returns the default registry name for a given manifest path, if defined.

        Args:
            manifest_path (str): Full relative path to the manifest file.

        Returns:
            str: Logical registry name (e.g., 'dockerhub'), or empty string.
        """
        return self._config_dict.get("manifest_registry_map", {}).get(manifest_path, "")

    def get_manifest_registry_map(self) -> dict:
        """
        Returns the mapping of manifest file paths to registry names.

        Returns:
            dict: Mapping of manifest file path -> logical registry name.
        """
        return self._config_dict.get("manifest_registry_map", {})

    def get_effective_source_registry_name(self, image: dict, manifest_filename: str) -> str:
        """
        Resolves the source registry name for a given image using the following precedence:

        1. The "source_registry" field in the image entry (if present).
        2. A per-manifest registry mapping defined in "manifest_registry_map" in the config.
        3. The global "default_source_registry" defined in the config.

        Args:
            image (dict): An image entry from the manifest.
            manifest_filename (str): Filename of the manifest (e.g., 'stx-test-images.yaml').

        Returns:
            str: The resolved logical registry name (e.g., 'dockerhub').
        """
        if "source_registry" in image:
            return image["source_registry"]

        manifest_map = self.get_manifest_registry_map()
        if manifest_filename in manifest_map:
            return manifest_map[manifest_filename]

        return self.get_default_source_registry_name()
