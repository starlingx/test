class KubectlCertObject:
    """
    Class to hold attributes of a 'kubectl get certificate' certificate entry.
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): Name of the certs.
        """
        self.name = name
        self.ready = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
             str: The name of the certs.
        """
        return self.name

    def set_secret(self, secret: str) -> None:
        """
        Setter for SECRET

        Args:
            secret (str): The secret associated with the certs.

        Returns: None
        """
        self.secret = secret

    def get_secret(self) -> str:
        """
        Getter for SECRET entry
        """
        return self.secret

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY

        Args:
            ready (str): The ready associated with the certs.

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
        Setter for AGE.

        Args:
            age (str): The age associated with the certs.

        Returns: None
        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry.

        Returns:
             str: The age of the certs.
        """
        return self.age
