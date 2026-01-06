from typing import Dict

import json5

from config.docker.objects.registry import Registry


class DockerConfig:
    """
    Holds configuration for Docker image sync.

    Manages Docker registry configuration including:
    - Local registry (destination for synced images)
    - Source registries with authentication credentials
    - Named manifest file mappings
    - Custom registry patterns for canonical name extraction

    Configuration file format: JSON5 with required fields 'local_registry' and 'named_manifests'.
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
        try:
            with open(config) as f:
                self._config_dict = json5.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Could not find the Docker config file: {config}") from e

        # Validate required fields
        if "local_registry" not in self._config_dict:
            raise ValueError("Config missing required field: 'local_registry'")
        if "named_manifests" not in self._config_dict:
            raise ValueError("Config missing required field: 'named_manifests'")

        # Parse local_registry
        local_reg_dict = self._config_dict["local_registry"]
        self.local_registry = Registry(
            registry_name="local_registry",
            registry_url=local_reg_dict["url"],
            user_name=local_reg_dict.get("username", ""),
            password=local_reg_dict.get("password", ""),
        )

        # Parse source_registries (optional - for authenticated pulls from external registries)
        # Note: For source registries, the URL serves as both the lookup key (in the map)
        # and the registry identity, so registry_name is set to the same value as registry_url.
        # This is semantically correct: the name of "docker.io" IS "docker.io".
        self.source_registries: Dict[str, Registry] = {}
        if "source_registries" in self._config_dict:
            for reg_host, creds in self._config_dict["source_registries"].items():
                self.source_registries[reg_host] = Registry(
                    registry_name=reg_host,  # URL is the identity for source registries
                    registry_url=reg_host,  # Connection endpoint (same as name)
                    user_name=creds.get("username", ""),
                    password=creds.get("password", ""),
                )

    def get_local_registry(self) -> Registry:
        """
        Returns the local registry configuration.

        Returns:
            Registry: Local registry object.
        """
        return self.local_registry

    def get_named_manifest(self, manifest_name: str) -> str:
        """
        Retrieves the path to a named manifest.

        Args:
            manifest_name (str): Logical name of the manifest (e.g., "sanity", "networking").

        Returns:
            str: Path to the manifest YAML file.

        Raises:
            ValueError: If the manifest name is not found in config.
        """
        named_manifests = self._config_dict.get("named_manifests", {})
        if manifest_name not in named_manifests:
            available = list(named_manifests.keys())
            raise ValueError(f"Named manifest '{manifest_name}' not found in config. Available: {available}")
        return named_manifests[manifest_name]

    def get_named_manifests(self) -> Dict[str, str]:
        """
        Returns all named manifests defined in config.

        Returns:
            Dict[str, str]: Mapping of manifest name -> manifest path.
        """
        return self._config_dict.get("named_manifests", {})

    def get_source_registries(self) -> Dict[str, Registry]:
        """
        Returns all configured source registries with authentication credentials.

        Source registries are external registries that require authentication for pulling images.
        The dictionary maps registry URL (e.g., "docker.io", "registry.example.com:5000")
        to Registry objects containing credentials.

        Returns:
            Dict[str, Registry]: Mapping of registry URL -> Registry object with credentials.
        """
        return self.source_registries

    def get_source_registry_for_image(self, image_ref: str) -> Registry | None:
        """
        Find matching source registry credentials for an image reference.

        Matches the image reference against configured source registry URLs.
        Returns credentials if a matching registry is found.

        Args:
            image_ref (str): Full image reference including registry URL
                            (e.g., "registry.example.com:5000/myapp/backend:v1.2.3")

        Returns:
            Registry | None: Registry object with credentials if match found, None otherwise

        Examples:
            >>> config.get_source_registry_for_image("registry.example.com:5000/myapp/backend:v1.2.3")
            <Registry: registry.example.com:5000>

            >>> config.get_source_registry_for_image("docker.io/library/busybox:1.36.1")
            <Registry: docker.io>

            >>> config.get_source_registry_for_image("public-registry.io/image:tag")
            None  # No credentials configured for this registry
        """
        for reg_host, registry in self.source_registries.items():
            # Match registry at proper boundary per Docker image format: <registry>/<namespace>/<image>:<tag>
            # Registry part must be followed by '/' to avoid matching "registry.io:5000" when config has "registry.io:500"
            if image_ref.startswith(f"{reg_host}/"):
                return registry
        return None

    def get_custom_registry_patterns(self) -> list[str]:
        """
        Returns list of custom registry patterns for canonical name extraction.

        Custom registry patterns identify public registries that don't require authentication
        but aren't in the built-in PUBLIC_REGISTRY_PATTERNS list. Examples include:
        - Corporate Docker mirrors (e.g., "mirror.company.com/dockerhub/")
        - Public Harbor registries (e.g., "public-harbor.example.com/")
        - Regional registry caches

        These patterns enable extracting canonical names from mirrored images.
        For example, with pattern "mirror.company.com/":
          mirror.company.com/namespace/app:tag -> namespace/app:tag

        Returns:
            list[str]: List of registry patterns as configured (may or may not include trailing "/")
        """
        return self._config_dict.get("custom_registry_patterns", [])
