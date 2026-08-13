"""Output class for host LVG REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.bare_metal.lvgs.objects.host_lvg_object import HostLvgObject


class HostLvgOutput:
    """Parses /ihosts/{id}/ilvgs REST API response into HostLvgObject list."""

    def __init__(self, response: RestResponse):
        """Initialize HostLvgOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.lvg_objects = []
        lvgs = response.get_json_content().get("ilvgs", [])
        for lvg in lvgs:
            obj = HostLvgObject()
            if lvg.get("uuid"):
                obj.set_uuid(lvg["uuid"])
            if lvg.get("lvm_vg_name"):
                obj.set_lvm_vg_name(lvg["lvm_vg_name"])
            if lvg.get("vg_state"):
                obj.set_vg_state(lvg["vg_state"])
            self.lvg_objects.append(obj)

    def get_lvg_objects(self) -> list[HostLvgObject]:
        """Get list of HostLvgObject.

        Returns:
            list[HostLvgObject]: List of LVG objects.
        """
        return self.lvg_objects
