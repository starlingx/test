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
            (str): release object

        """
        return self.release

    def get_rr(self) -> str:
        """
        Get rr

        Returns:
            (str): rr object

        """
        return self.rr

    def get_state(self) -> str:
        """
        Get state

        Returns:
            (str): state object

        """
        return self.state
