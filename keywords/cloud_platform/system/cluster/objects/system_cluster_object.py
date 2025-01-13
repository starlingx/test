class SystemClusterObject:
    """
    This class represents a cluster as an object.
    This is typically a line in the system cluster output table.
    """

    def __init__(self):
        self.uuid:str = None
        self.cluster_uuid:str = None
        self.type:str = None
        self.name:str = None
        self.deployment_model:str = None
        self.replication_groups:list[str] = []
        self.storage_tiers:list[str] = []


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

    def set_cluster_uuid(self, cluster_uuid: str):
        """
        Setter for the cluster_uuid
        """
        self.cluster_uuid = cluster_uuid

    def get_cluster_uuid(self) -> str:
        """
        Getter for cluster_uuid
        """
        return self.cluster_uuid

    def set_type(self, c_type: str):
        """
        Setter for the type
        """
        self.type = c_type

    def get_type(self) -> str:
        """
        Getter for the type
        """
        return self.type

    def set_name(self, name: str):
        """
        Setter for the name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for the name
        """
        return self.name

    def set_deployment_model(self, deployment_model: str):
        """
        Setter for the deployment_model
        """
        self.deployment_model = deployment_model

    def get_deployment_model(self) -> str:
        """
        Getter for the deployment_model
        """
        return self.deployment_model

    def set_replication_groups(self, replication_groups: []):
        """
        Setter for replication_groups
        """
        self.replication_groups = replication_groups

    def get_replication_groups(self) -> []:
        """
        Getter for replication_groups
        """
        return self.replication_groups

    def set_storage_tiers(self, storage_tiers: []):
        """
        Setter for storage_tiers
        """
        self.storage_tiers = storage_tiers

    def get_storage_tiers(self) -> []:
        """
        Getter for storage_tiers
        """
        return self.storage_tiers
