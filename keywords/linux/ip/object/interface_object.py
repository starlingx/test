class InterfaceObject:
    """
    Class for interface object
    """

    def __init__(self, interface_name: str, mtu: str, state: str, mode: str):
        self.interface_name = interface_name
        self.mtu = mtu
        self.state = state
        self.mode = mode

    def get_interface_name(self) -> str:
        """
        Getter for interface name
        Returns:

        """
        return self.interface_name

    def get_mtu(self) -> str:
        """
        Getter for mtu name
        Returns:

        """
        return self.mtu

    def get_state(self) -> str:
        """
        Getter for state
        Returns:

        """
        return self.state

    def get_mode(self) -> str:
        """
        Getter for mode
        Returns:

        """
        return self.mode
