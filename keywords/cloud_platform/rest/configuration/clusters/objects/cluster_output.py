"""Output class for ClusterOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.clusters.objects.cluster_object import ClusterObject


class ClusterOutput:
    """Parses /clusters REST API response into ClusterObject list."""

    def __init__(self, response: RestResponse):
        """Initialize ClusterOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("clusters", [])
        for item in items:
            obj = ClusterObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("cluster_name"):
                obj.set_cluster_name(item["cluster_name"])
            if item.get("type"):
                obj.set_type(item["type"])
            self.objects.append(obj)

    def get_clusterobjects(self) -> list[ClusterObject]:
        """Get list of ClusterObject.

        Returns:
            list[ClusterObject]: List of ClusterObject instances.
        """
        return self.objects
