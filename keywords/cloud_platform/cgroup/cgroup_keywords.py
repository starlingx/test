"""Keywords for cgroup version detection and validation."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

# Cgroup version constants
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


class CgroupKeywords(BaseKeyword):
    """Keywords for cgroup version detection and configuration validation.

    Provides methods to detect cgroup version, read service parameters,
    validate kernel parameters, kubelet config, and containerd config.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target host.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize cgroup keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def detect_cgroup_version(self) -> str:
        """Detect current cgroup version from filesystem type.

        Runs: stat -f -c %T /sys/fs/cgroup

        Returns:
            str: CGROUP_V1 or CGROUP_V2.
        """
        output = self.ssh_connection.send("stat -f -c %T /sys/fs/cgroup")
        self.validate_success_return_code(self.ssh_connection)
        fs_type = output.strip() if isinstance(output, str) else output[0].strip()
        if fs_type == "cgroup2fs":
            return CGROUP_V2
        return CGROUP_V1

    def get_cgroup_service_parameter(self) -> str:
        """Get current cgroup_v2_enabled service parameter value.

        Runs: system service-parameter-list --service platform --section config

        Returns:
            str: 'true' or 'false'.
        """
        sp_keywords = SystemServiceParameterKeywords(self.ssh_connection)
        params = sp_keywords.list_service_parameters(
            service="platform", section="config"
        )
        for param in params.get_parameters():
            if param.get_name() == "cgroup_v2_enabled":
                return param.get_value()
        return "false"

    def get_expected_values(self, version: str = None) -> dict:
        """Get expected configuration values for a cgroup version.

        Args:
            version (str): CGROUP_V1 or CGROUP_V2. Defaults to current detected version.

        Returns:
            dict: Expected values for the version.
        """
        if version is None:
            version = self.detect_cgroup_version()
        return EXPECTED_VALUES[version]

    def modify_cgroup_service_parameter(self, enable_v2: bool) -> None:
        """Modify and apply the cgroup_v2_enabled service parameter.

        Runs:
            system service-parameter-modify platform config cgroup_v2_enabled=<value>
            system service-parameter-apply platform

        Args:
            enable_v2 (bool): True to set cgroup_v2_enabled=true, False for false.
        """
        target_value = "true" if enable_v2 else "false"
        get_logger().log_info(f"Setting cgroup_v2_enabled={target_value}")

        sp_keywords = SystemServiceParameterKeywords(self.ssh_connection)
        sp_keywords.modify_service_parameter(
            "platform", "config", "cgroup_v2_enabled", target_value
        )
        sp_keywords.apply_service_parameters("platform")

    def validate_kernel_cmdline(self) -> None:
        """Validate cgroup kernel params in /proc/cmdline or boot.env.

        On trixie (Debian 13+), cgroup v2 is the kernel default and the
        explicit unified_cgroup_hierarchy param may not appear in
        /proc/cmdline but is present in boot.env. Validates the param
        exists in at least one location.

        Runs: cat /proc/cmdline; cat /boot/efi/EFI/BOOT/boot.env

        Validates:
            v1: systemd.unified_cgroup_hierarchy=0 in cmdline or boot.env
            v2: systemd.unified_cgroup_hierarchy=1 and cgroup_no_v1=all
        """
        logger = get_logger()
        output = self.ssh_connection.send("cat /proc/cmdline")
        self.validate_success_return_code(self.ssh_connection)
        cmdline = output.strip() if isinstance(output, str) else output[0].strip()

        boot_env_output = self.ssh_connection.send_as_sudo(
            "cat /boot/efi/EFI/BOOT/boot.env"
        )
        boot_env = boot_env_output if isinstance(boot_env_output, str) else "\n".join(boot_env_output)

        combined = cmdline + "\n" + boot_env
        version = self.detect_cgroup_version()
        expected = self.get_expected_values(version)

        logger.log_info(f"Validating kernel cgroup params for {version}")
        validate_str_contains(
            combined,
            expected["kernel_hierarchy"],
            f"cgroup param {expected['kernel_hierarchy']} in cmdline or boot.env",
        )
        if version == CGROUP_V2:
            validate_str_contains(
                combined,
                expected["kernel_no_v1"],
                f"cgroup param {expected['kernel_no_v1']} in cmdline or boot.env",
            )

    def validate_kubelet_config(self) -> None:
        """Validate kubelet config.yaml has correct cgroup settings.

        Runs: cat /var/lib/kubelet/config.yaml

        Validates:
            cgroupDriver matches version (cgroupfs for v1, systemd for v2)
            cgroupRoot is /k8sinfra
        """
        logger = get_logger()
        output = self.ssh_connection.send_as_sudo("cat /var/lib/kubelet/config.yaml")
        self.validate_success_return_code(self.ssh_connection)
        config_content = output if isinstance(output, str) else "\n".join(output)
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
        """Validate containerd config.toml has correct SystemdCgroup.

        Runs: cat /etc/containerd/config.toml

        Validates:
            SystemdCgroup = false (v1) or SystemdCgroup = true (v2)
        """
        logger = get_logger()
        output = self.ssh_connection.send_as_sudo("cat /etc/containerd/config.toml")
        self.validate_success_return_code(self.ssh_connection)
        config_content = output if isinstance(output, str) else "\n".join(output)
        version = self.detect_cgroup_version()
        expected = self.get_expected_values(version)

        logger.log_info(f"Validating containerd config for {version}")
        expected_line = f"SystemdCgroup = {expected['containerd_systemd_cgroup']}"
        validate_str_contains(
            config_content,
            expected_line,
            f"containerd config contains '{expected_line}'",
        )

    def validate_kubelet_active(self) -> None:
        """Validate kubelet service is active.

        Runs: systemctl is-active kubelet
        """
        output = self.ssh_connection.send_as_sudo("systemctl is-active kubelet")
        status = output.strip() if isinstance(output, str) else output[0].strip()
        validate_equals(status, "active", "kubelet service is active")


    def switch_cgroup_version(self, target_version: str) -> None:
        """Switch cgroup to target version via service parameter + lock/unlock.

        If already on target version, does nothing. Otherwise modifies the
        cgroup_v2_enabled service parameter and performs lock/unlock cycle.
        After lock/unlock the SSH connection on this instance is stale -
        caller must reconnect via LabConnectionKeywords.

        Args:
            target_version (str): CGROUP_V1 or CGROUP_V2.
        """
        current = self.detect_cgroup_version()
        if current == target_version:
            get_logger().log_info(f"Already on {target_version}, no switch needed")
            return

        get_logger().log_info(f"Switching cgroup from {current} to {target_version}")
        enable_v2 = target_version == CGROUP_V2
        self.modify_cgroup_service_parameter(enable_v2)
        lock_kw = SystemHostLockKeywords(self.ssh_connection)
        lock_kw.lock_unlock_hosts()

    def revert_cgroup_version(self, original_version: str) -> None:
        """Revert cgroup version to original if changed.

        Reconnects SSH internally. Safe to call even if version unchanged.

        Args:
            original_version (str): The version to revert to (CGROUP_V1 or CGROUP_V2).
        """
        get_logger().log_teardown_step(f"Revert cgroup version to {original_version}")
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        self.ssh_connection = ssh
        current = self.detect_cgroup_version()
        if current != original_version:
            enable_v2 = original_version == CGROUP_V2
            self.modify_cgroup_service_parameter(enable_v2)
            lock_kw = SystemHostLockKeywords(ssh)
            lock_kw.lock_unlock_hosts()
