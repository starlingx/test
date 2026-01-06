class KubectlDeploymentObject:
    """
    Represents a Kubernetes deployment.
    """

    def __init__(self, name: str):
        self.name = name
        self.ready = None
        self.up_to_date = None
        self.available = None
        self.age = None

    def set_ready(self, ready: str):
        self.ready = ready
    
    def get_ready(self) -> str:
        """
        Getter for READY entry
        Returns: The readiness status of the deployment.
        """
        return self.ready

    def set_up_to_date(self, up_to_date: str):
        self.up_to_date = up_to_date

    def get_up_to_date(self) -> str:
        """
        Getter for UP-TO-DATE entry
        Returns: The up-to-date status of the deployment.
        """
        return self.up_to_date

    def set_available(self, available: str):
        self.available = available

    def get_available(self) -> str:
        """
        Getter for AVAILABLE entry
        Returns: The availability status of the deployment.
        """
        return self.available

    def set_age(self, age: str):
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry
        Returns: The age of the deployment.
        """
        return self.age

    def get_name(self) -> str:
        """
        Getter for NAME entry
        Returns: The name of the deployment."""
        return self.name

    def __repr__(self):
        return f"<KubectlDeploymentObject name={self.name} ready={self.ready} up_to_date={self.up_to_date} available={self.available} age={self.age}>"