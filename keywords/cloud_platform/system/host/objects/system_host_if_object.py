class SystemHostInterfaceObject:
    """
    This class represents a Network Interface as an object.
    This is typically a line in the system host-if-list output table.
    """

    def __init__(self):
        self.uuid = None
        self.name = None
        self.if_class = None
        self.type = None
        self.vlan_id = -1
        self.ports = []
        self.uses_if = []
        self.used_by_if = []
        self.attributes = {}

    def set_uuid(self, uuid: str):
        """
        Setter for the network interface's uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this network interface's uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for the network interface's name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this network interface's name
        """
        return self.name

    def set_if_class(self, if_class: str):
        """
        Setter for the network interface's class
        """
        self.if_class = if_class

    def get_if_class(self) -> str:
        """
        Getter for this network interface's class
        """
        return self.if_class

    def set_type(self, type: str):
        """
        Setter for the network interface's type
        """
        self.type = type

    def get_type(self) -> str:
        """
        Getter for this network interface's type
        """
        return self.type

    def set_vlan_id(self, vlan_id: str):
        """
        Setter for the network interface's VLAN ID
        """
        self.vlan_id = vlan_id

    def get_vlan_id(self) -> str:
        """
        Getter for this network interface's VLAN ID
        """
        return self.vlan_id

    def set_ports(self, ports: list[str]):
        """
        Setter for the network interface's ports
        """
        self.ports = ports

    def get_ports(self) -> list[str]:
        """
        Getter for this network interface's ports
        """
        return self.ports

    def set_uses_if(self, uses_if: list[str]):
        """
        Setter for the network interfaces that this interface uses
        """
        self.uses_if = uses_if

    def get_uses_if(self) -> list[str]:
        """
        Getter for the network interfaces that this interface uses
        """
        return self.uses_if

    def set_used_by_if(self, used_by_if: list[str]):
        """
        Setter for the network interfaces that use this interface
        """
        self.used_by_if = used_by_if

    def get_used_by_if(self) -> list[str]:
        """
        Getter for the network interfaces that use this interface
        """
        return self.used_by_if

    def set_attributes(self, attributes: dict[str, str]):
        """
        Setter for the network interface's attributes
        """
        self.attributes = attributes

    def get_attributes(self) -> dict[str, str]:
        """
        Getter for this network interface's attributes
        """
        return self.attributes
