class DpkgStatusObject:
    """
    This class represents a Package's information as an object.
    This is obtained by running 'dpkg -s <package_name>'
    """

    def __init__(self):
        self.package: str = None
        self.status: str = None
        self.priority: str = None
        self.section: str = None
        self.installed_size: int = -1
        self.maintainer: str = None
        self.architecture: str = None
        self.version: str = None
        self.depends: str = None
        self.description: str = None
        self.homepage: str = None

    def set_package(self, package: str) -> None:
        """
        Sets the package name.

        Args:
            package: The name of the package (str).
        """
        self.package = package

    def get_package(self) -> str:
        """
        Gets the package name.

        Returns:
            The name of the package (str).
        """
        return self.package

    def set_status(self, status: str) -> None:
        """
        Sets the status of the package

        Args:
            status: The status of the package (str).
        """
        self.status = status

    def get_status(self) -> str:
        """
        Gets the status of the package.

        Returns:
            The status of the package (str).
        """
        return self.status

    def set_priority(self, priority: str) -> None:
        """
        Sets the priority

        Args:
            priority: The priority
        """
        self.priority = priority

    def get_priority(self) -> str:
        """
        Gets the priority

        Returns:
            The priority
        """
        return self.priority

    def set_section(self, section: str) -> None:
        """
        Sets the section

        Args:
            section: The section
        """
        self.section = section

    def get_section(self) -> str:
        """
        Gets the section

        Returns:
          The section
        """
        return self.section

    def set_installed_size(self, installed_size: int) -> None:
        """
        Sets the installed size

        Args:
          installed_size: The installed size of the package (int).
        """
        self.installed_size = installed_size

    def get_installed_size(self) -> int:
        """
        Gets the installed size

        Returns:
          The installed size of the package (int).
        """
        return self.installed_size

    def set_maintainer(self, maintainer: str) -> None:
        """
        Sets the maintainer of the package.

        Args:
            maintainer: The maintainer of the package (str).
        """
        self.maintainer = maintainer

    def get_maintainer(self) -> str:
        """
        Gets the maintainer of the package.

        Returns:
            The maintainer of the package (str).
        """
        return self.maintainer

    def set_architecture(self, architecture: str) -> None:
        """
        Sets the architecture.

        Args:
            architecture: The architecture
        """
        self.architecture = architecture

    def get_architecture(self) -> str:
        """
        Gets the architecture.

        Returns:
            The architecture.
        """
        return self.architecture

    def set_version(self, version: str) -> None:
        """
        Sets the version of the package.

        Args:
            version: The version of the package (str).
        """
        self.version = version

    def get_version(self) -> str:
        """
        Gets the version of the package.

        Returns:
            The version of the package (str).
        """
        return self.version

    def set_depends(self, depends: str) -> None:
        """
        Sets the dependencies of the package.

        Args:
            depends: The dependencies of the package (str).
        """
        self.depends = depends

    def get_depends(self) -> str:
        """
        Gets the dependencies of the package.

        Returns:
             The dependencies of the package (str).
        """
        return self.depends

    def append_description(self, description: str) -> None:
        """
        Sets the description of the package.
        If the description is already set, appends description in a new line.

        Args:
            description: The description of the package (str).
        """
        if self.description:
            self.description += "\n" + description
        else:
            self.description = description

    def get_description(self) -> str:
        """
        Gets the description of the package.

        Returns:
             The description of the package (str).
        """
        return self.description

    def set_homepage(self, homepage: str) -> None:
        """
        Sets the homepage.

        Args:
            homepage: The homepage.
        """
        self.homepage = homepage

    def get_homepage(self) -> str:
        """
        Gets the homepage.

        Returns:
             The homepage.
        """
        return self.homepage
