

class SystemNetworkObject:

    """
    This class represents network as an object.
    """

    def __init__(self):
        self.id: int = -1
        self.uuid: str = None
        self.name: str = None
        self.type: str = None
        self.dynamic: bool = None
        self.pool_uuid: str = None
        self.primary_pool_family: str = None

    def set_id(self, network_id):
        """
        Setter for network id
        """
        self.id = network_id

    def get_id(self) -> int:
        """
        Getter for network id
        """
        return self.id

    def set_uuid(self, uuid):
        """
        Setter for network uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for network UUID
        """
        return self.uuid

    def set_name(self, name):
        """
        Setter for this network's name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this network's name
        """
        return self.name

    def set_type(self, network_type):
        """
        Setter for this network's type
        """
        self.type = network_type

    def get_type(self) -> str:
        """
        Getter for this network's type
        """
        return self.type

    def set_dynamic(self, dynamic):
        """
        Setter for this network's dynamic
        """
        self.dynamic = dynamic

    def get_dynamic(self) -> bool:
        """
        Getter for this network's dynamic
        """
        return self.dynamic

    def set_pool_uuid(self, pool_uuid):
        """
        Setter for this network's pool_uuid
        """
        self.pool_uuid = pool_uuid

    def get_pool_uuid(self) -> str:
        """
        Getter for this network's pool_uuid
        """
        return self.pool_uuid

    def set_primary_pool_family(self, primary_pool_family):
        """
        Setter for this network's primary_pool_family
        """
        self.primary_pool_family = primary_pool_family

    def get_primary_pool_family(self) -> str:
        """
        Getter for this network's primary_pool_family
        """
        return self.primary_pool_family

