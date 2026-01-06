import copy
from typing import List, Optional

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.endpoint.objects.openstack_endpoint_list_object import OpenStackEndpointListObject
from keywords.cloud_platform.openstack.endpoint.objects.openstack_endpoint_list_object_filter import OpenStackEndpointListObjectFilter
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackEndpointListOutput:
    """
    Class for open stack endpoint output
    """

    def __init__(self, openstack_endpoint_list_output):
        self.openstack_endpoint_list_objects: [OpenStackEndpointListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_endpoint_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            endpoint_object = OpenStackEndpointListObject()
            endpoint_object.set_id(value["ID"])
            endpoint_object.set_region(value["Region"])
            endpoint_object.set_service_name(value["Service Name"])
            endpoint_object.set_service_type(value["Service Type"])
            endpoint_object.set_enabled(value["Enabled"])
            endpoint_object.set_interface(value["Interface"])
            endpoint_object.set_url(value["URL"])

            self.openstack_endpoint_list_objects.append(endpoint_object)

    def get_endpoints(self) -> [OpenStackEndpointListObject]:
        """Getter for endpoints"""
        return self.get_endpoints_list_objects_filtered(None)

    def get_endpoints_list_objects_filtered(self, filter_object: Optional[OpenStackEndpointListObjectFilter]) -> Optional[List[OpenStackEndpointListObjectFilter]]:
        """Gets the list of endpoints filtered by the filter object.

        Args:
            filter_object (Optional[OpenStackEndpointListObjectFilter]): OpenStackEndpointListObjectFilter object

        Returns:
            Optional[List[OpenStackEndpointListObjectFilter]]: List of OpenStackEndpointListObject objects

        """
        if filter_object is None:
            return self.openstack_endpoint_list_objects

        os_ep_list_objects_copy = copy.deepcopy(self.openstack_endpoint_list_objects)

        # Filters the copied list of OpenStackEndpointListObjectFilter by Region.
        if filter_object.get_region() is not None:
            os_ep_list_objects_copy = [ep for ep in os_ep_list_objects_copy if ep.get_region() == filter_object.get_region()]

        # Filters the copied list of OpenStackEndpointListObjectFilter by Service Name.
        if filter_object.get_service_name() is not None:
            os_ep_list_objects_copy = [ep for ep in os_ep_list_objects_copy if ep.get_service_name() == filter_object.get_service_name()]

        # Filters the copied list of OpenStackEndpointListObjectFilter by Service Type.
        if filter_object.get_service_type() is not None:
            os_ep_list_objects_copy = [ep for ep in os_ep_list_objects_copy if ep.get_service_type() == filter_object.get_service_type()]

        # Filters the copied list of OpenStackEndpointListObjectFilter by Interface.
        if filter_object.get_interface() is not None:
            os_ep_list_objects_copy = [ep for ep in os_ep_list_objects_copy if ep.get_interface() == filter_object.get_interface()]

        return os_ep_list_objects_copy

    def is_endpoint(self, service_name: str) -> bool:
        """This function will return true if the 'service_name' endpoint exists in the list.

        Args:
            service_name (str): Name of the service that we are looking for.

        Returns:
            bool: True if the endpoint exists, False otherwise.

        """
        for endpoint in self.openstack_endpoint_list_objects:
            if endpoint.get_service_name() == service_name:
                return True
        return False

    def get_endpoint(self, service_name: str, interface: str) -> OpenStackEndpointListObject:
        """Gets the endpoint with the given service and interface

        Args:
            service_name (str): service name
            interface (str): interface

        Returns:
            OpenStackEndpointListObject: The endpoint object with the given service name and interface.

        """
        endpoints = list(filter(lambda endpoint: endpoint.get_service_name() == service_name and endpoint.get_interface() == interface, self.openstack_endpoint_list_objects))

        if len(endpoints) < 1:
            raise KeywordException(f"No endpoint was found with service name {service_name} and interface {interface}")

        return endpoints[0]

    def get_horizon_url(self) -> str:
        """Gets the Horizon Endpoint URL for this lab.

        Returns:
            str: Horizon URL for this lab.

        """
        # Remove port from orignal url and then add 8443 for https or 8080 for http
        url = self.get_endpoint("keystone", "public").get_url().rsplit(":", 1)[0]
        if "https" in url:
            url += ":8443/"
        else:
            url += ":8080/"

        return url
