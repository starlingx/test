from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords

SERVICE_EXPECTED_LINES = [
    "After=kubelet.service",
    "Requires=kubelet.service",
    "[Service]",
    "ExecStart=/usr/local/sbin/isolcpu_plugin",
    "ExecStartPost=/bin/bash -c 'echo $MAINPID > /var/run/isolcpu_plugin.pid'",
    "Restart=no",
    "RestartSec=3",
    "[Install]",
    "WantedBy=multi-user.target",
]

CONF_EXPECTED_LINES = [
    "process  = isolcpu_plugin",
    "service  = isolcpu_plugin",
    "pidfile  = /var/run/isolcpu_plugin.pid",
    "style    = lsb",
    "severity = major",
    "restarts = 3",
    "startuptime = 5",
    "interval = 5",
    "debounce = 20",
    "subfunction = worker",
]


@mark.p1
def test_isolcpu_plugin_configuration():
    """
    Verify isolcpu_plugin configuration files and service status on all worker hosts.

    Test Steps:
        - Get all hosts with worker capability
        - Verify /lib/systemd/system/isolcpu_plugin.service exists and has correct content
        - Verify /etc/pmon.d/isolcpu_plugin.conf exists and has correct content
        - Verify isolcpu_plugin.service is active
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    worker_hosts = SystemHostListKeywords(ssh_connection).get_workers()

    # Isolcpu plugin runs on worker nodes only
    for worker_host in worker_hosts:
        hostname = worker_host.get_host_name()
        worker_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        file_keywords = FileKeywords(worker_ssh)

        get_logger().log_test_case_step(f"Verify isolcpu_plugin.service file on {hostname}")
        validate_equals(file_keywords.validate_file_content("/lib/systemd/system/isolcpu_plugin.service", SERVICE_EXPECTED_LINES), True, f"Service file validation on {hostname}")

        get_logger().log_test_case_step(f"Verify isolcpu_plugin.conf file on {hostname}")
        validate_equals(file_keywords.validate_file_content("/etc/pmon.d/isolcpu_plugin.conf", CONF_EXPECTED_LINES), True, f"Config file validation on {hostname}")

        get_logger().log_test_case_step(f"Verify isolcpu_plugin.service is active on {hostname}")
        validate_equals(SystemCTLIsActiveKeywords(worker_ssh).is_active("isolcpu_plugin.service"), "active", f"Service status on {hostname}")
