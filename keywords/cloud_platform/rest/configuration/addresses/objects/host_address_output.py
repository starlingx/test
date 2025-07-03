from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.addresses.objects.host_address_object import HostAddressObject
from keywords.python.type_converter import TypeConverter


class HostAddressOutput:
    """Parses host addresses from REST API responses."""

    def __init__(self, host_address_output: RestResponse | list | dict) -> None:
        """Initialize HostAddressOutput with parsed address data.

        Args:
            host_address_output (RestResponse | list | dict): REST response from /v1/ihosts/{host_id}/addresses endpoint.
        """
        if isinstance(host_address_output, RestResponse):
            json_object = host_address_output.get_json_content()
            if "addresses" in json_object:
                addresses = json_object["addresses"]
            else:
                addresses = [json_object] if json_object else []
        else:
            addresses = host_address_output if isinstance(host_address_output, list) else [host_address_output]

        self.host_address_objects: list[HostAddressObject] = []

        for address in addresses:
            host_address_object = HostAddressObject()

            if "uuid" in address:
                host_address_object.set_uuid(address["uuid"])

            if "interface_uuid" in address:
                host_address_object.set_interface_uuid(address["interface_uuid"])

            if "ifname" in address:
                host_address_object.set_ifname(address["ifname"])

            if "address" in address:
                host_address_object.set_address(address["address"])

            if "prefix" in address:
                host_address_object.set_prefix(int(address["prefix"]))

            if "enable_dad" in address:
                value = address["enable_dad"] if isinstance(address["enable_dad"], bool) else TypeConverter.str_to_bool(address["enable_dad"])
                host_address_object.set_enable_dad(value)

            if "forihostid" in address:
                host_address_object.set_forihostid(int(address["forihostid"]))

            if "pool_uuid" in address:
                host_address_object.set_pool_uuid(address["pool_uuid"])

            self.host_address_objects.append(host_address_object)

    def get_host_address_objects(self) -> list[HostAddressObject]:
        """Get all host address objects.

        Returns:
            list[HostAddressObject]: List of HostAddressObject instances.
        """
        return self.host_address_objects

    def get_address_by_ifname(self, ifname: str) -> str | None:
        """Get IP address by interface name.

        Args:
            ifname (str): Interface name to search for.

        Returns:
            str | None: IP address string or None if not found.
        """
        for addr in self.host_address_objects:
            if addr.get_ifname() == ifname:
                return addr.get_address()
        return None
