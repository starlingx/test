class SystemStorageTierObject:
    """
    This class represents a storage tier as an object.
    This is typically a line in the system storage-tier output table.
    """

    def __init__(self):
        self.uuid:str = None
        self.name:str = None
        self.status:str = None
        self.backend_using:str = None
        self.type:str = None
        self.backend_uuid: str = None
        self.cluster_uuid: str = None
        self.osds: [int] = []
        self.created_at: str = None
        self.updated_at: str = None

    def set_uuid(self, uuid: str):
        """
        Setter for the uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for the name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for name
        """
        return self.name

    def set_type(self, s_type: str):
        """
        Setter for the storage tier type
        """
        self.type = s_type

    def get_type(self) -> str:
        """
        Getter for the type
        """
        return self.type

    def set_status(self, status: str):
        """
        Setter for the status
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for the state
        """
        return self.status

    def set_backend_using(self, backend_using: str):
        """
        Setter for the backend_using
        """
        self.backend_using = backend_using

    def get_backend_using(self) -> str:
        """
        Getter for the backend_using
        """
        return self.backend_using

    def set_backend_uuid(self, backend_uuid: str):
        """
        Setter for the backend_uuid
        """
        self.backend_uuid = backend_uuid

    def get_backend_uuid(self) -> str:
        """
        Getter for the backend_uuid
        """
        return self.backend_uuid

    def set_cluster_uuid(self, cluster_uuid: str):
        """
        Setter for the cluster_uuid
        """
        self.cluster_uuid = cluster_uuid

    def get_cluster_uuid(self) -> str:
        """
        Getter for the cluster_uuid
        """
        return self.cluster_uuid

    def set_osds(self, osds: [int]):
        """
        Setter for the osds
        """
        self.osds = osds

    def get_osds(self) -> [int]:
        """
        Getter for the osds
        """
        return self.osds

    def set_created_at(self, created_at):
        """
        Setter for created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at):
        """
        Setter for updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated_at
        """
        return self.updated_at
