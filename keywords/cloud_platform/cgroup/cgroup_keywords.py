"""Keywords for cgroup (v2 only) detection and validation.

As of the 27.03 release only the cgroup v2 unified hierarchy is supported.
These keywords validate that a system is correctly configured for cgroup v2.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.base_keyword import BaseKeyword

# Cgroup version constants. As of 27.03 only v2 is supported, but detection can
# still report v1 so callers can detect it and fail with a clear message.
CGROUP_V1 = "v1"
CGROUP_V2 = "v2"

# Expected configuration values on a cgroup v2 system.
V2_EXPECTED_VALUES = {
    "filesystem_type": "cgroup2fs",
    "kernel_hierarchy": "systemd.unified_cgroup_hierarchy=1",
    "kernel_no_v1": "cgroup_no_v1=all",
    "kubelet_cgroup_driver": "systemd",
    "kubelet_cgroup_root": "/k8sinfra",
    "containerd_systemd_cgroup": "true",
    # kubelet cgroupRoot is /k8sinfra (systemd slice k8sinfra.slice), but on the cgroup v2
    # unified hierarchy pods and platform containers are placed under the k8sinfra_stx.slice
    # tree, so process cpuset paths are rooted there
    # (e.g. /k8sinfra_stx.slice/k8sinfra_stx-kubepods.slice/...).
    "cgroup_root_prefix": "k8sinfra_stx.slice",
}


class CgroupKeywords(BaseKeyword):
    """Keywords for cgroup v2 detection and configuration validation.

    Provides methods to confirm the cgroup v2 unified hierarchy and to
    validate kernel parameters, kubelet config, and containerd config.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize cgroup keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def detect_cgroup_version(self) -> str:
        """Detect the cgroup version from the /sys/fs/cgroup filesystem type.

        Runs: stat -f -c %T /sys/fs/cgroup

        Returns:
            str: CGROUP_V2 when the unified hierarchy (cgroup2fs) is mounted,
                otherwise CGROUP_V1.
        """
        output = self.ssh_connection.send("stat -f -c %T /sys/fs/cgroup")
        self.validate_success_return_code(self.ssh_connection)
        fs_type = output.strip() if isinstance(output, str) else output[0].strip()
        if fs_type == V2_EXPECTED_VALUES["filesystem_type"]:
            return CGROUP_V2
        return CGROUP_V1

    def validate_cgroup_v2(self) -> None:
        """Validate the system is running the cgroup v2 unified hierarchy.

        Fails with a clear message when v1 is detected, so callers do not hit a
        confusing configuration mismatch later.

        Runs: stat -f -c %T /sys/fs/cgroup
        """
        validate_equals(self.detect_cgroup_version(), CGROUP_V2, "system is running cgroup v2")

    def validate_kernel_cmdline(self) -> None:
        """Validate cgroup v2 kernel params in /proc/cmdline or boot.env.

        On trixie (Debian 13+), cgroup v2 is the kernel default and the
        explicit unified_cgroup_hierarchy param may not appear in
        /proc/cmdline but is present in boot.env. Validates the params
        exist in at least one location.

        Runs: cat /proc/cmdline; cat /boot/efi/EFI/BOOT/boot.env
        """
        output = self.ssh_connection.send("cat /proc/cmdline")
        self.validate_success_return_code(self.ssh_connection)
        cmdline = output.strip() if isinstance(output, str) else output[0].strip()

        boot_env_output = self.ssh_connection.send_as_sudo("cat /boot/efi/EFI/BOOT/boot.env")
        boot_env = boot_env_output if isinstance(boot_env_output, str) else "\n".join(boot_env_output)

        combined = cmdline + "\n" + boot_env

        get_logger().log_info("Validating kernel cgroup v2 params")
        for param in (V2_EXPECTED_VALUES["kernel_hierarchy"], V2_EXPECTED_VALUES["kernel_no_v1"]):
            validate_str_contains(combined, param, f"cgroup param {param} in cmdline or boot.env")

    def validate_kubelet_config(self) -> None:
        """Validate kubelet config.yaml has correct cgroup v2 settings.

        Runs: cat /var/lib/kubelet/config.yaml

        Validates:
            cgroupDriver is systemd
            cgroupRoot is /k8sinfra
        """
        output = self.ssh_connection.send_as_sudo("cat /var/lib/kubelet/config.yaml")
        self.validate_success_return_code(self.ssh_connection)
        config_content = output if isinstance(output, str) else "\n".join(output)

        get_logger().log_info("Validating kubelet config for cgroup v2")
        validate_str_contains(
            config_content,
            f"cgroupDriver: {V2_EXPECTED_VALUES['kubelet_cgroup_driver']}",
            f"kubelet cgroupDriver is {V2_EXPECTED_VALUES['kubelet_cgroup_driver']}",
        )
        validate_str_contains(
            config_content,
            f"cgroupRoot: {V2_EXPECTED_VALUES['kubelet_cgroup_root']}",
            f"kubelet cgroupRoot is {V2_EXPECTED_VALUES['kubelet_cgroup_root']}",
        )

    def validate_containerd_config(self) -> None:
        """Validate containerd config.toml has SystemdCgroup = true.

        Runs: cat /etc/containerd/config.toml
        """
        output = self.ssh_connection.send_as_sudo("cat /etc/containerd/config.toml")
        self.validate_success_return_code(self.ssh_connection)
        config_content = output if isinstance(output, str) else "\n".join(output)

        get_logger().log_info("Validating containerd config for cgroup v2")
        expected_line = f"SystemdCgroup = {V2_EXPECTED_VALUES['containerd_systemd_cgroup']}"
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
