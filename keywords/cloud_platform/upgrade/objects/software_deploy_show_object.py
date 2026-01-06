class SoftwareDeployShowObject:
    """
    Class to hold attributes of a software deploy show as returned by software deploy show command

    """

    def __init__(
        self,
        from_release: str,
        to_release: str,
        rr: str,
        state: str,
    ):
        self.from_release = from_release
        self.to_release = to_release
        self.rr = rr
        self.state = state

    def get_from_release(self) -> str:
        """
        Getter for from_release

        Returns:
            str: the deployment from release version

        """
        return self.from_release

    def get_to_release(self) -> str:
        """
        Getter for to_release

        Returns:
            str: the deployment to release version

        """
        return self.to_release

    def get_rr(self) -> str:
        """
        Getter for rr (reboot required field)

        Returns:
            str: (True/False) reboot required

        """
        return self.rr

    def get_state(self) -> str:
        """
        Getter for state

        Returns:
            str: the deployment state

        """
        return self.state
