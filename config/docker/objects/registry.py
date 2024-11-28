class Registry:
    """
    Class for Registry object
    """

    def __init__(self, registry_name: str, registry_url: str, user_name: str, password: str):
        self.registry_name = registry_name
        self.registry_url = registry_url
        self.user_name = user_name
        self.password = password

    def get_registry_name(self) -> str:
        """
        Getter for registry name
        Returns:

        """
        return self.registry_name

    def get_registry_url(self) -> str:
        """
        Getter for registry url
        Returns:

        """
        return self.registry_url

    def get_user_name(self) -> str:
        """
        Getter for user name
        Returns:

        """
        return self.user_name

    def get_password(self) -> str:
        return self.password
