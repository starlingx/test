class PtpCguInputObject:
    """
    Class for PTP CGU Input Object.
    """

    def __init__(
        self, name: str, idx: int, state: str, eec: int, pps: int, esync_fail: str
    ):
        self.name = name
        self.idx = idx
        self.state = state
        self.eec = eec
        self.pps = pps
        self.esync_fail = esync_fail

    def get_name(self) -> str:
        """
        Getter for name.

        Returns:
            str: the name.
        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for name.

        Args:
            name (str): the name.

        """
        self.name = name

    def get_idx(self) -> str:
        """
        Gets the unique identifier.

        Returns:
            str: The unique identifier.
        """
        return self.idx

    def set_idx(self, idx: str) -> None:
        """
        Sets the unique identifier.

        Args:
            idx (str): The new unique identifier.
        """
        self.idx = idx

    def get_state(self) -> str:
        """
        Gets the state.

        Returns:
            str: The state.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """Sets the state.

        Args:
            state (str): The new state.
        """
        self.state = state

    def get_eec(self) -> int:
        """
        Gets the EEC value.

        Returns:
            int: The EEC value.
        """
        return self.eec

    def set_eec(self, eec: int) -> None:
        """
        Sets the EEC value.

        Args:
            eec (int): The new EEC value.
        """
        self.eec = eec

    def get_pps(self) -> int:
        """
        Gets the PPS value.

        Returns:
            int: The PPS value.
        """
        return self.pps

    def set_pps(self, pps: int) -> None:
        """
        Sets the PPS value.

        Args:
            pps (int): The new PPS value.
        """
        self.pps = pps

    def get_esync_fail(self) -> str:
        """
        Gets the ESYNC failure status.

        Returns:
            str: The ESYNC failure status.
        """
        return self.esync_fail

    def set_esync_fail(self, esync_fail: str) -> None:
        """
        Sets the ESYNC failure status.

        Args:
            esync_fail (str): The new ESYNC failure status.
        """
        self.esync_fail = esync_fail
