class OpenStackEndpointListObject:
    """
    Class to hold attibutes of an Open Stack Endpoint list object
    """

    def __init__(self):
        self.id = None
        self.region = None
        self.service_name = None
        self.service_type = None
        self.enabled = False
        self.interface = None
        self.url = None

    def set_id(self, id: str):
        """
        Setter for id
        Args:
            id (): the id

        Returns:

        """
        self.id = id

    def get_id(self) -> str:
        """
        Getter for id
        Returns: the id

        """
        return self.id

    def set_region(self, region: str):
        """
        Setter for region
        Args:
            region (): the region

        Returns:

        """
        self.region = region

    def get_region(self) -> str:
        """
        Getter for region
        Returns:

        """
        return self.region

    def set_service_name(self, service_name: str):
        """
        Setter for service name
        Args:
            service_name (): the service name

        Returns:

        """
        self.service_name = service_name

    def get_service_name(self) -> str:
        """
        Getter for service name
        Returns:

        """
        return self.service_name

    def set_service_type(self, service_type: str):
        """
        Setter for service type
        Args:
            service_type (): the service type

        Returns:

        """
        self.service_type = service_type

    def set_enabled(self, enabled: bool):
        """
        Setter for enabled
        Args:
            enabled (): True or False

        Returns:

        """
        self.enabled = enabled

    def get_enabled(self) -> bool:
        """
        Getter for enabled
        Returns:

        """
        return self.enabled

    def set_interface(self, interface: str):
        """
        Setter for interface
        Args:
            interface (): the interface

        Returns:

        """
        self.interface = interface

    def get_interface(self) -> str:
        """
        Getter for interface
        Returns:

        """
        return self.interface

    def set_url(self, url: str):
        """
        Setter for url
        Args:
            url (): the url

        Returns:

        """
        self.url = url

    def get_url(self) -> str:
        """
        Getter for url
        Returns:

        """
        return self.url
