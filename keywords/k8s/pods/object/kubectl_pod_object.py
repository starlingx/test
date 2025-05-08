class KubectlPodObject:
    """
    Class to hold attributes of a 'kubectl get pods' pod entry.
    """

    def __init__(self, name: str):
        """
        Constructor
        Args:
            name: Name of the pod.
        """

        self.name = name
        self.namespace = None
        self.ready = None
        self.status = None
        self.restarts = None
        self.age = None
        self.ip = None
        self.node = None
        self.nominated_node = None
        self.readiness_gates = None

    def get_name(self) -> str:
        """
        Getter for NAME entry
        Returns: The name of the pod.

        """
        return self.name

    def set_namespace(self, namespace: str) -> None:
        """
        Setter for NAMESPACE
        Args:
            namespace:

        Returns: None

        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """
        Getter for NAMESPACE entry
        """

        return self.namespace

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY
        Args:
            ready:

        Returns: None

        """
        self.ready = ready

    def get_ready(self) -> str:
        """
        Getter for READY entry
        """

        return self.ready

    def set_status(self, status: str) -> None:
        """
        Setter for STATUS
        Args:
            status:

        Returns: None

        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for STATUS entry
        """

        return self.status

    def set_restarts(self, restarts: str) -> None:
        """
        Setter for RESTARTS
        Args:
            restarts:

        Returns: None

        """
        self.restarts = restarts

    def get_restarts(self) -> str:
        """
        Getter for RESTARTS entry
        """

        return self.restarts

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
    
    def get_age_in_minutes(self) -> int:
        """
        Converts the age of the pod into minutes.
        
        Returns:
             int: The age of the pod in minutes.
        """
        pod_age = self.get_age()
        total_minutes = 0

        if "m" in pod_age:
            minutes = int(pod_age.split("m")[0])
            total_minutes += minutes
        if "h" in pod_age:
            hours = int(pod_age.split("h")[0])
            total_minutes += hours * 60
        if "d" in pod_age:
            days = int(pod_age.split("d")[0])
            total_minutes += days * 1440
        if "s" in pod_age:
            pass

        return total_minutes

    def set_ip(self, ip: str) -> None:
        """
        Setter for IP
        Args:
            ip:

        Returns: None

        """
        self.ip = ip

    def get_ip(self) -> str:
        """
        Getter for IP entry
        """

        return self.ip

    def set_node(self, node: str) -> None:
        """
        Setter for NODE
        Args:
            node:

        Returns: None

        """
        self.node = node

    def get_node(self) -> str:
        """
        Getter for NODE entry
        """

        return self.node

    def set_nominated_node(self, nominated_node: str) -> None:
        """
        Setter for NOMINATED NODE
        Args:
            nominated_node:

        Returns: None

        """
        self.nominated_node = nominated_node

    def get_nominated_node(self) -> str:
        """
        Getter for NOMINATED NODE entry
        """

        return self.nominated_node

    def set_readiness_gates(self, readiness_gates: str) -> None:
        """
        Setter for READINESS GATES
        Args:
            readiness_gates:

        Returns: None

        """
        self.readiness_gates = readiness_gates

    def get_readiness_gates(self) -> str:
        """
        Getter for READINESS GATES entry
        """

        return self.readiness_gates
