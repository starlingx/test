from typing import Optional


class OpenStackEndpointListObjectFilter:
    """
    Class to filter OpenStack Endpoint List objects.
    """

    def __init__(self):
        self.region: Optional[str] = None
        self.service_name: Optional[str] = None
        self.service_type: Optional[str] = None
        self.interface: Optional[str] = None

    def get_region(self) -> Optional[str]:
        """
        Getter for the filter by Region.
        """
        return self.region

    def set_region(self, region: str):
        """
        Setter for the filter by Region.
        """
        self.region = region
        return self

    def get_service_name(self) -> Optional[str]:
        """
        Getter for the filter by Service Name.
        """
        return self.service_name

    def set_service_name(self, service_name: str):
        """
        Setter for the filter by Service Name.
        """
        self.service_name = service_name
        return self

    def get_service_type(self) -> Optional[str]:
        """
        Getter for the filter by Service Type.
        """
        return self.service_type

    def set_service_type(self, service_type: str):
        """
        Setter for the filter by Service Type.
        """
        self.service_type = service_type
        return self

    def get_interface(self) -> Optional[str]:
        """
        Getter for the filter by Interface.
        """
        return self.interface

    def set_interface(self, interface: str):
        """
        Setter for the filter by Interface.
        """
        self.interface = interface
        return self

    def __str__(self) -> str:
        """
        String representation of the filter object.
        """
        return f"OpenstackEndpointListObjectFilter(region={self.region}, " f"service_name={self.service_name}, service_type={self.service_type}, " f"interface={self.interface})"

    def __repr__(self) -> str:
        """
        String representation of the filter object for debugging.
        """
        return self.__str__()
