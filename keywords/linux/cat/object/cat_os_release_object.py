class CatOSReleaseObject:
    """Class to hold attributes of an OS release entry from /etc/os-release."""

    def __init__(self, name: str = ""):
        """Constructor.

        Args:
            name (str): Name of the OS.
        """
        self.name = name
        self.version = ""
        self.id = ""
        self.id_like = ""
        self.version_id = ""
        self.version_codename = ""
        self.pretty_name = ""
        self.ansi_color = ""
        self.home_url = ""
        self.support_url = ""
        self.bug_report_url = ""
        self.privacy_policy_url = ""

    def get_name(self) -> str:
        """Getter for NAME entry.

        Returns:
            str: The name of the OS.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Setter for NAME.

        Args:
            name (str): Name value.
        """
        self.name = name

    def get_version(self) -> str:
        """Getter for VERSION entry.

        Returns:
            str: Version value.
        """
        return self.version

    def set_version(self, version: str) -> None:
        """Setter for VERSION.

        Args:
            version (str): Version value.
        """
        self.version = version

    def get_id(self) -> str:
        """Getter for ID entry.

        Returns:
            str: ID value.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Setter for ID.

        Args:
            id (str): ID value.
        """
        self.id = id

    def get_id_like(self) -> str:
        """Getter for ID_LIKE entry.

        Returns:
            str: ID_LIKE value.
        """
        return self.id_like

    def set_id_like(self, id_like: str) -> None:
        """Setter for ID_LIKE.

        Args:
            id_like (str): ID_LIKE value.
        """
        self.id_like = id_like

    def get_version_id(self) -> str:
        """Getter for VERSION_ID entry.

        Returns:
            str: Version ID value.
        """
        return self.version_id

    def set_version_id(self, version_id: str) -> None:
        """Setter for VERSION_ID.

        Args:
            version_id (str): Version ID value.
        """
        self.version_id = version_id

    def get_version_codename(self) -> str:
        """Getter for VERSION_CODENAME entry.

        Returns:
            str: Version codename value.
        """
        return self.version_codename

    def set_version_codename(self, version_codename: str) -> None:
        """Setter for VERSION_CODENAME.

        Args:
            version_codename (str): Version codename value.
        """
        self.version_codename = version_codename

    def get_pretty_name(self) -> str:
        """Getter for PRETTY_NAME entry.

        Returns:
            str: Pretty name value.
        """
        return self.pretty_name

    def set_pretty_name(self, pretty_name: str) -> None:
        """Setter for PRETTY_NAME.

        Args:
            pretty_name (str): Pretty name value.
        """
        self.pretty_name = pretty_name

    def get_ansi_color(self) -> str:
        """Getter for ANSI_COLOR entry.

        Returns:
            str: ANSI color value.
        """
        return self.ansi_color

    def set_ansi_color(self, ansi_color: str) -> None:
        """Setter for ANSI_COLOR.

        Args:
            ansi_color (str): ANSI color value.
        """
        self.ansi_color = ansi_color

    def get_home_url(self) -> str:
        """Getter for HOME_URL entry.

        Returns:
            str: Home URL value.
        """
        return self.home_url

    def set_home_url(self, home_url: str) -> None:
        """Setter for HOME_URL.

        Args:
            home_url (str): Home URL value.
        """
        self.home_url = home_url

    def get_support_url(self) -> str:
        """Getter for SUPPORT_URL entry.

        Returns:
            str: Support URL value.
        """
        return self.support_url

    def set_support_url(self, support_url: str) -> None:
        """Setter for SUPPORT_URL.

        Args:
            support_url (str): Support URL value.
        """
        self.support_url = support_url

    def get_bug_report_url(self) -> str:
        """Getter for BUG_REPORT_URL entry.

        Returns:
            str: Bug report URL value.
        """
        return self.bug_report_url

    def set_bug_report_url(self, bug_report_url: str) -> None:
        """Setter for BUG_REPORT_URL.

        Args:
            bug_report_url (str): Bug report URL value.
        """
        self.bug_report_url = bug_report_url

    def get_privacy_policy_url(self) -> str:
        """Getter for PRIVACY_POLICY_URL entry.

        Returns:
            str: Privacy policy URL value.
        """
        return self.privacy_policy_url

    def set_privacy_policy_url(self, privacy_policy_url: str) -> None:
        """Setter for PRIVACY_POLICY_URL.

        Args:
            privacy_policy_url (str): Privacy policy URL value.
        """
        self.privacy_policy_url = privacy_policy_url

    def __str__(self) -> str:
        """String representation of the OS release object.

        Returns:
            str: OS name and version.
        """
        return f"OSRelease(name={self.name}, version={self.version})"

    def __repr__(self) -> str:
        """Representation of the OS release object.

        Returns:
            str: OS name and version.
        """
        return self.__str__()