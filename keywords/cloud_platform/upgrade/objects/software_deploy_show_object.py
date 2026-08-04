class SoftwareDeployShowObject:
    """
    Class to hold attributes of a software deploy show as returned by software deploy show command.

    Supports two output formats:

    Legacy (full release deploy):
        +--------------+------------+------+-------------+--------------+
        | From Release | To Release |  RR  | Pre-Upgrade |    State     |
        +--------------+------------+------+-------------+--------------+
        | 12.00.0      | 13.00.0    | True |    False    | deploy-start |
        +--------------+------------+------+-------------+--------------+

    Metapackage (subset deploy):
        +---------------------------------------------+------+-------------+-------------------+
        | Releases                                    | RR   | Pre-Upgrade |       State       |
        +---------------------------------------------+------+-------------+-------------------+
        | Metapackage    From Release    To Release   | True |    False    | deploy-start-done |
        | -------------  --------------  ------------ |      |             |                   |
        | infra          13.00.0         13.10.100    |      |             |                   |
        +---------------------------------------------+------+-------------+-------------------+
    """

    def __init__(
        self,
        rr: str,
        state: str,
        from_release: str = "",
        to_release: str = "",
        releases: str = "",
    ):
        self.from_release = from_release
        self.to_release = to_release
        self.releases = releases
        self.rr = rr
        self.state = state

    def get_from_release(self) -> str:
        """
        Getter for from_release.

        Returns:
            str: the deployment from release version, or empty string in metapackage format.
        """
        return self.from_release

    def get_to_release(self) -> str:
        """
        Getter for to_release.

        Returns:
            str: the deployment to release version, or empty string in metapackage format.
        """
        return self.to_release

    def get_releases(self) -> str:
        """
        Getter for releases (metapackage format only).

        Returns:
            str: the raw releases cell content, or empty string in legacy format.
        """
        return self.releases

    def get_rr(self) -> str:
        """
        Getter for rr (reboot required field).

        Returns:
            str: (True/False) reboot required
        """
        return self.rr

    def get_state(self) -> str:
        """
        Getter for state.

        Returns:
            str: the deployment state
        """
        return self.state
