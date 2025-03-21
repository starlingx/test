import time
from multiprocessing import get_logger
from time import sleep

from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.ssh.ptp_connection_keywords import PTPConnectionKeywords
from keywords.ptp.cat.cat_ptp_cgu_keywords import CatPtpCguKeywords


class GnssKeywords(BaseKeyword):
    """
    Gnss power on and off using GNSS SSH connection.
    """

    def __init__(self):
        """
        Initializes the GnssKeywords.
        """

    def gnss_power_on(self, hostname: str, nic: str) -> None:
        """
        Power on gnss

        Args:
            hostname (str) : The name of the host
            nic (str) : The name of the nic
        """
        ptp_connect_keywords = PTPConnectionKeywords()
        gnss_ssh_connection = ptp_connect_keywords.get_gnss_server_ssh()

        host_name = hostname.replace("-", "_")
        ptp_config = ConfigurationManager.get_ptp_config()
        pci_slot = ptp_config.get_host(host_name).get_nic(nic).get_pci_slot()
        cgu_location = f"/sys/kernel/debug/ice/{pci_slot}/cgu"

        gpio_switch_port = ptp_config.get_host(host_name).get_nic(nic).get_gpio_switch_port()
        command = f"echo 1 > /sys/class/gpio/gpio{gpio_switch_port}/value"
        # power on gnss
        gnss_ssh_connection.send_as_sudo(command)

        expected_gnss_1pps_state = "valid"
        expected_pps_dpll_status = ["locked_ho_acq"]
        self.validate_gnss_1pps_state_and_pps_dpll_status(hostname, cgu_location, expected_gnss_1pps_state, expected_pps_dpll_status)

    def gnss_power_off(self, hostname: str, nic: str) -> None:
        """
        Power off gnss

        Args:
            hostname (str) : The name of the host
            nic (str) : The name of the nic
        """
        ptp_connect_keywords = PTPConnectionKeywords()
        gnss_ssh_connection = ptp_connect_keywords.get_gnss_server_ssh()

        host_name = hostname.replace("-", "_")
        ptp_config = ConfigurationManager.get_ptp_config()
        pci_slot = ptp_config.get_host(host_name).get_nic(nic).get_pci_slot()
        cgu_location = f"/sys/kernel/debug/ice/{pci_slot}/cgu"

        gpio_switch_port = ptp_config.get_host(host_name).get_nic(nic).get_gpio_switch_port()
        command = f"echo 0 > /sys/class/gpio/gpio{gpio_switch_port}/value"
        # power off gnss
        gnss_ssh_connection.send_as_sudo(command)

        expected_gnss_1pps_state = "invalid"
        expected_pps_dpll_status = ["holdover", "freerun"]
        self.validate_gnss_1pps_state_and_pps_dpll_status(hostname, cgu_location, expected_gnss_1pps_state, expected_pps_dpll_status)

    def validate_gnss_1pps_state_and_pps_dpll_status(
        self,
        hostname: str,
        cgu_location: str,
        expected_gnss_1pps_state: str,
        expected_pps_dpll_status: list,
        timeout: int = 800,
        polling_sleep_time: int = 60,
    ) -> None:
        """
        Validates the GNSS-1PPS state and PPS DPLL status within the specified time.

        Args:
            hostname (str): The name of the host.
            cgu_location (str): the cgu location.
            expected_gnss_1pps_state (str): The expected gnss 1pss state value.
            expected_pps_dpll_status (list): expected list of PPS DPLL status values.
            timeout (int): The maximum time (in seconds) to wait for the match.
            polling_sleep_time (int): The time period to wait to receive the expected output.

        Raises:
            TimeoutError: raised when validate does not equal in the required time
        """
        get_logger().log_info("Attempting Validation - GNSS-1PPS state and PPS DPLL status")
        end_time = time.time() + timeout

        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        cat_ptp_cgu_keywords = CatPtpCguKeywords(ssh_connection)

        # Attempt the validation
        while True:

            # Compute the actual status and state that we are trying to validate.
            ptp_cgu_output = cat_ptp_cgu_keywords.cat_ptp_cgu(cgu_location)
            ptp_cgu_component = ptp_cgu_output.get_cgu_component()

            pps_dpll_object = ptp_cgu_component.get_pps_dpll()
            status = pps_dpll_object.get_status()

            input_object = ptp_cgu_component.get_cgu_input("GNSS-1PPS")
            state = input_object.get_state()

            if status in expected_pps_dpll_status and state == expected_gnss_1pps_state:
                get_logger().log_info("Validation Successful - GNSS-1PPS state and PPS DPLL status")
                return
            else:
                get_logger().log_info("Validation Failed")
                get_logger().log_info(f"Expected GNSS-1PPS state: {expected_gnss_1pps_state}")
                get_logger().log_info(f"Observed GNSS-1PPS state: {state}")
                get_logger().log_info(f"Expected PPS DPLL status: {expected_pps_dpll_status}")
                get_logger().log_info(f"Observed PPS DPLL status: {status}")

                if time.time() < end_time:
                    get_logger().log_info(f"Retrying in {polling_sleep_time}s")
                    sleep(polling_sleep_time)
                    # Move on to the next iteration
                else:
                    raise TimeoutError("Timeout performing validation - GNSS-1PPS state and PPS DPLL status")
