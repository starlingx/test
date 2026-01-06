class SoftwareListObject:
    """
    Class to hold attributes of a software list as returned by software list command
    """

    def __init__(
        self,
        release: str,
        rr: str,
        state: str,
    ):
        self.release = release
        self.rr = rr
        self.state = state

    def get_release(self) -> str:
        """
        Get release

        Returns:
            str: release object

        """
        return self.release

    def get_rr(self) -> str:
        """
        Get rr

        Returns:
            str: rr object

        """
        return self.rr

    def get_state(self) -> str:
        """
        Get state

        Returns:
            str: state object

        """
        return self.state

    def __str__(self) -> str:
        """
        Return a readable string representation of the software list object.

        Returns:
            str: Formatted string of the release, RR, and state.
        """
        return f"Release: {self.release}, RR: {self.rr}, State: {self.state}"

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Object representation with class name and field values.
        """
        return f"{self.__class__.__name__}(release={self.release}, rr={self.rr}, state={self.state})"
