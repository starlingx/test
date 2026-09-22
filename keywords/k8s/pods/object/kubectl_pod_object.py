import re


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
        self.restart_count = None
        self.init_restart_count = None
        self.age = None
        self.ip = None
        self.node = None
        self.nominated_node = None
        self.readiness_gates = None
        self.labels = {}
        self.images = []
        self.owner_name = None
        self.owner_kind = None

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

    def is_ready(self) -> bool:
        """
        Check if pod is ready by comparing ready vs total containers.

        Returns:
            bool: True if all containers are ready (e.g., '2/2'), False otherwise.
        """
        if not self.ready:
            return False
        parts = self.ready.split("/")
        if len(parts) != 2:
            return False
        return parts[0] == parts[1]

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

    def set_restart_count(self, count: int) -> None:
        """
        Setter for the app-container restart count.

        Args:
            count (int): Restart count summed across the pod's app (regular)
                containers, i.e. status.containerStatuses[].restartCount.
                Excludes init containers (see set_init_restart_count).
        """
        self.restart_count = count

    def get_restart_count(self) -> int:
        """
        Getter for the app-container restart count.

        Summed from status.containerStatuses[].restartCount - the pod's app
        (regular) containers, i.e. the long-running workload. An app-container
        restart means the running workload crashed and was restarted (OOM,
        liveness-probe failure, panic) - steady-state instability. Init-container
        restarts are tracked separately via get_init_restart_count(); init
        containers run once at startup and cannot restart again while the pod
        lives, so their count is startup history, not steady-state stability.
        This is the lifetime count of the current pod object; recreating the pod
        resets it to 0.

        Note: this is a defensive backstop for callers iterating a
        KubectlGetPodsOutput directly. The deliberate interface is
        KubectlGetPodsKeywords.get_pod_restart_count(), which sources the value
        via JSON regardless of how any snapshot was built.

        Returns:
            int: App-container restart count.

        Raises:
            ValueError: If the count was not populated (pod parsed from table
                source). Build the snapshot from JSON, e.g. via
                KubectlGetPodsKeywords.get_pods_json().
        """
        if self.restart_count is None:
            raise ValueError(f"Restart count is not available for pod '{self.name}' parsed from table source; build the snapshot from JSON (e.g. get_pods_json()) or use KubectlGetPodsKeywords.get_pod_restart_count().")
        return self.restart_count

    def set_init_restart_count(self, count: int) -> None:
        """
        Setter for the init-container restart count.

        Args:
            count (int): Restart count summed across the pod's init containers,
                i.e. status.initContainerStatuses[].restartCount.
        """
        self.init_restart_count = count

    def get_init_restart_count(self) -> int:
        """
        Getter for the init-container restart count.

        Summed from status.initContainerStatuses[].restartCount. Init containers
        run once at pod startup (dependency waits, migrations, image-pull
        retries), then never again while the pod lives, so this reflects
        startup-time retries rather than steady-state stability.

        Returns:
            int: Init-container restart count.

        Raises:
            ValueError: If the count was not populated (pod parsed from table
                source). Build the snapshot from JSON, e.g. via
                KubectlGetPodsKeywords.get_pods_json().
        """
        if self.init_restart_count is None:
            raise ValueError(f"Init restart count is not available for pod '{self.name}' parsed from table source; build the snapshot from JSON (e.g. get_pods_json()).")
        return self.init_restart_count

    def get_total_restart_count(self, include_init: bool = False) -> int:
        """
        Get this pod's total restart count: app (regular) containers, optionally plus init.

        Combines the two per-container-type counts this object already holds. By
        default returns app-container restarts only (steady-state instability);
        set include_init=True to also add init-container restarts (startup
        history - image-pull retries, dependency waits). See get_restart_count()
        and get_init_restart_count() for the meaning of each and the
        pod-recreation caveat (the count resets to 0 when the pod object is
        replaced).

        Args:
            include_init (bool): Also add init-container restarts. Defaults to False.

        Returns:
            int: App-container restart count, plus init-container restarts when
                include_init is True.

        Raises:
            ValueError: If the counts were not populated (pod parsed from table
                source). Build the snapshot from JSON, e.g. via
                KubectlGetPodsKeywords.get_pods_json().
        """
        count = self.get_restart_count()
        if include_init:
            count += self.get_init_restart_count()
        return count

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

        days = re.search(r"(\d+)d", pod_age)
        hours = re.search(r"(\d+)h", pod_age)
        minutes = re.search(r"(\d+)m", pod_age)

        if days:
            total_minutes += int(days.group(1)) * 1440
        if hours:
            total_minutes += int(hours.group(1)) * 60
        if minutes:
            total_minutes += int(minutes.group(1))

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

    def set_owner_name(self, owner_name: str) -> None:
        """Setter for the controlling owner's name.

        Args:
            owner_name (str): Name of the controlling owner (for example the
                ReplicaSet or DaemonSet that manages this pod).
        """
        self.owner_name = owner_name

    def get_owner_name(self) -> str:
        """Getter for the controlling owner's name.

        Only populated from the JSON source (``metadata.ownerReferences``);
        the table source does not expose owner references.

        Returns:
            str: The owner name, or None if not populated.
        """
        return self.owner_name

    def set_owner_kind(self, owner_kind: str) -> None:
        """Setter for the controlling owner's kind.

        Args:
            owner_kind (str): Kind of the controlling owner (for example
                'ReplicaSet', 'DaemonSet', or 'StatefulSet').
        """
        self.owner_kind = owner_kind

    def get_owner_kind(self) -> str:
        """Getter for the controlling owner's kind.

        Only populated from the JSON source (``metadata.ownerReferences``);
        the table source does not expose owner references.

        Returns:
            str: The owner kind, or None if not populated.
        """
        return self.owner_kind

    def set_images(self, images: list[str]) -> None:
        """Setter for container images.

        Args:
            images (list[str]): List of container image strings.
        """
        self.images = images

    def get_images(self) -> list[str]:
        """Getter for container images.

        Returns:
            list[str]: List of container image strings.
        """
        return self.images

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
