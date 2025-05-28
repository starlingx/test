from config.configuration_manager import ConfigurationManager
from framework.ssh.prompt_response import PromptResponse
from keywords.base_keyword import BaseKeyword
from keywords.ptp.gnss_keywords import GnssKeywords


class SmaKeywords(BaseKeyword):
    """
    Disabled and enable SMA using SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SmaKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def disable_sma(self, hostname: str, nic: str) -> None:
        """
        Disables the SMA output on the specified interface.

        Args:
            hostname (str): The name of the host.
            nic (str): The name of the NIC.

        Returns : None
        """
        gnss_keywords = GnssKeywords()

        # Normalize host name for PTP config access
        normalized_hostname = hostname.replace("-", "_")
        ptp_config = ConfigurationManager.get_ptp_config()
        interface = ptp_config.get_host(normalized_hostname).get_nic(nic).get_base_port()

        # Disable SMA1 pin
        command = f"echo 0 1 > /sys/class/net/{interface}/device/ptp/ptp1/pins/SMA1"

        # Setup expected prompts for password request and echo command
        password_prompt = PromptResponse("Password:", ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
        root_cmd = PromptResponse("root@", command)
        expected_prompts = [password_prompt, root_cmd]

        # Run echo command to crash standby controller
        self.ssh_connection.send_expect_prompts("sudo su", expected_prompts)

        # Expected states for validation
        expected_cgu_input_state = "invalid"
        expected_dpll_status_list = ["holdover"]

        # Construct CGU location path
        pci_address = gnss_keywords.get_pci_slot_name(hostname, interface)
        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"

        # Validate GNSS 1PPS state and DPLL status
        gnss_keywords.validate_sma1_and_gnss_1pps_eec_pps_dpll_status_with_retry(hostname, cgu_location, "SMA1", expected_cgu_input_state, expected_dpll_status_list)

    def enable_sma(self, hostname: str, nic: str) -> None:
        """
        Enables the SMA output on the specified interface.

        Args:
            hostname (str): The name of the host.
            nic (str): The name of the NIC.

        Returns : None
        """
        gnss_keywords = GnssKeywords()

        # Normalize host name for PTP config access
        normalized_hostname = hostname.replace("-", "_")
        ptp_config = ConfigurationManager.get_ptp_config()
        interface = ptp_config.get_host(normalized_hostname).get_nic(nic).get_base_port()

        # Enable SMA1 pin
        command = f"echo 1 1 > /sys/class/net/{interface}/device/ptp/ptp1/pins/SMA1"

        # Setup expected prompts for password request and echo command
        password_prompt = PromptResponse("Password:", ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
        root_cmd = PromptResponse("root@", command)
        expected_prompts = [password_prompt, root_cmd]

        # Run echo command to crash standby controller
        self.ssh_connection.send_expect_prompts("sudo su", expected_prompts)

        # Construct CGU location path
        pci_address = gnss_keywords.get_pci_slot_name(hostname, interface)
        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"

        # Validate GNSS 1PPS state and DPLL status
        gnss_keywords.validate_sma1_and_gnss_1pps_eec_pps_dpll_status_with_retry(hostname, cgu_location, "SMA1")
