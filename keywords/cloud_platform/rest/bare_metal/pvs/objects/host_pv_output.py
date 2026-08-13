"""Output class for host PV REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.bare_metal.pvs.objects.host_pv_object import HostPvObject


class HostPvOutput:
    """Parses /ihosts/{id}/ipvs REST API response into HostPvObject list."""

    def __init__(self, response: RestResponse):
        """Initialize HostPvOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.pv_objects = []
        pvs = response.get_json_content().get("ipvs", [])
        for pv in pvs:
            obj = HostPvObject()
            if pv.get("uuid"):
                obj.set_uuid(pv["uuid"])
            if pv.get("pv_state"):
                obj.set_pv_state(pv["pv_state"])
            if pv.get("pv_type"):
                obj.set_pv_type(pv["pv_type"])
            self.pv_objects.append(obj)

    def get_pv_objects(self) -> list[HostPvObject]:
        """Get list of HostPvObject.

        Returns:
            list[HostPvObject]: List of PV objects.
        """
        return self.pv_objects
