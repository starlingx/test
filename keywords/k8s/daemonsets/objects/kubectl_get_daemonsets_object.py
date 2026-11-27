class KubectlDaemonsetsObject:
    """
    Class for Kubectl Daemonset objects
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): the name of the daemonset
        """
        self.name = name
        self.desired: int = -1
        self.current: int = -1
        self.ready: int = -1
        self.up_to_date: int = -1
        self.available: int = -1
        self.node_selector: str = None
        self.age: str = None

    def get_name(self) -> str:
        """
        Getter for name

        Returns:
            str: the name
        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for name

        Args:
            name (str): the name
        """
        self.name = name

    def get_desired(self) -> int:
        """
        Getter for desired

        Returns:
            int: the number of desired pods
        """
        return self.desired

    def set_desired(self, desired: int):
        """
        Setter for desired

        Args:
            desired (int): the number of desired pods
        """
        self.desired = desired

    def get_current(self) -> int:
        """
        Getter for current

        Returns:
            int: the number of current pods
        """
        return self.current

    def set_current(self, current: int):
        """
        Setter for current

        Args:
            current (int): the number of current pods
        """
        self.current = current

    def get_ready(self) -> int:
        """
        Getter for ready

        Returns:
            int: the number of ready pods
        """
        return self.ready

    def set_ready(self, ready: int):
        """
        Setter for ready

        Args:
            ready (int): the number of ready pods
        """
        self.ready = ready

    def get_up_to_date(self) -> int:
        """
        Getter for up_to_date

        Returns:
            int: the number of up-to-date pods
        """
        return self.up_to_date

    def set_up_to_date(self, up_to_date: int):
        """
        Setter for up_to_date

        Args:
            up_to_date (int): the number of up-to-date pods
        """
        self.up_to_date = up_to_date

    def get_available(self) -> int:
        """
        Getter for available

        Returns:
            int: the number of available pods
        """
        return self.available

    def set_available(self, available: int):
        """
        Setter for available

        Args:
            available (int): the number of available pods
        """
        self.available = available

    def is_rolled_out(self) -> bool:
        """
        Checks if every desired pod of the daemonset is updated, ready and available.

        The check uses the counters of 'kubectl get daemonsets', so it also works for
        a daemonset whose pod template has an affinity.

        A daemonset with no desired pods, or whose counters were never read, is
        not rolled out, since there is no pod to confirm the rollout.

        Returns:
            bool: True if there is at least one desired pod and updated, ready and available all equal desired.
        """
        if self.desired <= 0:
            return False
        return self.up_to_date == self.desired and self.ready == self.desired and self.available == self.desired

    def get_node_selector(self) -> str:
        """
        Getter for node selector

        Returns:
            str: the node selector
        """
        return self.node_selector

    def set_node_selector(self, node_selector: str):
        """
        Setter for node selector

        Args:
            node_selector (str): the node selector
        """
        self.node_selector = node_selector

    def get_age(self) -> str:
        """
        Getter for age

        Returns:
            str: the age
        """
        return self.age

    def set_age(self, age: str):
        """
        Setter for age

        Args:
            age (str): the age
        """
        self.age = age
