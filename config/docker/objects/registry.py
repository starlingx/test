class Registry:
    """Represents a Docker registry configuration."""

    def __init__(self, registry_name: str, registry_url: str, user_name: str, password: str):
        """
        Initializes a Registry object.

        Args:
            registry_name (str): Logical name of the registry (e.g., "source_registry").
            registry_url (str): Registry endpoint URL (e.g., "docker.io/starlingx").
            user_name (str): Username for authenticating with the registry.
            password (str): Password for authenticating with the registry.
        """
        self.registry_name = registry_name
        self.registry_url = registry_url
        self.user_name = user_name
        self.password = password

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

    def __str__(self) -> str:
        """
        Returns a human-readable string representation of the registry.

        Returns:
            str: Formatted string showing registry name and URL.
        """
        return f"{self.registry_name} ({self.registry_url})"

    def __repr__(self) -> str:
        """
        Returns the representation string of the registry.

        Returns:
            str: Registry representation.
        """
        return self.__str__()
