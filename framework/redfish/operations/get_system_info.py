from framework.redfish.client.redfish_client import RedFishClient
from framework.redfish.objects.system_collections import SystemCollections
from framework.redfish.objects.system_info import SystemInfo
from framework.redfish.operations.get_systems_operations import GetSystemsOperations


class GetSystemInfo:
    """
    Class for System Info
    """

    def __init__(self, bmc_ip: str, username: str, password: str):
        self.bmc_ip = bmc_ip
        self.username = username
        self.password = password
        self.system_id = None

    def get_system_id(self) -> str:
        """
        Getter for system_id

        Returns:
            str: system_id
        """
        if not self.system_id:
            system_collection: SystemCollections = GetSystemsOperations(self.bmc_ip, self.username, self.password).get_systems()
            members: list[str] = system_collection.get_members()

            # we seem to only ever use the first one so just check it's not empty and return first
            if not members:
                raise Exception("No members found")
            self.system_id: str = members[0]
        return self.system_id

    def get_system_info(self) -> SystemInfo:
        """Get system information.

        Returns:
            SystemInfo: System information object.
        """
        redfish_client = RedFishClient(self.bmc_ip, self.username, self.password)
        resp = redfish_client.get(self.system_id)
        return SystemInfo(resp.dict)
