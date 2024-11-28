from keywords.linux.ip.object.ip_object import IPObject


class IPBrAddrObject:
    """
    Class that represents each line of the output of the 'ip -br addr' command as an object structure.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.network_interface_name: str = ""
        self.network_interface_status: str = ""
        self.ip_objects: list[IPObject] = []

    def set_network_interface_name(self, network_interface_name: str):
        """
        Setter for the 'network_interface_name' property.
        """
        self.network_interface_name = network_interface_name

    def get_network_interface_name(self) -> str:
        """
        Getter for this 'network_interface_name' property.
        """
        return self.network_interface_name

    def set_network_interface_status(self, network_interface_status: str):
        """
        Setter for the 'network_interface_status' property.
        """
        self.network_interface_status = network_interface_status

    def get_network_interface_status(self) -> str:
        """
        Getter for this 'network_interface_status' property.
        """
        return self.network_interface_status

    def set_ip_objects(self, ip_objects: list[IPObject]):
        """
        Setter for the 'ip_objects' property.
        """
        self.ip_objects = ip_objects

    def get_ip_objects(self) -> list[IPObject]:
        """
        Getter for this 'ip_objects' property.
        """
        return self.ip_objects
