class KubectlNodeTaintObject:
    """
    Class to hold attributes of a node taint.
    """

    def __init__(self):
        """
        Constructor
        """
        self.node: str = None
        self.key: str = None
        self.value: str = None
        self.effect: str = None

    def set_node(self, node: str):
        """
        Setter for the node name

        Args:
            node(str): Name of the node
        """
        self.node = node

    def get_node(self) -> str:
        """
        Getter for the node name

        Returns:
            str: Name of the node
        """
        return self.node

    def set_key(self, key: str):
        """
        Setter for the taint key

        Args:
            key(str): Taint key
        """
        self.key = key

    def get_key(self) -> str:
        """
        Getter for the taint key

        Returns:
            str: Taint key
        """
        return self.key

    def set_value(self, value: str):
        """
        Setter for the taint value

        Args:
            value(str): Taint value
        """
        self.value = value

    def get_value(self) -> str:
        """
        Getter for the taint value

        Returns:
            str: Taint value
        """
        return self.value

    def set_effect(self, effect: str):
        """
        Setter for the taint effect

        Args:
            effect(str): Taint effect
        """
        self.effect = effect

    def get_effect(self) -> str:
        """
        Getter for the taint effect

        Returns:
            str: Taint effect
        """
        return self.effect
