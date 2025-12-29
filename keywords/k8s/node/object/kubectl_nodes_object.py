class KubectlNodesObject:
    """
    Class to hold attributes of a 'kubectl get nodes' entry.
    """

    def __init__(self):
        """
        Constructor

        """
        self.name: str = None
        self.status: str = None
        self.roles: str = None
        self.age: str = None
        self.version: str = None
        self.allocatable: dict = {}

    def set_name(self, name: str):
        """
        Setter for the name

        Args:
            name(str): Name of the Node
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for the name of the node.

        Returns: (str) name of the node.

        """
        return self.name

    def set_status(self, status: str):
        """
        Setter for the status

        Args:
            status (str): Status of the Node
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for the status of the node.

        Returns: (str) status of the node.
        """
        return self.status

    def set_roles(self, roles: str):
        """
        Setter for the roles

        Args:
            roles(str): Roles of the Node
        """
        self.roles = roles

    def get_roles(self) -> str:
        """
        Getter for the roles of the node.

        Returns: (str) roles  of the node.
        """
        return self.roles

    def set_age(self, age: str):
        """
        Setter for the age of the node

        Args:
            age(str): Age of the Node
        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for the age of the node.

        Returns: (str) Age of the node.
        """
        return self.age

    def set_version(self, version: str):
        """
        Setter for the version of the node

        Args:
            version(str): Version of the Node
        """
        self.version = version

    def get_version(self) -> str:
        """
        Getter for the version of the node.

        Returns:
             str: Version of the node.
        """
        return self.version

    def set_allocatable(self, allocatable: dict):
        """
        Setter for the allocatable resources

        Args:
            allocatable(dict): Allocatable resources of the Node
        """
        self.allocatable = allocatable

    def get_allocatable(self) -> dict:
        """
        Getter for the allocatable resources of the node.

        Returns:
             dict: Allocatable resources of the node.
        """
        return self.allocatable

    def get_allocatable_resource(self, resource_key: str) -> int:
        """
        Return the allocatable resource value for a specific resource key.

        Args:
            resource_key (str): Resource key, e.g. "dsa.intel.com/wq-user-dedicated".

        Returns:
            int: Resource value for the node, or 0 if missing/non-integer.
        """
        val = self.allocatable.get(resource_key)
        return int(val) if val and str(val).isdigit() else 0
