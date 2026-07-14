"""Software Metapackage List Object."""


class SoftwareMetapackageListObject:
    """Holds attributes of a single row from 'software metapackage list' output."""

    def __init__(self, release: str, rr: str, state: str):
        """Initialize the object.

        Args:
            release (str): Metapackage release name.
            rr (str): RR flag value.
            state (str): Metapackage state (e.g., 'deployed', 'available').
        """
        self.release = release
        self.rr = rr
        self.state = state

    def get_release(self) -> str:
        """Get the release name.

        Returns:
            str: Metapackage release name.
        """
        return self.release

    def get_rr(self) -> str:
        """Get the RR flag.

        Returns:
            str: RR flag value.
        """
        return self.rr

    def get_state(self) -> str:
        """Get the state.

        Returns:
            str: Metapackage state.
        """
        return self.state

    def __str__(self) -> str:
        """Return a human-readable string representation.

        Returns:
            str: Formatted string of release, RR, and state.
        """
        return f"Release: {self.release}, RR: {self.rr}, State: {self.state}"

    def __repr__(self) -> str:
        """Return the developer-facing representation.

        Returns:
            str: Class name and field values.
        """
        return f"{self.__class__.__name__}(release={self.release}, rr={self.rr}, state={self.state})"
