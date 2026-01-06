class KubectlHelmReleaseObject:
    """
    Class to hold attributes of a 'kubectl get hr -A' helm release entry.
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): Name of the helm release.
        """
        self.name: str = name
        self.age: str = None
        self.ready: str = None
        self.status: str = None

    def get_name(self) -> str:
        """
        Getter for NAME entry

        Returns:
            str: The name of the helm release.

        """
        return self.name

    def set_age(self, age: str) -> None:
        """
        Setter for AGE

        Args:
            age (str): Age of the helm release

        Returns: None

        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry

        Returns:
            str: The age of the helm release

        """
        return self.age

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY

        Args:
            ready(str): Ready of the helm release

        Returns: None

        """
        self.ready = ready

    def get_ready(self) -> str:
        """
        Getter for READY entry

        Returns:
             str: The ready of the helm release

        """
        return self.ready

    def set_status(self, status: str) -> None:
        """
        Setter for STATUS

        Args:
            status(str): Status of the helm release

        Returns: None

        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for STATUS entry

        Returns:
            str: The status of the helm release

        """
        return self.status
