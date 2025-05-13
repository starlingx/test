class SystemApplicationShowObject:
    """
    Represents a system application returned from the 'system application-show' command

    Provides access to key attributes such as status, version, manifest name, etc.
    """

    def __init__(self):
        """
        Initialize with an empty property dictionary
        """
        self._properties = {}

    def set_property(self, key: str, value: str):
        """
        Sets a property in the application's properties dictionary

        Args:
            key (str): The name of the property
            value (str): The value of the property
        """
        self._properties[key] = value

    def get_property(self, key: str) -> str:
        """
        Retrieves a property value from the application's properties dictionary

        Args:
            key (str): The name of the property

        Returns:
            str: The value of the property
        """
        return self._properties.get(key)

    def get_status(self) -> str:
        """
        Retrieves the status of the application

        Returns:
            str: The status of the application
        """
        return self.get_property("status")

    def get_progress(self) -> str:
        """
        Retrieves the progress of the application

        Returns:
            str: The progress of the application
        """
        return self.get_property("progress")

    def get_active(self) -> str:
        """
        Retrieves the active status of the application

        Returns:
            str: 'True' if the application is active, 'False' otherwise
        """
        return self.get_property("active")

    def get_name(self) -> str:
        """
        Retrieves the name of the application

        Returns:
            str: The name of the application
        """
        return self.get_property("name")

    def get_version(self) -> str:
        """
        Retrieves the version of the application

        Returns:
            str: The version of the application
        """
        return self.get_property("app_version")

    def get_manifest_name(self) -> str:
        """
        Retrieves the manifest name used by the application

        Returns:
            str: The manifest name
        """
        return self.get_property("manifest_name")

    def get_manifest_file(self) -> str:
        """
        Retrieves the manifest file used by the application

        Returns:
            str: The manifest file
        """
        return self.get_property("manifest_file")

    def get_created_at(self) -> str:
        """
        Retrieves the creation timestamp of the application

        Returns:
            str: The creation timestamp
        """
        return self.get_property("created_at")

    def get_updated_at(self) -> str:
        """
        Retrieves the last updated timestamp of the application

        Returns:
            str: The last updated timestamp
        """
        return self.get_property("updated_at")
