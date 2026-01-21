class SoftwareDeployHostListObject:
    """
    Class to hold attributes of a software deploy host-list entry.

    This represents a single row from the `software deploy host-list` command.
    """

    def __init__(
        self,
        host: str,
        from_release: str,
        to_release: str,
        rr: str,
        state: str,
    ):
        self.host = host
        self.from_release = from_release
        self.to_release = to_release
        self.rr = rr
        self.state = state

    def get_host(self) -> str:
        """
        Get host name.

        Returns:
            str: Host name.
        """
        return self.host

    def get_from_release(self) -> str:
        """
        Get from release.

        Returns:
            str: From release value.
        """
        return self.from_release

    def get_to_release(self) -> str:
        """
        Get to release.

        Returns:
            str: To release value.
        """
        return self.to_release

    def get_rr(self) -> str:
        """
        Get RR (Reboot Required) flag.

        Returns:
            str: RR value as string (e.g., "True", "False").
        """
        return self.rr

    def get_state(self) -> str:
        """
        Get state.

        Returns:
            str: State value.
        """
        return self.state

    def __str__(self) -> str:
        """
        Return a readable string representation of the host-list entry.

        Returns:
            str: Formatted string of host, from/to release, RR, and state.
        """
        return f"Host: {self.host}, " f"From Release: {self.from_release}, " f"To Release: {self.to_release}, " f"RR: {self.rr}, " f"State: {self.state}"

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Object representation with class name and field values.
        """
        return f"{self.__class__.__name__}(" f"host={self.host}, " f"from_release={self.from_release}, " f"to_release={self.to_release}, " f"rr={self.rr}, " f"state={self.state}" f")"
