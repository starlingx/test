"""Tests for GRUB/boot.env cgroup v2 kernel parameters.

Verifies /proc/cmdline or boot.env contain the cgroup v2 kernel parameters.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.cgroup.cgroup_keywords import V2_EXPECTED_VALUES, CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p2
def test_cgroup_v2_kernel_params_in_cmdline_or_boot_env() -> None:
    """Verify cgroup v2 kernel params are present in /proc/cmdline or boot.env.

    On trixie (Debian 13+), cgroup v2 is kernel-native and the explicit
    unified_cgroup_hierarchy param may not appear in /proc/cmdline but
    is present in boot.env. The keyword checks both locations.

    Expected params: systemd.unified_cgroup_hierarchy=1, cgroup_no_v1=all

    Test Steps:
        - Confirm the system is running cgroup v2
        - Validate the cgroup v2 kernel params in cmdline or boot.env
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    cgroup_kw.validate_cgroup_v2()

    get_logger().log_test_case_step("Validate cgroup v2 kernel params in cmdline or boot.env")
    cgroup_kw.validate_kernel_cmdline()


@mark.p2
def test_boot_env_has_cgroup_v2_kernel_params() -> None:
    """Verify /boot/efi/EFI/BOOT/boot.env contains the cgroup v2 kernel params.

    Test Steps:
        - Confirm the system is running cgroup v2
        - Read boot.env
        - Validate boot.env has the cgroup v2 kernel params
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    CgroupKeywords(ssh).validate_cgroup_v2()

    get_logger().log_test_case_step("Read boot.env")
    file_keywords = FileKeywords(ssh)
    output = file_keywords.read_file_with_sudo("/boot/efi/EFI/BOOT/boot.env")
    boot_env = "\n".join(output) if isinstance(output, list) else output

    get_logger().log_test_case_step("Validate boot.env has the cgroup v2 kernel params")
    for param in (V2_EXPECTED_VALUES["kernel_hierarchy"], V2_EXPECTED_VALUES["kernel_no_v1"]):
        validate_str_contains(boot_env, param, f"boot.env has {param}")
