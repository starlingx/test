from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.system.ptp.objects.gnss_monitoring_data_output import GnssMonitoringDataOutput
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.cat.cat_ptp_config_keywords import CatPtpConfigKeywords
from keywords.ptp.cat.gnss_monitor_conf_keywords import GnssMonitorConfKeywords


class GnssMonitoringKeywords(BaseKeyword):
    """
    Keywords for GNSS monitoring operations using existing system keywords.
    """

    def __init__(self, ssh_connection):
        """
        Initialize GNSS monitoring keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_gnss_monitoring_data(self, device_path: str) -> GnssMonitoringDataOutput:
        """
        Get GNSS monitoring data using the CLI tool.

        Args:
            device_path (str): Path to the GNSS device (e.g., "/dev/ttyACM0").

        Returns:
            GnssMonitoringDataOutput: Parsed monitoring data output.
        """
        get_logger().log_info(f"Getting GNSS monitoring data for device {device_path}")
        cli_command = f"python /usr/rootdirs/opt/collectd/extensions/python/ptp_gnss_monitor_cli.py --devices {device_path}"
        output = self.ssh_connection.send_as_sudo(cli_command)
        self.validate_success_return_code(self.ssh_connection)
        return GnssMonitoringDataOutput(output)

    def create_monitoring_instance(self, instance_name: str) -> None:
        """
        Create a GNSS monitoring PTP instance.

        Args:
            instance_name (str): Name of the monitoring instance.

        Returns: None
        """
        self.ptp_instance_keywords = SystemPTPInstanceKeywords(self.ssh_connection)
        get_logger().log_info(f"Creating GNSS monitoring instance {instance_name}")
        return self.ptp_instance_keywords.system_ptp_instance_add(instance_name, "gnss-monitor")

    def verify_monitoring_configuration_file(self, expected_satellite_count: int, expected_signal_quality: int, expected_devices: str) -> None:
        """
        Verify the monitoring configuration file contains expected values.

        Args:
            expected_satellite_count (int): Expected satellite count threshold.
            expected_signal_quality (int): Expected signal quality threshold.
            expected_devices (str): Expected device paths.

        Returns: None
        """
        get_logger().log_info("Verifying monitoring configuration file")

        gnss_conf_output = GnssMonitorConfKeywords((self.ssh_connection)).cat_gnss_monitor_conf("/etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf")
        gnss_conf_object = gnss_conf_output.get_gnss_monitor_conf_object()

        actual_devices = gnss_conf_object.get_devices()
        actual_satellite_count = gnss_conf_object.get_satellite_count()
        actual_signal_quality_db = gnss_conf_object.get_signal_quality_db()

        validate_equals(actual_satellite_count, expected_satellite_count, "satellite_count not found in configuration")

        validate_equals(actual_signal_quality_db, expected_signal_quality, "signal_quality_db not found in configuration")

        validate_equals(actual_devices, expected_devices, "devices not found in configuration")

    def wait_for_monitoring_configuration_file(self, expected_satellite_count: int, expected_signal_quality: int, expected_devices: str) -> None:
        """
        Wait for monitoring configuration file to contain expected values.

        Args:
            expected_satellite_count (int): Expected satellite count threshold.
            expected_signal_quality (int): Expected signal quality threshold.
            expected_devices (str): Expected device paths.

        Returns: None

        Raises:
            TimeoutError: raised when validate does not equal in the required time
        """
        get_logger().log_info("Waiting for monitoring configuration file to match expected values")

        def check_monitoring_config_matches() -> bool:
            """
            Check if configuration file matches expected values.

            Returns:
                bool: True if all values match, False otherwise.
            """
            gnss_conf_output = GnssMonitorConfKeywords(self.ssh_connection).cat_gnss_monitor_conf("/etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf")
            gnss_conf_object = gnss_conf_output.get_gnss_monitor_conf_object()
            actual_devices = gnss_conf_object.get_devices()
            actual_satellite_count = gnss_conf_object.get_satellite_count()
            actual_signal_quality_db = gnss_conf_object.get_signal_quality_db()
            return actual_satellite_count == expected_satellite_count and actual_signal_quality_db == expected_signal_quality and actual_devices == expected_devices

        validate_equals_with_retry(check_monitoring_config_matches, True, "monitoring configuration file to match expected values", 120, 10)

    def verify_gpsd_service_status(self, devices: list[str], expected_status: str = "active") -> None:
        """
        Verify gpsd service status and gpspipe services for devices.

        Args:
            devices (list[str]): List of device paths (e.g., ["/dev/ttyACM0", "/dev/gnssx"]).
            expected_status (str): Expected service status (default: "active").

        Returns: None
        """
        get_logger().log_info("Verifying gpsd service status")
        service_status = SystemCTLStatusKeywords(self.ssh_connection).get_status("gpsd.service")
        status_output = "\n".join(service_status) if isinstance(service_status, list) else service_status
        validate_str_contains(status_output, f"Active: {expected_status}", "gpsd service status")

        for device in devices:
            device_name = device.replace("/dev/", "").replace("/", "-")
            gpspipe_service = f"gpspipe@-dev-{device_name}.service"
            validate_str_contains(status_output, gpspipe_service, f"gpspipe service for {device_name} should be running")

    def verify_pty_device_exists(self, device_path: str, should_exist: bool = True) -> None:
        """
        Verify PTY device exists or doesn't exist.

        Args:
            device_path (str): Path to the original device (e.g., "/dev/ttyACM0").
            should_exist (bool): Whether the PTY device should exist (default: True).

        Returns: None
        """
        pty_path = f"{device_path}.pty"
        get_logger().log_info(f"Verifying PTY device {pty_path} existence: {should_exist}")

        file_keywords = FileKeywords(self.ssh_connection)
        pty_exists = file_keywords.file_exists(pty_path)

        validate_equals(pty_exists, should_exist, f"PTY device {pty_path} expected existance: {should_exist}")

    def wait_for_monitoring_services_active(self, devices: list[str]) -> None:
        """
        Wait for monitoring services to be active and running.

        Args:
            devices (list[str]): List of device paths (e.g., ["/dev/ttyACM0", "/dev/gnssx"]).

        Returns: None

        Raises:
            TimeoutError: raised when validate does not equal in the required time
        """
        get_logger().log_info("Waiting for monitoring services to be active")

        def check_services_active() -> bool:
            """
            Checks if gpsd and gpspipe services are active and running.

            Returns:
                bool: True if all services are active and running, False otherwise.
            """
            gpsd_status_output = SystemCTLStatusKeywords(self.ssh_connection).get_status("gpsd")
            if not any("Active: active (running)" in line for line in gpsd_status_output or []):
                return False

            for device in devices:
                device_name = device.replace("/dev/", "").replace("/", "-")
                gpspipe_service = f"gpspipe@-dev-{device_name}.service"
                gpspipe_status_output = SystemCTLStatusKeywords(self.ssh_connection).get_status(gpspipe_service)
                if not any("Active: active (running)" in line for line in gpspipe_status_output or []):
                    return False

            return True

        validate_equals_with_retry(check_services_active, True, "systemctl status for gpsd services to be active", 180, 30)

        alarm_list_object = AlarmListObject()
        alarm_list_object.set_alarm_id("250.001")
        AlarmListKeywords(self.ssh_connection).set_timeout_in_seconds(180)
        AlarmListKeywords(self.ssh_connection).wait_for_alarms_cleared([alarm_list_object])

    def wait_for_monitoring_services_inactive(self) -> None:
        """
        Wait for monitoring services to be inactive.

        Returns: None

        Raises:
            TimeoutError: raised when validate does not equal in the required time
        """
        get_logger().log_info("Waiting for monitoring services to be inactive")

        def check_services_inactive() -> bool:
            """
            Checks if gpsd service is inactive.

            Returns:
                bool: True if gpsd service is inactive, False otherwise.
            """
            gpsd_status_output = SystemCTLStatusKeywords(self.ssh_connection).get_status("gpsd")
            return any("Active: inactive (dead)" in line for line in gpsd_status_output or [])

        validate_equals_with_retry(check_services_inactive, True, "systemctl status for gpsd services to be inactive", 120, 30)

        alarm_objects = []
        for alarm_id in ["250.001", "100.119"]:
            alarm_obj = AlarmListObject()
            alarm_obj.set_alarm_id(alarm_id)
            alarm_objects.append(alarm_obj)
        AlarmListKeywords(self.ssh_connection).wait_for_alarms_cleared(alarm_objects)

    def verify_device_exists(self, device_path: str) -> None:
        """
        Verify that a device exists on the system.

        Args:
            device_path (str): Path to the device (e.g., "/dev/ttyACM0").

        Returns: None
        """
        get_logger().log_info(f"Verifying device {device_path} exists")
        device_check = self.ssh_connection.send(f"ls {device_path}")
        device_check_str = "\n".join(device_check) if isinstance(device_check, list) else device_check
        validate_str_contains(device_check_str, device_path, f"Device {device_path} should exist")

    def verify_gnss_pty_data(self, device_path: str) -> None:
        """
        Verify GNSS data through PTY device.

        Args:
            device_path (str): Path to the original device (e.g., "/dev/ttyACM0").

        Returns: None
        """
        pty_path = f"{device_path}.pty"
        get_logger().log_info(f"Verifying GNSS data from PTY device {pty_path}")
        gnss_data = self.ssh_connection.send_as_sudo(f"timeout 60 cat {pty_path} | head -20")
        gnss_data_str = "\n".join(gnss_data) if isinstance(gnss_data, list) else gnss_data
        validate_str_contains(gnss_data_str, "$GP", "Should receive NMEA data through PTY device")

    def verify_ts2phc_config_serialport(self, instance_name: str, expected_serialport: str) -> None:
        """
        Verify ts2phc configuration file contains correct nmea_serialport setting.

        Args:
            instance_name (str): Name of the PTP instance.
            expected_serialport (str): Expected serialport path (e.g., "/dev/ttyACM0" or "/dev/ttyACM0.pty").

        Returns: None
        """
        config_file = f"/etc/linuxptp/ptpinstance/ts2phc-{instance_name}.conf"
        get_logger().log_info(f"Verifying ts2phc config file {config_file}")

        cat_ptp_config_keywords = CatPtpConfigKeywords(self.ssh_connection)
        cat_ptp_config_output = cat_ptp_config_keywords.cat_ptp_config(config_file)
        get_pmc_get_default_data_set_object = cat_ptp_config_output.data_set_output.get_pmc_get_default_data_set_object()
        observed_serialport = get_pmc_get_default_data_set_object.get_ts2phc_nmea_serialport()

        validate_equals(observed_serialport, expected_serialport, "verify ts2phc.nmea_serialport")
