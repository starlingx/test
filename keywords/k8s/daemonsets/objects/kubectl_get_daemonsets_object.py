class KubectlDaemonsetsObject:
    """
    Class for Kubectl Daemonset objects
    """

    def __init__(self, name: str):
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
        Returns: the name

        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for name
        Args:
            name (): the name

        Returns:

        """
        self.name = name

    def get_desired(self) -> int:
        """
        Getter for desired
        Returns:

        """
        return self.desired

    def set_desired(self, desired: int):
        """
        Setter for desired
        Args:
            desired (): desired

        Returns:

        """
        self.desired = desired

    def get_current(self) -> int:
        """
        Getter for current
        Returns:

        """
        return self.current

    def set_current(self, current: int):
        """
        Setter for desired
        Args:
            current (): current

        Returns:

        """
        self.current = current

    def get_ready(self) -> int:
        """
        Getter for ready
        Returns:

        """
        return self.ready

    def set_ready(self, ready: int):
        """
        Setter for ready
        Args:
            ready (): ready

        Returns:

        """
        self.ready = ready

    def get_up_to_date(self) -> int:
        """
        Getter for up_to_date
        Returns:

        """
        return self.up_to_date

    def set_up_to_date(self, up_to_date: int):
        """
        Setter for up_to_date
        Args:
            up_to_date (): up_to_date

        Returns:

        """
        self.up_to_date = up_to_date

    def get_available(self) -> int:
        """
        Getter for available
        Returns:

        """
        return self.available

    def set_available(self, available: int):
        """
        Setter for available
        Args:
            available (): available

        Returns:

        """
        self.available = available

    def get_node_selector(self) -> str:
        """
        Getter for node selector
        Returns: node selector

        """
        return self.node_selector

    def set_node_selector(self, node_selector: str):
        """
        Setter for node selector
        Args:
            node_selector (): the node selector

        Returns:

        """
        self.node_selector = node_selector

    def get_age(self) -> str:
        """
        Getter for age
        Returns: age

        """
        return self.age

    def set_age(self, age: str):
        """
        Setter for age
        Args:
            age (): the age

        Returns:

        """
        self.age = age
