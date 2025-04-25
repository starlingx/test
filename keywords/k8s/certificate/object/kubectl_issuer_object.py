class KubectlIssuerObject:
    """
    Class to hold attributes of a 'kubectl get issuer' pod entry.
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): Name of the pod.
        """
        self.name = name
        self.ready = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry

        """
        return self.name

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY

        Args:
            ready (str): The ready associated with the issuer.

        Returns: None

        """
        self.ready = ready

    def get_ready(self) -> str:
        """
        Getter for READY entry
        """
        return self.ready

    def set_age(self, age: str) -> None:
        """
        Setter for AGE

        Args:
            age (str): The age associated with the issuer.

        Returns: None

        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """
        return self.age
