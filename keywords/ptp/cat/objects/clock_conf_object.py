class ClockConfObject:
    """
    Object to hold the values of Clock conf Object
    """

    def __init__(self):
        self.ifname: str = ""
        self.base_port: str = ""
        self.sma_name: str = ""
        self.sma_mode: str = ""

    def set_ifname(self, ifname: str):
        """
        Setter for ifname

        Args:
            ifname (str): the ifname

        """
        self.ifname = ifname

    def get_ifname(self) -> str:
        """
        Getter for ifname

        Returns:
            str: the ifname

        """
        return self.ifname

    def set_base_port(self, base_port: str):
        """
        Setter for base_port

        Args:
            base_port (str): the base_port

        """
        self.base_port = base_port

    def get_base_port(self) -> str:
        """
        Getter for base_port

        Returns:
            str: the base_port

        """
        return self.base_port

    def set_sma_name(self, sma_name: str):
        """
        Setter for sma_name

        Args:
            sma_name (str): the sma_name

        """
        self.sma_name = sma_name

    def get_sma_name(self) -> str:
        """
        Getter for sma_name

        Returns:
            str: the sma_name

        """
        return self.sma_name

    def set_sma_mode(self, sma_mode: str):
        """
        Setter for sma_mode

        Args:
            sma_mode (str): the sma_mode

        """
        self.sma_mode = sma_mode

    def get_sma_mode(self) -> str:
        """
        Getter for sma_mode

        Returns:
            str: the sma_mode

        """
        return self.sma_mode
