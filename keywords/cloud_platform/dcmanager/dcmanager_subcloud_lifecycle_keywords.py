"""Keywords for subcloud lifecycle orchestration (delete)."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords


class DcManagerSubcloudLifecycleKeywords:
    """High-level subcloud lifecycle operations that orchestrate multiple keywords.

    Provides operations that span multiple lower-level keyword classes such as
    power off, unmanage, and delete.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
        """
        self.ssh_connection = ssh_connection

    def delete_subcloud(self, subcloud_name: str) -> None:
        """Power off, unmanage, and delete a subcloud.

        Powers off the subcloud, unmanages it if currently managed, then deletes it.

        Args:
            subcloud_name (str): Subcloud to delete.
        """
        dcm_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(self.ssh_connection)

        get_logger().log_info(f"Powering off subcloud '{subcloud_name}'")
        dcm_sc_manager_kw.set_subcloud_poweroff(subcloud_name)

        subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
        management_state = subcloud.get_management()
        if management_state == "managed":
            get_logger().log_info(f"Unmanaging subcloud '{subcloud_name}'")
            dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(subcloud_name, timeout=10)
        else:
            get_logger().log_info(f"Subcloud '{subcloud_name}' is already '{management_state}', skipping unmanage")

        get_logger().log_info(f"Deleting subcloud '{subcloud_name}'")
        DcManagerSubcloudDeleteKeywords(self.ssh_connection).dcmanager_subcloud_delete(subcloud_name)
