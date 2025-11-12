class KubectlPodObject:
    """
    Class to hold attributes of a 'kubectl get pods' pod entry.
    """

    def __init__(self, name: str):
        """
        Constructor.

        Args:
            name (str): Name of the pod.
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
        self.labels = {}

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
            str: The name of the pod.
        """
        return self.name

    def set_namespace(self, namespace: str) -> None:
        """
        Setter for NAMESPACE.

        Args:
            namespace (str): Namespace value.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """
        Getter for NAMESPACE entry.

        Returns:
            str: Namespace value.
        """
        return self.namespace

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY.

        Args:
            ready (str): Ready value.
        """
        self.ready = ready

    def get_ready(self) -> str:
        """
        Getter for READY entry.

        Returns:
            str: Ready value.
        """
        return self.ready

    def set_status(self, status: str) -> None:
        """
        Setter for STATUS.

        Args:
            status (str): Status value.
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for STATUS entry.

        Returns:
            str: Status value.
        """
        return self.status

    def set_restarts(self, restarts: str) -> None:
        """
        Setter for RESTARTS.

        Args:
            restarts (str): Restarts value.
        """
        self.restarts = restarts

    def get_restarts(self) -> str:
        """
        Getter for RESTARTS entry.

        Returns:
            str: Restarts value.
        """
        return self.restarts

    def set_age(self, age: str) -> None:
        """
        Setter for AGE.

        Args:
            age (str): Age value.
        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry.

        Returns:
            str: Age value.
        """
        return self.age

    def get_age_in_minutes(self) -> int:
        """
        Convert the age of the pod into minutes.

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
        Setter for IP.

        Args:
            ip (str): IP address value.
        """
        self.ip = ip

    def get_ip(self) -> str:
        """
        Getter for IP entry.

        Returns:
            str: IP address value.
        """
        return self.ip

    def set_node(self, node: str) -> None:
        """
        Setter for NODE.

        Args:
            node (str): Node value.
        """
        self.node = node

    def get_node(self) -> str:
        """
        Getter for NODE entry.

        Returns:
            str: Node value.
        """
        return self.node

    def set_nominated_node(self, nominated_node: str) -> None:
        """
        Setter for NOMINATED NODE.

        Args:
            nominated_node (str): Nominated node value.
        """
        self.nominated_node = nominated_node

    def get_nominated_node(self) -> str:
        """
        Getter for NOMINATED NODE entry.

        Returns:
            str: Nominated node value.
        """
        return self.nominated_node

    def set_readiness_gates(self, readiness_gates: str) -> None:
        """
        Setter for READINESS GATES.

        Args:
            readiness_gates (str): Readiness gates value.
        """
        self.readiness_gates = readiness_gates

    def get_readiness_gates(self) -> str:
        """
        Getter for READINESS GATES entry.

        Returns:
            str: Readiness gates value.
        """
        return self.readiness_gates

    def set_labels(self, labels: dict) -> None:
        """
        Setter for labels.

        Args:
            labels (dict): Labels dictionary.
        """
        self.labels = labels

    def get_labels(self) -> dict:
        """
        Getter for labels.

        Returns:
            dict: Labels dictionary.
        """
        return self.labels

    def get_label(self, key: str) -> str:
        """
        Get specific label value.

        Args:
            key (str): Label key.

        Returns:
            str: Label value or empty string if not found.
        """
        return self.labels.get(key, "")

    def get_app_version(self) -> str:
        """
        Get app.kubernetes.io/version label.

        Returns:
            str: App version or empty string if not found.
        """
        return self.get_label("app.kubernetes.io/version")

    def get_helm_chart(self) -> str:
        """
        Get helm.sh/chart label.

        Returns:
            str: Helm chart or empty string if not found.
        """
        return self.get_label("helm.sh/chart")

    def __str__(self) -> str:
        """
        String representation of the pod object.

        Returns:
            str: Pod name and status.
        """
        return f"Pod(name={self.name}, status={self.status})"

    def __repr__(self) -> str:
        """
        Representation of the pod object.

        Returns:
            str: Pod name and status.
        """
        return self.__str__()
