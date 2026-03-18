class KubernetesNodeAllocatedResourcesObject:
    """
    Class to hold attributes of Allocated resources
    """

    def __init__(self):
        """
        Constructor
        """

        self.resource: str = None
        self.requests: str = None
        self.limits: str = None

    def set_resource(self, resource: str):
        """
        Setter for the resource
        Args:
            resource:
        """
        self.resource = resource

    def get_resource(self) -> str:
        """
        Getter for the resource
        Returns: (str)

        """
        return self.resource

    def set_requests(self, requests: str):
        """
        Setter for the requests
        Args:
            requests:
        """
        self.requests = requests

    def get_requests(self) -> str:
        """
        Getter for the requests
        Returns: (str)

        """
        return self.requests

    def get_requests_as_int(self) -> int:
        """
        Parse the requests string and return the integer value.

        The requests field is typically in format like "2 (9%)" or "0 (0%)".
        This method extracts the first integer value.

        Returns:
            int: The integer value from the requests string, or 0 if requests is None or empty.
        """
        if not self.requests:
            return 0
        return int(self.requests.split()[0])

    def set_limits(self, limits: str):
        """
        Setter for the limits
        Args:
            limits:
        """
        self.limits = limits

    def get_limits(self) -> str:
        """
        Getter for the limits
        Returns: (str)

        """
        return self.limits
