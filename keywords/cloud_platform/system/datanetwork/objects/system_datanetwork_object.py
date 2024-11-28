class SystemDatanetworkObject:
    """
    Class for System datanetwork object
    """

    def __init__(self):
        self.name: str = None
        self.uuid: str = None
        self.network_type: str = None
        self.mtu: int = -1
        self.description: str = None
        self.id: int = None

    def set_name(self, name: str):
        """
        Setter for name
        Args:
            name (): the name

        Returns:

        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for name
        Returns:

        """
        return self.name

    def set_uuid(self, uuid: str):
        """
        Setter for uuid
        Args:
            uuid (): the uuid

        Returns:

        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns:

        """
        return self.uuid

    def set_network_type(self, network_type: str):
        """
        Setter for network type
        Args:
            network_type (): the network type

        Returns:

        """
        self.network_type = network_type

    def get_network_type(self) -> str:
        """
        Getter for network type
        Returns:

        """
        return self.network_type

    def set_mtu(self, mtu: int):
        """
        Setter for mtu
        Args:
            mtu (): the mtu value

        Returns:

        """
        self.mtu = mtu

    def get_mtu(self) -> int:
        return self.mtu


    def set_description(self, description: str):
        """
        Setter for description
        Args:
            description: the description

        Returns:

        """
        self.description = description

    def get_description(self) -> str:
        """
        Getter for network type
        Returns:
        description of str type or None
        """
        return self.description

    def set_id(self, network_id: int):
        """
        Setter for id
        Args:
            network_id: the id of network

        Returns:

        """
        self.id = network_id

    def get_id(self) -> int:
        """
        Getter for network id
        Returns:
        id of str int
        """
        return self.id