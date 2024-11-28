class KubectlNamespaceObject:
    """
    Class to hold attributes of a 'kubectl get ns' namespace entry.
    """

    def __init__(self, name: str):
        """
        Constructor
        Args:
            name: Name of the namespace.
        """

        self.name = name
        self.status = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry
        Returns: The name of the pod.

        """
        return self.name

    def set_status(self, status: str) -> None:
        """
        Setter for STATUS
        Args:
            status: str

        Returns: None

        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for STATUS entry
        """

        return self.status

    def set_age(self, age: str) -> None:
        """
        Setter for AGE
        Args:
            age: str

        Returns: None

        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """

        return self.age
