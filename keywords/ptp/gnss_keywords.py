import re
import time
from multiprocessing import get_logger

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
        if not gpio_switch_port:
            raise Exception(f"GPIO switch port not configured for {hostname} {nic}")

        # Export GPIO pin if not already exported
        export_cmd = f"if [ ! -d /sys/class/gpio/gpio{gpio_switch_port} ]; then echo {gpio_switch_port} > /sys/class/gpio/export; fi"
        gnss_ssh_connection.send(export_cmd)

        # Set direction to output
        direction_cmd = f"echo out > /sys/class/gpio/gpio{gpio_switch_port}/direction"
        gnss_ssh_connection.send(direction_cmd)

        # Set GPIO value to 1 (power on GNSS)
        value_cmd = f"echo 1 > /sys/class/gpio/gpio{gpio_switch_port}/value"
        gnss_ssh_connection.send(value_cmd)

        self.validate_sma1_and_gnss_1pps_eec_pps_dpll_status_with_retry(hostname, cgu_location, timeout=1200, polling_interval=120)

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
        if not gpio_switch_port:
            raise Exception(f"GPIO switch port not configured for {hostname} {nic}")

        # Export GPIO pin if not already exported
        export_cmd = f"if [ ! -d /sys/class/gpio/gpio{gpio_switch_port} ]; then echo {gpio_switch_port} > /sys/class/gpio/export; fi"
        gnss_ssh_connection.send(export_cmd)

        # Set direction to output
        direction_cmd = f"echo out > /sys/class/gpio/gpio{gpio_switch_port}/direction"
        gnss_ssh_connection.send(direction_cmd)

        # Set GPIO value to 0 (power off GNSS)
        value_cmd = f"echo 0 > /sys/class/gpio/gpio{gpio_switch_port}/value"
        gnss_ssh_connection.send(value_cmd)

        # Expected states for validation
        expected_cgu_input_state = "invalid"
        expected_dpll_status_list = ["holdover"]

        self.validate_sma1_and_gnss_1pps_eec_pps_dpll_status_with_retry(hostname, cgu_location, expected_cgu_input_state=expected_cgu_input_state, expected_dpll_status_list=expected_dpll_status_list, timeout=1500, polling_interval=120)

    def validate_sma1_and_gnss_1pps_eec_pps_dpll_status_with_retry(
        self,
        hostname: str,
        cgu_location: str,
        cgu_input: str = "GNSS-1PPS",
        expected_cgu_input_state: str = "valid",
        expected_dpll_status_list: list = ["locked_ho_acq"],
        timeout: int = 800,
        polling_interval: int = 60,
    ) -> None:
        """
        Validates the synchronization status of SMA1, GNSS 1PPS input, and both EEC and PPS DPLLs
        on the specified host within a defined timeout.

        Args:
            hostname (str): Hostname of the target system.
            cgu_location (str): Path to the CGU debug file on the target system.
            cgu_input (str): CGU input identifier (e.g., "GNSS_1PPS" or "SMA1").
            expected_cgu_input_state (str): Expected CGU input state (e.g., "valid", "invalid").
            expected_dpll_status_list (list): List of acceptable DPLL statuses (e.g., ["locked_ho_acq"], ["holdover", "freerun"]).
            timeout (int): Maximum wait time in seconds for synchronization (default: 800).
            polling_interval (int): Time in seconds between polling attempts (default: 60).

        Returns: None

        Raises:
            TimeoutError: If expected input state or DPLL statuses are not observed within the timeout period.

        Notes:
            Status	        Meaning
            locked	        DPLL is locked to a valid timing source.
            holdover	    Timing is maintained using previously locked values (interim fallback).
            freerun	        No synchronization — internal clock is free-running.
            invalid	        Signal or lock state is not usable.
            locked_ho_acq	locked with holdover acquisition.
        """
        get_logger().log_info("Attempting Validation - CGU input state and DPLL statuses...")
        end_time = time.time() + timeout

        ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        cgu_reader = CatPtpCguKeywords(ssh_connection)

        # Attempt the validation
        while True:
            cgu_output = cgu_reader.cat_ptp_cgu(cgu_location)
            cgu_component = cgu_output.get_cgu_component()

            eec_dpll_status = cgu_component.get_eec_dpll().get_status()
            pps_dpll_status = cgu_component.get_pps_dpll().get_status()
            cgu_input_state = cgu_component.get_cgu_input(cgu_input).get_state()

            if cgu_input_state == expected_cgu_input_state and eec_dpll_status in expected_dpll_status_list and pps_dpll_status in expected_dpll_status_list:
                get_logger().log_info("Validation Successful - CGU input state and both DPLL statuses match expectations.")
                return
            else:
                get_logger().log_info("Validation Failed")
                get_logger().log_info(f"Expected CGU input {cgu_input} state: {expected_cgu_input_state}, Observed: {cgu_input_state}")
                get_logger().log_info(f"Expected EEC DPLL status: {expected_dpll_status_list}, Observed: {eec_dpll_status}")
                get_logger().log_info(f"Expected PPS DPLL status: {expected_dpll_status_list}, Observed: {pps_dpll_status}")

                if time.time() < end_time:
                    get_logger().log_info(f"Retrying in {polling_interval}s")
                    time.sleep(polling_interval)
                    # Move on to the next iteration
                else:
                    raise TimeoutError("Timeout exceeded: CGU input state or DPLL statuses did not meet expected values.")
