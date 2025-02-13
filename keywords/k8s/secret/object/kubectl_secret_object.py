class KubectlSecretObject:
    """
    Class to hold attributes of a 'kubectl get secrets' command entry
    """

    def __init__(self, name: str):
        """
        Constructor
        Args:
            name (str): secret name
        """
        self.name = name
        self.type = None
        self.data = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry
        """
        return self.name

    def set_name(self, name: str) -> None:
        """
        Setter for NAME entry

        Args:
            name (str): secret name
        """
        self.name = name

    def get_type(self) -> str:
        """
        Getter for TYPE entry
        """
        return self.type

    def set_type(self, type: str) -> None:
        """
        Setter for TYPE entry

        Args:
            type (str): secret type
        """
        self.type = type

    def get_data(self) -> int:
        """
        Getter for DATA entry
        """
        return self.data

    def set_data(self, data: int) -> None:
        """
        Setter for DATA entry

        Args:
            data (int): secret data
        """
        self.data = data

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """
        return self.age

    def set_age(self, age: str) -> None:
        """
        Setter for AGE entry
        Args:
            age (str): secret age
        """
        self.age = age
