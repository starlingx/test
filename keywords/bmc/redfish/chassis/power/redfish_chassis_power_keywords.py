from framework.redfish.client.redfish_client import RedFishClient
from framework.redfish.operations.get_system_info import GetSystemInfo, SystemInfo
from framework.redfish.objects.computer_system_reset import ComputerSystemReset

class RedFishChassisPowerKeywords(object):

    def __init__(self, host, username, password):
        self.redfish_client = RedFishClient(host, username, password)
        self.get_system_info = GetSystemInfo(host, username, password)
        self.system_id = self.get_system_info.get_system_id()
        self.system_info: SystemInfo = self.get_system_info.get_system_info()
        self.computer_system_reset: ComputerSystemReset = \
            self.system_info.get_computer_system_reset()
        self.allowable_values = \
            self.computer_system_reset.get_reset_type_allowable_values()

    def _reset_system(self, reset_type: str) -> bool:
        if reset_type not in self.allowable_values:
            raise ValueError(f"Invalid reset type: {reset_type}. Allowed values: {self.allowable_values}")
        target = self.computer_system_reset.get_target()
        response = self.redfish_client.post(target, body={"ResetType": reset_type})
        return 200 <= response.status < 300

    def power_on(self):
        """Power on the server using redfish API.

        Returns:
        None.

        """
        reset_types = {
            "On",
            "ForceOn",
        }.intersection(self.allowable_values)
        success = self._reset_system(reset_types.pop())
        if not success:
            raise RuntimeError("Failed to power on the server.")

    def power_off(self):
        """Power off the server using redfish API.

        Returns:
          None.

        """
        reset_types = {
            "GracefulShutdown",
            "ForceOff",
            "PushPowerButton"
        }.intersection(self.allowable_values)
        success = self._reset_system(reset_types.pop())
        if not success:
            raise RuntimeError("Failed to power off the server.")

    def power_cycle(self):
        """Power cycle the server using redfish API.
        Returns:
          None.

        """
        reset_types = {
            "GracefulRestart",
            "ForceRestart",
            "PowerCycle"
        }.intersection(self.allowable_values)
        success = self._reset_system(reset_types.pop())
        if not success:
            raise RuntimeError(f"Failed to power cycle the server.")
