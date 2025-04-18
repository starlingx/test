import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_manage_output import DcManagerSubcloudManageOutput


class DcManagerSubcloudManagerKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'dcmanager subcloud <manage/unmanage> <subcloud name>' and command."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection to the central subcloud.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_manage(self, subcloud_name: str, timeout: int) -> DcManagerSubcloudManageOutput:
        """Dcmanager subcloud manage

        Gets the output of 'dcmanager subcloud manage <subcloud_name>' as an instance of DcManagerSubcloudManageOutput
        if the subcloud is successfully set to 'managed' (its 'management' attribute updated to 'managed') within the
        specified 'timeout' period. Otherwise, this method returns None.

        Args:
            subcloud_name (str): The name of the subcloud that must be set to the 'managed' state.
            timeout (int): The maximum time, in seconds, to wait for the subcloud to enter the 'managed' state.

        Returns:
            DcManagerSubcloudManageOutput: An instance representing the output of the command
            'dcmanager subcloud manage <subcloud_name>' if successful, or None otherwise.

        """
        return self._get_dcmanager_subcloud_operation(subcloud_name, timeout, "manage")

    def get_dcmanager_subcloud_unmanage(self, subcloud_name: str, timeout: int) -> DcManagerSubcloudManageOutput:
        """Dcmanager subcloud unmanage

        Gets the output of 'dcmanager subcloud unmanage <subcloud_name>' as an instance of DcManagerSubcloudManageOutput
        if the subcloud is successfully set to 'unmanaged' (its 'management' attribute updated to 'unmanaged') within
        the specified 'timeout' period. Otherwise, this method returns None.

        Args:
            subcloud_name (str): The name of the subcloud that must be set to the 'unmanaged' state.
            timeout (int): The maximum time, in seconds, to wait for the subcloud to enter the 'unmanaged' state.

        Returns:
            DcManagerSubcloudManageOutput: An instance representing the output of the command
            'dcmanager subcloud unmanage <subcloud_name>' if successful, or None otherwise.

        """
        return self._get_dcmanager_subcloud_operation(subcloud_name, timeout, "unmanage")

    def _get_dcmanager_subcloud_operation(self, subcloud_name: str, end_time: int, operation: str) -> DcManagerSubcloudManageOutput:
        """Dcmanager subcloud manage/unmanage

        Gets the output of 'dcmanager subcloud <operation> <subcloud_name>' as an instance of DcManagerSubcloudManageOutput
        if the subcloud is successfully set to 'managed' or 'unmanaged' (its 'management' attribute updated to 'managed'
        or to 'unmanaged', depending on 'operation') within the specified 'timeout' period. Otherwise, this method
        returns None.

        Args:
            subcloud_name (str): The name of the subcloud that must be set to the 'managed' state.
            end_time (int): The maximum time, in seconds, to wait for the subcloud to enter the 'managed' state.
            operation (str): The operation to be performed on the subcloud ('manage' or 'unmanage').

        Returns:
            DcManagerSubcloudManageOutput: An instance representing the output of the command
            'dcmanager subcloud <operation> <subcloud_name>' if successful, or None otherwise.

        Raises:
            TimeoutError: If the subcloud does not enter the 'managed' or 'unmanaged' state within the specified timeout.

        """
        target_state = "managed"
        if operation == "unmanage":
            target_state = "unmanaged"

        # This section is responsible for changing the state of the subcloud to 'managed' or 'unmanaged'.
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud {operation} {subcloud_name}"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_manage_output = DcManagerSubcloudManageOutput(output)

        # This section is responsible for obtaining the object used to verify the state change.
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter()
        dcmanager_subcloud_list_object_filter.set_name(subcloud_name)
        dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(self.ssh_connection)

        # This section is responsible for verifying whether the state has changed within a defined timeout.
        end_time = time.time() + end_time
        while time.time() < end_time:
            dcmanager_subcloud_list_object = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)[0]
            if dcmanager_subcloud_list_object.get_management() == target_state:
                return dcmanager_subcloud_manage_output
            time.sleep(5)

        error_message = f"Failed to change the state of subcloud '{subcloud_name}' to '{target_state}'."
        get_logger().log_error(error_message)
        raise TimeoutError(error_message)

    def set_subcloud_poweroff(self, subcloud_name: str, timeout: int = 600) -> bool:
        """Does the power off of the subcloud

        Args:
            subcloud_name (str): The name of the subcloud to be powered off.
            timeout (int): The maximum time, in seconds, to wait for the subcloud to enter the 'offline' state.

        Returns:
            bool: True if the subcloud is successfully powered off and its state is 'offline', False otherwise.
        Raises: TimeoutError
        """
        # get SSH connection to subcloud
        # power off all the controllers in the subcloud
        IPMIToolChassisPowerKeywords(self.ssh_connection, None).power_off_subcloud(subcloud_name)
        # This section is responsible for verifying whether the state has changed within a defined timeout.
        target_state = "offline"
        end_time = time.time() + timeout
        while time.time() < end_time:
            dcm_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
            if subcloud.get_availability() == target_state:
                return True
            # If the subcloud is not 'offline', wait and check again
            time.sleep(5)
        error_message = f"Failed to change the state of subcloud '{subcloud_name}' to '{target_state}'."
        get_logger().log_error(error_message)
        raise TimeoutError(error_message)
