class KubectlServicesObject:
    """
    Class to hold attributes of a 'kubectl get service' entry.
    """

    def __init__(self, name: str):
        """
        Constructor
        Args:
            name: Name of the service.
        """

        self.name = name
        self.type = None
        self.cluster_ip = None
        self.external_ip = None
        self.ports = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry
        Returns: The name of the service.

        """
        return self.name

    def set_type(self, type: str) -> None:
        """
        Setter for type
        Args:
            type:

        Returns: None

        """
        self.type = type

    def get_type(self) -> str:
        """
        Getter for type entry
        """

        return self.type

    def set_cluster_ip(self, cluster_ip: str) -> None:
        """
        Setter for cluster_ip
        Args:
            cluster_ip:

        Returns: None

        """
        self.cluster_ip = cluster_ip

    def get_cluster_ip(self) -> str:
        """
        Getter for cluster_ip entry
        """

        return self.cluster_ip

    def set_external_ip(self, external_ip: str) -> None:
        """
        Setter for external_ip
        Args:
            external_ip:

        Returns: None

        """
        self.external_ip = external_ip

    def get_external_ip(self) -> str:
        """
        Getter for external_ip entry
        """

        return self.external_ip

    def set_age(self, age: str) -> None:
        """
        Setter for AGE
        Args:
            age:

        Returns: None

        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """

        return self.age

    def set_ports(self, ports: str) -> None:
        """
        Setter for ports
        Args:
            ports:

        Returns: None

        """
        self.ports = ports

    def get_ports(self) -> str:
        """
        Getter for ports entry
        """

        return self.ports
