import time

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_object import SystemHostObject
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.upgrade.objects.software_upload_output import SoftwareUploadOutput
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords


class USMKeywords(BaseKeyword):
    """
    Keywords for USM software operations.

    Supports: commands for upgrade and patch management.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection
        self.usm_config = ConfigurationManager.get_usm_config()

    def upload_patch_file(self, patch_file_path: str, sudo: bool = False, os_region_name: str = "") -> SoftwareUploadOutput:
        """
        Upload a single patch file using 'software upload'.

        Args:
            patch_file_path (str): Absolute path to a .patch file.
            sudo (bool): Option to pass the command with sudo.
            os_region_name (str): Use Os region name option for upload if it is specified

        Raises:
            KeywordException: On failure to upload.

        Returns:
            SoftwareUploadOutput: Parsed output containing details of the uploaded patch.
        """
        get_logger().log_info(f"Uploading patch file: {patch_file_path}")
        upload_option = ""
        if os_region_name:
            upload_option = f"--os-region-name {os_region_name}"
        base_cmd = f"software {upload_option} upload {patch_file_path}"
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_upload_patch_timeout_sec()
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Upload completed:\n" + "\n".join(output))
        return SoftwareUploadOutput(output)

    def upload_patch_dir(self, patch_dir_path: str, sudo: bool = False, os_region_name: str = "") -> None:
        """
        Upload all patches in a directory using 'software upload-dir'.

        Args:
            patch_dir_path (str): Absolute path to a directory of .patch files.
            sudo (bool): Option to pass the command with sudo.
            os_region_name (str): OS region name option for upload if it is specified

        Raises:
            KeywordException: On failure to upload.
        """
        get_logger().log_info(f"Uploading patch directory: {patch_dir_path}")
        upload_option = ""
        if os_region_name:
            upload_option = f"--os-region-name {os_region_name}"
        base_cmd = f"software {upload_option} upload-dir {patch_dir_path}"
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_upload_patch_timeout_sec()
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Upload directory completed:\n" + "\n".join(output))

    def show_software_release(self, release_id: str) -> list[str]:
        """
        Show info for a specific release using 'software show'.

        Args:
            release_id (str): ID of the release (e.g., "starlingx-10.0.0")

        Returns:
            list[str]: Raw output lines.

        Raises:
            KeywordException: If release_id is missing or the command fails.
        """
        if not release_id:
            raise KeywordException("Missing release ID for software show")

        get_logger().log_info(f"Showing software release: {release_id}")
        output = self.ssh_connection.send_as_sudo(f"software show {release_id}")
        self.validate_success_return_code(self.ssh_connection)
        return output

    def upload_release(self, iso_path: str, sig_path: str, sudo: bool = False, os_region_name: str = "") -> None:
        """
        Upload a full software release using 'software upload'.

        Args:
            iso_path (str): Absolute path to the .iso file.
            sig_path (str): Absolute path to the corresponding .sig file.
            sudo (bool): Option to pass the command with sudo.
            os_region_name (str): Use Os region name option for upload if it is specified

        Raises:
            KeywordException: On failure to upload.
        """
        get_logger().log_info(f"Uploading software release: ISO={iso_path}, SIG={sig_path}")
        upload_option = ""
        if os_region_name:
            upload_option = f"--os-region-name {os_region_name}"
        base_cmd = f"software {upload_option} upload {iso_path} {sig_path}"
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_upload_release_timeout_sec()
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Release upload completed:\n" + "\n".join(output))

    def upload_and_verify_patch_file(self, patch_file_path: str, expected_release_id: str, timeout: int, poll_interval: int, sudo: bool = False, os_region_name: str = "") -> None:
        """Upload a patch and verify that it becomes available.

        This method is used for USM patching operations. It uploads a `.patch` file
        using `software upload` and polls for the corresponding release ID to appear
        with state "available" using `software show`.

        Args:
            patch_file_path (str): Absolute path to the `.patch` file.
            expected_release_id (str): Expected release ID after patch upload.
            timeout (int): Maximum number of seconds to wait for the release to appear.
            poll_interval (int): Interval (in seconds) between poll attempts.
            sudo (bool): Option to pass the command with sudo.
            os_region_name (str): Use Os region name option for upload if it is specified

        Raises:
            KeywordException: If upload fails or release does not become available in time.
        """
        self.upload_patch_file(patch_file_path, sudo, os_region_name=os_region_name)

        validate_equals_with_retry(
            function_to_execute=lambda: SoftwareListKeywords(self.ssh_connection).get_software_list(sudo=True).get_release_state_by_release_name(expected_release_id),
            expected_value="available",
            validation_description=f"Wait for patch release {expected_release_id} to become available",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def upload_and_verify_release(self, iso_path: str, sig_path: str, expected_release_id: str, timeout: int, poll_interval: int, sudo: bool = False, os_region_name: str = "") -> None:
        """Upload a software release and verify that it becomes available.

        This method is used for USM upgrade operations. It uploads a `.iso` and `.sig`
        pair using `software upload` and waits for the release ID to appear with
        state "available" using `software show`.

        Args:
            iso_path (str): Absolute path to the `.iso` file.
            sig_path (str): Absolute path to the `.sig` signature file.
            expected_release_id (str): Expected release ID after upload.
            timeout (int): Maximum number of seconds to wait for the release to appear.
            poll_interval (int): Interval (in seconds) between poll attempts.
            sudo (bool): Option to pass the command with sudo.
            os_region_name (str): Use Os region name option for upload if it is specified

        Raises:
            KeywordException: If upload fails or release does not become available in time.
        """
        self.upload_release(iso_path, sig_path, sudo, os_region_name)

        validate_equals_with_retry(
            function_to_execute=lambda: SoftwareListKeywords(self.ssh_connection).get_software_list(sudo=True).get_release_state_by_release_name(expected_release_id),
            expected_value="available",
            validation_description=f"Wait for release {expected_release_id} to become available",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def software_deploy_delete(self, sudo: bool = False) -> str:
        """
        This method executed the command 'software deploy delete'

        Args:
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: output
        """
        timeout = self.usm_config.get_deploy_delete_timeout_sec()
        base_cmd = "software deploy delete"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = "".join(output)
        return output

    def software_delete(self, release: str, sudo: bool = False) -> str:
        """
        This method executed the command 'software delete <release>'

        Args:
            release (str): release to be deleted
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: software delete output
        """
        timeout = self.usm_config.get_software_delete_timeout_sec()
        base_cmd = f"software delete {release}"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = "".join(output)
        return output

    def deploy_start(self, release: str, sudo: bool = False) -> str:
        """
        This method executed the command 'software deploy start <release>'

        Args:
            release (str): release to be started
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: software deploy start output
        """
        timeout = self.usm_config.get_deploy_start_timeout_sec()
        base_cmd = f"software deploy start {release}"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = [line.strip() for line in output if line.strip()]
        output = output[0] if output else ""
        return output

    def wait_for_deploy_state(self, expected_deploy_state: str, timeout: int = 6000) -> bool:
        """
        Method to wait for desired state in deploy show

        Args:
            expected_deploy_state (str): Desired state in the deploy show output for the specified release.
            timeout (int): Timeout value to wait for the deploy state to match specified value.

        Returns:
            bool: True / False
        """
        deploy_show = SoftwareDeployShowKeywords(self.ssh_connection)
        end_time = time.time() + timeout
        while time.time() < end_time:
            deploy_state = deploy_show.get_software_deploy_show().get_software_deploy_show().get_state()
            get_logger().log_info(f"Currently deploy state:{deploy_state} ")
            if deploy_state == expected_deploy_state:
                get_logger().log_info(f"Deploy state updated as {deploy_state}")
                return True
            elif "failed" in deploy_state:
                break
            time.sleep(5)
        return False

    def software_deploy_host(self, host: str, sudo: bool = False) -> str:
        """
        This method executed the command 'software deploy host <host>'

        Args:
            host (str): host do be deployed
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: software deploy host result output
        """
        timeout = self.usm_config.get_deploy_host_timeout_sec()
        base_cmd = f"software deploy host {host}"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = [line.strip() for line in output if line.strip()]
        output = output[0] if output else ""
        return output

    def software_deploy_activate(self, sudo: bool = False) -> str:
        """
        This method executed the command 'software deploy activate'

        Args:
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: software deploy activate output
        """
        timeout = self.usm_config.get_deploy_activate_timeout_sec()
        base_cmd = "software deploy activate"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = [line.strip() for line in output if line.strip()]
        output = output[0] if output else ""
        return output

    def active_controller_host_upgrade(self) -> SystemHostObject:
        """
        This method returns the active controller host object for upgrade flows.

        Returns:
            SystemHostObject: active controller host object
        """
        system_host_list_keywords = SystemHostListKeywords(self.ssh_connection)
        return system_host_list_keywords.get_active_controller()

    def standby_controller_host_upgrade(self) -> SystemHostObject | None:
        """
        This method returns the standby controller host object for upgrade flows. If it exists, otherwise None.

        Returns:
            SystemHostObject | None:  standby controller host object or None
        """
        system_host_list_keywords = SystemHostListKeywords(self.ssh_connection)
        output = system_host_list_keywords.get_system_host_with_extra_column(["capabilities"])
        for host in output.system_hosts:
            caps = host.get_capabilities()
            if caps and caps.get_personality() == "Controller-Standby":
                return host
        return None

    def storage_host_upgrade_list(self) -> list[SystemHostObject]:
        """
        This method returns the list of storage nodes, or an empty list if none exist.

        Returns:
            list[SystemHostObject]: List of storage nodes objects
        """
        system_host_list_keywords = SystemHostListKeywords(self.ssh_connection)
        output = system_host_list_keywords.get_system_host_with_extra_column(["capabilities"])
        return [h for h in output.system_hosts if h.get_personality() == "storage"]

    def computes_host_upgrade_list(self) -> list[SystemHostObject]:
        """
        This method returns the list of compute nodes, or an empty list if none exist.

        Returns:
            list[SystemHostObject]: List of compute nodes objects
        """
        system_host_list_keywords = SystemHostListKeywords(self.ssh_connection)
        output = system_host_list_keywords.get_system_host_with_extra_column(["capabilities"])
        return [h for h in output.system_hosts if h.get_personality() == "worker"]

    def deploy_host_upgrade_order(self) -> list[str]:
        """
        This method returns the ordered list of hostnames to be used for 'software deploy host' operations.

        Order rules:
        - Standby controller (if exists)
        - Active controller
        - Storage nodes (alphabetical order)
        - Compute nodes (alphabetical order)

        Returns:
            list[str]: ordered list of hostnames for upgrade flows.
        """
        order: list[str] = []

        # Controllers
        active = self.active_controller_host_upgrade()
        standby = self.standby_controller_host_upgrade()

        if standby is not None:
            order.append(standby.get_host_name())

        order.append(active.get_host_name())

        # Storages (alphabetical)
        storages = self.storage_host_upgrade_list()
        storage_names = sorted(host.get_host_name() for host in storages)
        order.extend(storage_names)

        # Computes (alphabetical)
        computes = self.computes_host_upgrade_list()
        compute_names = sorted(host.get_host_name() for host in computes)
        order.extend(compute_names)

        return order

    def software_deploy_complete(self, sudo: bool = False) -> str:
        """
        This method executed the command 'software deploy complete'

        Args:
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: software deploy complete output
        """
        timeout = self.usm_config.get_deploy_complete_timeout_sec()
        base_cmd = "software deploy complete"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = [line.strip() for line in output if line.strip()]
        output = output[0] if output else ""
        return output
