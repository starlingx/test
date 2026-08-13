"""Output class for host route REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.bare_metal.routes.objects.host_route_object import HostRouteObject


class HostRouteOutput:
    """Parses /ihosts/{id}/routes REST API response into HostRouteObject list."""

    def __init__(self, response: RestResponse):
        """Initialize HostRouteOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.route_objects = []
        routes = response.get_json_content().get("routes", [])
        for route in routes:
            obj = HostRouteObject()
            if route.get("uuid"):
                obj.set_uuid(route["uuid"])
            if route.get("network"):
                obj.set_network(route["network"])
            if route.get("gateway"):
                obj.set_gateway(route["gateway"])
            self.route_objects.append(obj)

    def get_route_objects(self) -> list[HostRouteObject]:
        """Get list of HostRouteObject.

        Returns:
            list[HostRouteObject]: List of route objects.
        """
        return self.route_objects
