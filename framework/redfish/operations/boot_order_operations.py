from framework.redfish.client.redfish_client import RedFishClient
from framework.redfish.objects.boot_option import BootOption
from framework.redfish.operations.get_system_info import GetSystemInfo


class BootOrderOperations:
    """
    Class for Boot order operations
    """

    def __init__(self, bmc_ip: str, username: str, password):
        self.redfish_client = RedFishClient(bmc_ip, username, password)
        self.sys_info = GetSystemInfo(bmc_ip, username, password)
        self.system_id = self.sys_info.get_system_id()

    def get_boot_order(self) -> list[BootOption]:
        """
        Gets the list of boot options in order

        Returns:
            list[BootOption]: List of boot options.]
        """
        boot_option_list = []
        boot_options = self.redfish_client.get(f"{self.system_id}/BootOptions").dict["Members"]

        for boot_option in boot_options:
            id = boot_option.get("@odata.id")
            text = self.redfish_client.get(id)
            boot_option_list.append(self.create_boot_option(text.dict))

        return boot_option_list

    def create_boot_option(self, boot_option_dict: {}) -> BootOption:
        """
        Creates a boot option from the given dict.

        Args:
            boot_option_dict ({}): the dict to create the boot option from

        Returns:
            BootOption: BootOption object.
        """
        boot_option_id = boot_option_dict.get("Id", "")
        name = boot_option_dict.get("Name", "")
        display_name = boot_option_dict.get("DisplayName", "")
        boot_option_enabled = boot_option_dict.get("BootOptionEnabled", False)
        description = boot_option_dict.get("Description", "")

        return BootOption(boot_option_id, name, display_name, boot_option_enabled, description)
