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

        # Validate manifest_registry_map entries
        manifest_map = self._config_dict.get("manifest_registry_map", {})
        for manifest_path, entry in manifest_map.items():
            if isinstance(entry, dict):
                override = entry.get("override", False)
                manifest_registry = entry.get("manifest_registry", None)
                if override and manifest_registry is None:
                    raise ValueError(f"Invalid manifest_registry_map entry for '{manifest_path}': " "override=true requires 'manifest_registry' to be set (not null).")

        for registry_key in self._config_dict.get("registries", {}):
            registry_dict = self._config_dict["registries"][registry_key]
            reg = Registry(
                registry_name=registry_dict["registry_name"],
                registry_url=registry_dict["registry_url"],
                user_name=registry_dict["user_name"],
                password=registry_dict["password"],
                path_prefix=registry_dict.get("path_prefix"),
            )
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

    def get_manifest_registry_map(self) -> dict:
        """
        Returns the mapping of manifest file paths to registry definitions.

        Returns:
            dict: Mapping of manifest file path -> dict with 'manifest_registry' and 'override'.
        """
        return self._config_dict.get("manifest_registry_map", {})

    def get_effective_source_registry_name(self, image: dict, manifest_filename: str) -> str:
        """
        Resolves the source registry name for a given image using the following precedence:

        1. If a manifest entry exists in "manifest_registry_map":
            - If "override" is true, use the manifest's "manifest_registry" (must not be null).
            - If "override" is false:
                a. If the image has "source_registry", use it.
                b. If the manifest's "manifest_registry" is set (not null), use it.
                c. Otherwise, use "default_source_registry".
        2. If no manifest entry exists:
            - If the image has "source_registry", use it.
            - Otherwise, use "default_source_registry".

        Args:
            image (dict): An image entry from the manifest.
            manifest_filename (str): Filename of the manifest.

        Returns:
            str: The resolved logical registry name.

        Raises:
            ValueError: If "override" is true but "manifest_registry" is null.
        """
        manifest_map = self.get_manifest_registry_map()
        manifest_entry = manifest_map.get(manifest_filename)

        if manifest_entry:
            manifest_registry = manifest_entry.get("manifest_registry")
            override = manifest_entry.get("override", False)

            if override:
                if manifest_registry is None:
                    raise ValueError(f"Invalid manifest_registry_map entry for '{manifest_filename}': " "override=true requires 'manifest_registry' to be set (not null).")
                return manifest_registry

            # override == False
            if "source_registry" in image:
                return image["source_registry"]

            if manifest_registry is not None:
                return manifest_registry

            return self.get_default_source_registry_name()

        # No manifest entry
        if "source_registry" in image:
            return image["source_registry"]

        return self.get_default_source_registry_name()
