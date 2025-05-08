import re
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

    def get_pci_slot_name(self, hostname: str, interface: str) -> str:
        """
        Retrieves the PCI_SLOT_NAME from the uevent file for a given PTP interface.

        Args:
            hostname (str) : The name of the host
            interface (str): The name of the ptp interface (e.g., "enp138s0f0").

        Returns:
            str: The PCI slot name if found, otherwise None.

        Raises:
            Exception: raised when PCI_SLOT_NAME not found
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)

        # The GNSS signal will always be on port 0 of the NIC, even if ts2phc uses ports 1, 2, 3, and so on.
        interface_name = f"{interface[:-1]}0"
        uevent_path = f"/sys/class/net/{interface_name}/device/uevent"

        uevent_content = ssh_connection.send(f"grep PCI_SLOT_NAME {uevent_path}")

        # Use regex to find the PCI_SLOT_NAME
        match = re.search(r"PCI_SLOT_NAME=(.*)", " ".join(uevent_content))
        if match:
            return match.group(1).strip()  # Return the captured value, removing leading/trailing spaces
        else:
            raise Exception(f"PCI_SLOT_NAME not found in {uevent_path}")

    def get_gnss_serial_port_from_gnss_directory(self, hostname: str, interface: str) -> str:
        """
        Get GNSS serial port from the specified gnss directory.

        Args:
            hostname (str) : The name of the host
            interface (str): The name of the PTP interface (e.g., "enp138s0f0").

        Returns:
            str: The GNSS serial port value (e.g., "gnss0") if found, otherwise None.
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)

        pci_address = self.get_pci_slot_name(hostname, interface)

        gnss_dir = f"/sys/bus/pci/devices/{pci_address}/gnss"

        contents = ssh_connection.send(f"ls {gnss_dir}")
        if not contents:
            get_logger().log_info(f"The directory {gnss_dir} is empty.")
            return None

        return " ".join(contents).strip()  # Return the captured value in str, removing leading/trailing spaces

    def extract_gnss_port(self, instance_parameters: str) -> str:
        """
        Extracts the GNSS serial port value from a ts2phc.nmea_serialport configuration string using regex.

        Args:
            instance_parameters (str): The string containing the ts2phc.nmea_serialport setting.

        Returns:
            str: The GNSS serial port value (e.g., "gnss0") if found, otherwise None.
        """
        match = re.search(r"ts2phc\.nmea_serialport\s*=\s*/dev/([^ ]*)", instance_parameters)
        if match:
            return match.group(1)
        else:
            return None

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
        interface = ptp_config.get_host(host_name).get_nic(nic).get_base_port()
        pci_address = self.get_pci_slot_name(hostname, interface)
        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"

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
        interface = ptp_config.get_host(host_name).get_nic(nic).get_base_port()
        pci_address = self.get_pci_slot_name(hostname, interface)
        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"

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

        Returns: None

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
