class KubectlExecOSReleaseObject:
    """
    Class to hold attributes of /etc/os-release content from a pod.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.name = ""
        self.version = ""
        self.id = ""
        self.version_id = ""
        self.pretty_name = ""

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
            str: The name of the OS.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """
        Setter for NAME.

        Args:
            name (str): Name value.
        """
        self.name = name

    def get_version(self) -> str:
        """
        Getter for VERSION entry.

        Returns:
            str: Version value.
        """
        return self.version

    def set_version(self, version: str) -> None:
        """
        Setter for VERSION.

        Args:
            version (str): Version value.
        """
        self.version = version

    def get_id(self) -> str:
        """
        Getter for ID entry.

        Returns:
            str: ID value.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """
        Setter for ID.

        Args:
            id (str): ID value.
        """
        self.id = id

    def get_version_id(self) -> str:
        """
        Getter for VERSION_ID entry.

        Returns:
            str: Version ID value.
        """
        return self.version_id

    def set_version_id(self, version_id: str) -> None:
        """
        Setter for VERSION_ID.

        Args:
            version_id (str): Version ID value.
        """
        self.version_id = version_id

    def get_pretty_name(self) -> str:
        """
        Getter for PRETTY_NAME entry.

        Returns:
            str: Pretty name value.
        """
        return self.pretty_name

    def set_pretty_name(self, pretty_name: str) -> None:
        """
        Setter for PRETTY_NAME.

        Args:
            pretty_name (str): Pretty name value.
        """
        self.pretty_name = pretty_name

    def __str__(self) -> str:
        """
        String representation of the OS release object.

        Returns:
            str: OS name and version.
        """
        return f"OSRelease(name={self.name}, version={self.version})"

    def __repr__(self) -> str:
        """
        Representation of the OS release object.

        Returns:
            str: OS name and version.
        """
        return self.__str__()
