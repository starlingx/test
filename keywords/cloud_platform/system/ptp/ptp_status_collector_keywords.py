from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.cat.cat_ptp_cgu_keywords import CatPtpCguKeywords
from keywords.ptp.gnss_keywords import GnssKeywords
from keywords.ptp.pmc.pmc_keywords import PMCKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


class PTPStatusCollectorKeywords(BaseKeyword):
    """Keywords for collecting PTP status without validation."""

    def __init__(self, ssh_connection, ptp_setup: PTPSetupKeywords):
        """Initialize PTP status collector.

        Args:
            ssh_connection: SSH connection to the system.
            ptp_setup (PTPSetupKeywords): PTP setup configuration.
        """
        self.ssh_connection = ssh_connection
        self.ptp4l_setup_list = ptp_setup.get_ptp4l_setup_list()
        self.phc2sys_setup_list = ptp_setup.get_phc2sys_setup_list()
        self.ts2phc_setup_list = ptp_setup.get_ts2phc_setup_list()
        self.clock_setup_list = ptp_setup.get_clock_setup_list()

    def collect_all_ptp_status(self) -> None:
        """Collect all PTP status information without validation."""
        get_logger().log_info("Collecting PTP status information")

        hosts = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_controllers_and_computes()

        self.collect_gnss_status(hosts)
        self.collect_sma_status(hosts)
        self.collect_systemctl_status()
        self.collect_ptp_pmc_values()
        self.collect_ptp_config_files()
        self.collect_alarms()

    def collect_gnss_status(self, hosts: list) -> None:
        """Collect GNSS status.

        Args:
            hosts (list): List of controllers and computes.
        """
        get_logger().log_info("Collecting GNSS status")
        gnss_keywords = GnssKeywords()

        for ts2phc_instance_obj in self.ts2phc_setup_list:
            gnss_port = gnss_keywords.extract_gnss_port(ts2phc_instance_obj.get_instance_parameters())

            if not gnss_port:
                get_logger().log_info("Skipping GNSS status collection - GNSS port is None")
                continue

            if gnss_port == "ttyACM0":
                get_logger().log_info(f"Skipping GNSS status collection for {gnss_port} - not valid for USB serial device type")
                return

            for ptp_host_if in ts2phc_instance_obj.get_ptp_interfaces():
                for host in hosts:
                    interfaces = ptp_host_if.get_interfaces_for_hostname(host.get_host_name())
                    for interface in filter(None, interfaces):
                        pci_address = gnss_keywords.get_pci_slot_name(host.get_host_name(), interface)
                        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
                        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host.get_host_name())
                        CatPtpCguKeywords(host_ssh).cat_ptp_cgu(cgu_location)

    def collect_sma_status(self, hosts: list) -> None:
        """Collect SMA status.

        Args:
            hosts (list): List of controllers and computes.
        """
        get_logger().log_info("Collecting SMA status")
        gnss_keywords = GnssKeywords()

        for clock_instance_obj in self.clock_setup_list:
            for ptp_host_if in clock_instance_obj.get_ptp_interfaces():
                if "input" not in ptp_host_if.get_ptp_interface_parameter():
                    continue

                for host in hosts:
                    interfaces = ptp_host_if.get_interfaces_for_hostname(host.get_host_name())
                    for interface in filter(None, interfaces):
                        pci_address = gnss_keywords.get_pci_slot_name(host.get_host_name(), interface)
                        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
                        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host.get_host_name())
                        CatPtpCguKeywords(host_ssh).cat_ptp_cgu(cgu_location)

    def collect_systemctl_status(self) -> None:
        """Collect systemctl status for all PTP services per host."""
        get_logger().log_info("Collecting systemctl status")

        for service_type, setup_list in [
            ("ptp4l", self.ptp4l_setup_list),
            ("phc2sys", self.phc2sys_setup_list),
            ("ts2phc", self.ts2phc_setup_list),
        ]:
            for instance_obj in setup_list:
                name = instance_obj.get_name()
                service_name = f"{service_type}@{name}.service"

                for hostname in instance_obj.get_instance_hostnames():
                    host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
                    systemctl_keywords = SystemCTLStatusKeywords(host_ssh)
                    systemctl_keywords.get_status(service_name)

    def collect_ptp_pmc_values(self) -> None:
        """Collect PMC values for all PTP instances."""
        get_logger().log_info("Collecting PMC values")

        for ptp4l_setup in self.ptp4l_setup_list:
            name = ptp4l_setup.get_name()
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"

            for hostname in ptp4l_setup.get_instance_hostnames():
                for ptp_interface in ptp4l_setup.get_ptp_interfaces():
                    interfaces = ptp_interface.get_interfaces_for_hostname(hostname)
                    if interfaces:
                        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
                        pmc_keywords = PMCKeywords(host_ssh)
                        pmc_keywords.pmc_get_port_data_set(config_file, socket_file)
                        pmc_keywords.pmc_get_domain(config_file, socket_file)
                        pmc_keywords.pmc_get_parent_data_set(config_file, socket_file)
                        pmc_keywords.pmc_get_time_properties_data_set(config_file, socket_file)
                        pmc_keywords.pmc_get_grandmaster_settings_np(config_file, socket_file)

    def collect_ptp_config_files(self) -> None:
        """Collect PTP configuration file contents per host."""
        get_logger().log_info("Collecting PTP config files")

        for ptp4l_setup in self.ptp4l_setup_list:
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{ptp4l_setup.get_name()}.conf"
            for hostname in ptp4l_setup.get_instance_hostnames():
                host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
                FileKeywords(host_ssh).read_file(config_file)

        for phc2sys_setup in self.phc2sys_setup_list:
            config_file = f"/etc/linuxptp/ptpinstance/phc2sys-{phc2sys_setup.get_name()}.conf"
            for hostname in phc2sys_setup.get_instance_hostnames():
                host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
                FileKeywords(host_ssh).read_file(config_file)

        for ts2phc_setup in self.ts2phc_setup_list:
            config_file = f"/etc/linuxptp/ptpinstance/ts2phc-{ts2phc_setup.get_name()}.conf"
            for hostname in ts2phc_setup.get_instance_hostnames():
                host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
                FileKeywords(host_ssh).read_file(config_file)

    def collect_alarms(self) -> None:
        """Collect system alarms."""
        get_logger().log_info("Collecting system alarms")
        AlarmListKeywords(self.ssh_connection).get_alarm_list()
