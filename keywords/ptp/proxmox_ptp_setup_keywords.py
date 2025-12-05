from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.ptp.proxmox_keywords import ProxmoxKeywords


class ProxmoxPTPSetupKeywords(BaseKeyword):
    """Keywords for Proxmox PTP VM setup operations."""

    def setup_proxmox_environment(self, ptp_test_scenario_reader, ptp_setup_template_path: str, operation_name: str) -> ProxmoxKeywords:
        """
        Setup Proxmox PTP VM environment.

        Args:
            ptp_test_scenario_reader: PTP test scenario reader instance.
            ptp_setup_template_path (str): Path to PTP setup template.
            operation_name (str): Operation name from test scenario.

        Returns:
            ProxmoxKeywords: Proxmox keywords instance for cleanup operations.
        """
        proxmox_config = ptp_test_scenario_reader.get_proxmox_config(operation_name)

        ptp_config = ConfigurationManager.get_ptp_config()
        hostname_key = proxmox_config["hostname"].replace("-", "_")
        proxmox_vm_config = ptp_config.get_host(hostname_key).get_nic(proxmox_config["nic"]).get_proxmox_ptp_vm_config()
        proxmox_keywords = ProxmoxKeywords(proxmox_vm_config)

        get_logger().log_info("Starting PTP VM verification with auto-recovery capability")
        proxmox_keywords.verify_ptp_service_with_auto_recovery()

        return proxmox_keywords
