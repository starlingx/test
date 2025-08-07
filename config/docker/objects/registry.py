class Registry:
    """Represents a Docker registry configuration."""

    def __init__(self, registry_name: str, registry_url: str, user_name: str, password: str, path_prefix: str = None):
        """
        Initializes a Registry object.

        Args:
            registry_name (str): Logical name of the registry (e.g., "source_registry").
            registry_url (str): Registry endpoint URL (e.g., "docker.io").
            user_name (str): Username for authenticating with the registry.
            password (str): Password for authenticating with the registry.
            path_prefix (str): Optional path prefix for registry projects (e.g., "project/namespace/").
        """
        self.registry_name = registry_name
        self.registry_url = registry_url
        self.user_name = user_name
        self.password = password
        self.path_prefix = path_prefix or ""

    def get_registry_name(self) -> str:
        """
        Returns the logical name of the registry.

        Returns:
            str: Registry name.
        """
        return self.registry_name

    def get_registry_url(self) -> str:
        """
        Returns the URL endpoint of the registry.

        Returns:
            str: Registry URL.
        """
        return self.registry_url

    def get_user_name(self) -> str:
        """
        Returns the username used for registry authentication.

        Returns:
            str: Username.
        """
        return self.user_name

    def get_password(self) -> str:
        """
        Returns the password used for registry authentication.

        Returns:
            str: Password.
        """
        return self.password

    def get_path_prefix(self) -> str:
        """
        Returns the path prefix prepended to image names during sync operations.

        The path prefix enables organizational separation within the same registry host,
        such as Harbor projects or private registry namespaces.

        Returns:
            str: Path prefix (e.g., "project/namespace") or empty string for registries
                 like DockerHub that don't require path-based organization.
        """
        return self.path_prefix

    def __str__(self) -> str:
        """
        Returns a human-readable string representation of the registry.

        Returns:
            str: Formatted string showing registry name, URL, and path prefix if present.
        """
        if self.path_prefix:
            return f"{self.registry_name} ({self.registry_url}/{self.path_prefix})"
        return f"{self.registry_name} ({self.registry_url})"

    def __repr__(self) -> str:
        """
        Returns the representation string of the registry for debugging.

        Returns:
            str: Registry representation showing constructor parameters (excluding credentials).
        """
        return f"Registry(registry_name='{self.registry_name}', registry_url='{self.registry_url}', path_prefix='{self.path_prefix}')"
