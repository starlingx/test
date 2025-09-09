from framework.redfish.client.redfish_client import RedFishClient
from framework.redfish.objects.system_collections import SystemCollections
from framework.validation.validation import validate_equals


class GetSystemsOperations:
    """
    Get Systems Operations Class
    """

    def __init__(self, bmc_ip: str, username: str, password):
        self.redfish_client = RedFishClient(bmc_ip, username, password)

    def get_systems(self) -> SystemCollections:
        """
        Gets systems

        Returns:
            SystemCollections: SystemCollections object.

        """
        resp = self.redfish_client.get("/redfish/v1/Systems")
        validate_equals(self.redfish_client.get_status_code(), 200, "Validate 200 status code")

        context = resp.dict.get("@odata.context", "")
        id = resp.dict.get("@odata.id", "")
        type = resp.dict.get("@odata.type", "")
        description = resp.dict.get("Description", "")
        members = resp.dict.get("Members", [])
        data_count = resp.dict.get("Members@odata.count", 0)
        name = resp.dict.get("Name", "")

        members_list = []
        for member in members:
            members_list.append(member["@odata.id"])

        system_collections = SystemCollections(context, id, type, description, members_list, data_count, name)
        return system_collections
