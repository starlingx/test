import time
from multiprocessing import get_logger
from typing import List

from config.configuration_manager import ConfigurationManager
from framework.ssh.prompt_response import PromptResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


class PhcCtlKeywords(BaseKeyword):
    """
    Directly control PHC device clock using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the PhcCtlKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def phc_ctl_get(self, device: str) -> str:
        """
        Get the current time of the PHC clock device

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.

        Example:
            phc_ctl[643764.828]: clock time is 1739856255.215802036 or Tue Feb 18 05:24:15 2025

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} get")
        self.validate_success_return_code(self.ssh_connection)
        output_str = "".join(output).replace("\n", "")
        if output_str and len(output_str.split()) > 4:
            return output_str.split()[4]
        else:
            raise "output_str.split() is expected to be a List with four elements."

    def phc_ctl_cmp(self, device: str) -> str:
        """
        Compare the PHC clock device to CLOCK_REALTIME

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.

        Example:
            phc_ctl[645639.878]: offset from CLOCK_REALTIME is -37000000008ns

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} cmp")
        self.validate_success_return_code(self.ssh_connection)
        output_str = "".join(output)
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[5]
        else:
            raise "output_str.split() is expected to be a List with five elements."

    def phc_ctl_adj(self, device: str, seconds: str) -> str:
        """
        Adjust the PHC clock by an amount of seconds provided

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.
            seconds :

        Example:
            phc_ctl[646368.470]: adjusted clock by 0.000001 seconds

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} adj {seconds}")
        self.validate_success_return_code(self.ssh_connection)
        output_str = "".join(output).replace("\n", "")
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[4]
        else:
            raise "output_str.split() is expected to be a List with five elements."

    def phc_ctl_set(self, device: str, seconds: str = None) -> str:
        """
        Set the PHC clock time to the value specified in seconds. Defaults to reading CLOCK_REALTIME if no value is provided.

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.
            seconds :

        Example :
            phc_ctl[647759.416]: set clock time to 1739860212.789318498 or Tue Feb 18 06:30:12 2025

        Returns:
        """
        if seconds:
            cmd = f"phc_ctl {device} set {seconds}"
        else:
            cmd = f"phc_ctl {device} set"

        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        output_str = "".join(output).replace("\n", "")
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[5]
        else:
            raise "output_str.split() is expected to be a List with five elements."

    def wait_for_phc_ctl_adjustment_alarm(self, interface: str, alarms: List[AlarmListObject], timeout: int = 120, polling_interval: int = 10) -> None:
        """
        Run a remote phc_ctl adjustment loop on the controller as root,
        and stop it once the specified PTP alarm(s) are detected or
        a timeout occurs.

        Args:
            interface (str): The interface to apply phc_ctl adjustments to.
            alarms (List[AlarmListObject]): A list of expected alarm objects to wait for.
            timeout (int): Maximum wait time in seconds (default: 120).
            polling_interval (int): Interval in seconds between polling attempts (default: 10).

        Returns: None

        Raises:
            TimeoutError: If the expected alarms are not observed within the timeout period.
        """
        # Prepare prompt responses for entering sudo
        password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        password_prompt = PromptResponse("Password:", password)

        def run_as_root(command: str) -> None:
            """
            Executes a given shell command on the remote host as the root user using 'sudo su'.

            Args:
                command (str): The shell command to be executed with root privileges.

            Returns:
                None
            """
            root_prompt = PromptResponse("#", command)
            self.ssh_connection.send_expect_prompts("sudo su", [password_prompt, root_prompt])

        # Create and store the phc_ctl loop script
        remote_script_path = "/tmp/phc_loop.sh"
        loop_script = f"while true; do phc_ctl {interface} -q adj 0.0001; sleep 1; done"
        run_as_root(f"echo '{loop_script}' > {remote_script_path}")
        run_as_root(f"chmod +x {remote_script_path}")
        run_as_root(f"nohup bash {remote_script_path} & echo $! > /tmp/phc_loop.pid")

        alarm_keywords = AlarmListKeywords(LabConnectionKeywords().get_active_controller_ssh())
        alarm_descriptions = ", ".join(alarm_keywords.alarm_to_str(alarm_obj) for alarm_obj in alarms)

        get_logger().log_info(f"Waiting for alarms: {alarm_descriptions}")

        end_time = time.time() + timeout
        all_matched = False

        while time.time() < end_time:
            observed_alarms = alarm_keywords.alarm_list()
            all_matched = all(any(alarm_keywords.alarms_match(observed_alarm_obj, expected_alarm_obj) for observed_alarm_obj in observed_alarms) for expected_alarm_obj in alarms)

            if all_matched:
                get_logger().log_info("All expected alarms have been observed.")
                break

            remaining = end_time - time.time()
            get_logger().log_info(f"Expected alarms not fully observed yet. Retrying in {polling_interval}s. " f"Time remaining: {remaining:.2f}s")
            time.sleep(polling_interval)

        # Clean up: stop script and remove temp files
        run_as_root("test -f /tmp/phc_loop.pid && kill $(cat /tmp/phc_loop.pid) 2>/dev/null")
        run_as_root("rm -f /tmp/phc_loop.sh /tmp/phc_loop.pid")

        if not all_matched:
            observed_alarm_strs = [alarm_keywords.alarm_to_str(observed_alarm_obj) for observed_alarm_obj in observed_alarms]
            raise TimeoutError(f"Timeout: Expected alarms not found within {timeout}s.\n" f"Expected: {alarm_descriptions}\n" f"Observed:\n" + "\n".join(observed_alarm_strs))
