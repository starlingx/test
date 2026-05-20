"""Helper class for cgroup v2 functional tests.

Provides detection, validation, and switch logic for cgroup v1/v2 testing.
Follows the same setup/teardown pattern as HelperSysctlServiceParameters.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

# Expected values per cgroup version
CGROUP_V1 = "v1"
CGROUP_V2 = "v2"

EXPECTED_VALUES = {
    CGROUP_V1: {
        "filesystem_type": "tmpfs",
        "service_param_value": "false",
        "kernel_hierarchy": "systemd.unified_cgroup_hierarchy=0",
        "kubelet_cgroup_driver": "cgroupfs",
        "kubelet_cgroup_root": "/k8sinfra",
        "containerd_systemd_cgroup": "false",
        "cgroup_root_prefix": "/k8sinfra/",
    },
    CGROUP_V2: {
        "filesystem_type": "cgroup2fs",
        "service_param_value": "true",
        "kernel_hierarchy": "systemd.unified_cgroup_hierarchy=1",
        "kernel_no_v1": "cgroup_no_v1=all",
        "kubelet_cgroup_driver": "systemd",
        "kubelet_cgroup_root": "/k8sinfra",
        "containerd_systemd_cgroup": "true",
        "cgroup_root_prefix": "/k8sinfra/",
    },
}


class HelperCgroup:
    """Helper class for cgroup v1/v2 functional tests."""

    def __init__(self) -> None:
        self.ssh_connection: SSHConnection = None
        self.original_version: str = None
        self.hostname: str = None

    def setup_method(self) -> None:
        """Set up SSH connection and record original cgroup version."""
        self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        self.hostname = SystemHostListKeywords(
            self.ssh_connection
        ).get_active_controller().get_host_name()
        self.original_version = self.detect_cgroup_version()
        get_logger().log_info(f"Detected cgroup version: {self.original_version}")

    def teardown_method(self) -> None:
        """Revert to original cgroup version if changed."""
        if self.original_version is None:
            return
        current = self.detect_cgroup_version()
        if current != self.original_version:
            get_logger().log_info(
                f"Reverting cgroup from {current} to {self.original_version}"
            )
            enable_v2 = self.original_version == CGROUP_V2
            self.switch_cgroup_version(enable_v2)

    def detect_cgroup_version(self) -> str:
        """Detect current cgroup version from filesystem type.

        Returns:
            str: CGROUP_V1 or CGROUP_V2
        """
        output = self.ssh_connection.send("stat -f -c %T /sys/fs/cgroup")
        fs_type = output.strip() if isinstance(output, str) else output[0].strip()
        if fs_type == "cgroup2fs":
            return CGROUP_V2
        return CGROUP_V1

    def get_cgroup_service_parameter(self) -> str:
        """Get current cgroup_v2_enabled service parameter value.

        Returns:
            str: 'true' or 'false'
        """
        sp_keywords = SystemServiceParameterKeywords(self.ssh_connection)
        params = sp_keywords.list_service_parameters(
            service="platform", section="config"
        )
        for param in params.get_parameters():
            if param.get_name() == "cgroup_v2_enabled":
                return param.get_value()
        return "false"

    def switch_cgroup_version(self, enable_v2: bool) -> None:
        """Switch cgroup version via service parameter + lock/unlock.

        Modifies the cgroup_v2_enabled service parameter and performs a
        lock/unlock cycle (handles both simplex and non-simplex).

        Args:
            enable_v2: True to switch to v2, False to switch to v1.
        """

        logger = get_logger()
        target_value = "true" if enable_v2 else "false"
        target_version = CGROUP_V2 if enable_v2 else CGROUP_V1

        logger.log_info(
            f"Switching cgroup to {target_version} "
            f"(cgroup_v2_enabled={target_value})"
        )

        sp_keywords = SystemServiceParameterKeywords(self.ssh_connection)
        sp_keywords.modify_service_parameter(
            "platform", "config", "cgroup_v2_enabled", target_value
        )
        sp_keywords.apply_service_parameters("platform")

        lock_keywords = SystemHostLockKeywords(self.ssh_connection)
        lock_keywords.lock_unlock_hosts()

        # Reconnect after lock/unlock cycle
        self.ssh_connection = (
            LabConnectionKeywords().get_active_controller_ssh()
        )

        logger.log_info(
            f"Host {self.hostname} is unlocked/enabled/available"
        )

    def get_expected_values(self, version: str = None) -> dict:
        """Get expected configuration values for a cgroup version.

        Args:
            version: CGROUP_V1 or CGROUP_V2. Defaults to current detected
                version.

        Returns:
            dict: Expected values for the version.
        """
        if version is None:
            version = self.detect_cgroup_version()
        return EXPECTED_VALUES[version]

    def validate_kernel_cmdline(self) -> None:
        """Validate /proc/cmdline contains correct cgroup kernel params."""
        logger = get_logger()
        output = self.ssh_connection.send("cat /proc/cmdline")
        cmdline = (
            output.strip() if isinstance(output, str) else output[0].strip()
        )
        version = self.detect_cgroup_version()
        expected = self.get_expected_values(version)

        logger.log_info(f"Validating kernel cmdline for {version}")
        validate_str_contains(
            cmdline,
            expected["kernel_hierarchy"],
            f"kernel cmdline contains {expected['kernel_hierarchy']}",
        )
        if version == CGROUP_V2:
            validate_str_contains(
                cmdline,
                expected["kernel_no_v1"],
                f"kernel cmdline contains {expected['kernel_no_v1']}",
            )

    def validate_kubelet_config(self) -> None:
        """Validate kubelet config.yaml has correct cgroup settings."""
        logger = get_logger()
        output = self.ssh_connection.send_as_sudo(
            "cat /var/lib/kubelet/config.yaml"
        )
        config_content = (
            output if isinstance(output, str) else "\n".join(output)
        )
        version = self.detect_cgroup_version()
        expected = self.get_expected_values(version)

        logger.log_info(f"Validating kubelet config for {version}")
        validate_str_contains(
            config_content,
            f"cgroupDriver: {expected['kubelet_cgroup_driver']}",
            f"kubelet cgroupDriver is {expected['kubelet_cgroup_driver']}",
        )
        validate_str_contains(
            config_content,
            f"cgroupRoot: {expected['kubelet_cgroup_root']}",
            f"kubelet cgroupRoot is {expected['kubelet_cgroup_root']}",
        )

    def validate_containerd_config(self) -> None:
        """Validate containerd config.toml has correct SystemdCgroup."""
        logger = get_logger()
        output = self.ssh_connection.send_as_sudo(
            "cat /etc/containerd/config.toml"
        )
        config_content = (
            output if isinstance(output, str) else "\n".join(output)
        )
        version = self.detect_cgroup_version()
        expected = self.get_expected_values(version)

        logger.log_info(f"Validating containerd config for {version}")
        expected_line = (
            f"SystemdCgroup = {expected['containerd_systemd_cgroup']}"
        )
        validate_str_contains(
            config_content,
            expected_line,
            f"containerd config contains '{expected_line}'",
        )

    def validate_kubelet_active(self) -> None:
        """Validate kubelet service is active."""
        output = self.ssh_connection.send_as_sudo(
            "systemctl is-active kubelet"
        )
        status = (
            output.strip() if isinstance(output, str) else output[0].strip()
        )
        validate_equals(
            status, "active", "kubelet service is active"
        )

    def validate_pods_healthy(self) -> None:
        """Validate no pods in non-Running/Completed state."""
        output = self.ssh_connection.send_as_sudo(
            "kubectl --kubeconfig=/etc/kubernetes/admin.conf get pods -A "
            "--field-selector=status.phase!=Running,status.phase!=Succeeded "
            "--no-headers 2>/dev/null | wc -l"
        )
        count = (
            output.strip() if isinstance(output, str) else output[0].strip()
        )
        validate_equals(
            count, "0", "no pods in non-Running/Succeeded state"
        )
