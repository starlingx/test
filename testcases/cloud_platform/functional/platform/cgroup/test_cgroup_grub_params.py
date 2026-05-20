"""Tests for GRUB/boot.env kernel parameters matching cgroup version.

Verifies /proc/cmdline and boot.env contain the correct cgroup kernel
parameters for the detected version.
"""

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from testcases.cloud_platform.functional.platform.cgroup.helper_cgroup import (
    CGROUP_V2, HelperCgroup,
)


def test_grub_params_match_cgroup_version():
    """Verify /proc/cmdline contains correct params for detected version.

    v1: systemd.unified_cgroup_hierarchy=0
    v2: systemd.unified_cgroup_hierarchy=1, cgroup_no_v1=all
    """
    helper = HelperCgroup()
    helper.setup_method()
    helper.validate_kernel_cmdline()


def test_boot_env_matches_cgroup_version():
    """Verify /boot/efi/EFI/BOOT/boot.env contains correct cgroup kernel params."""

    helper = HelperCgroup()
    helper.setup_method()

    logger = get_logger()
    version = helper.detect_cgroup_version()

    output = helper.ssh_connection.send_as_sudo("cat /boot/efi/EFI/BOOT/boot.env")
    boot_env = output if isinstance(output, str) else "\n".join(output)

    logger.log_info(f"Validating boot.env for {version}")

    if version == CGROUP_V2:
        validate_str_contains(boot_env, "unified_cgroup_hierarchy=1", "boot.env has unified_cgroup_hierarchy=1")
        validate_str_contains(boot_env, "cgroup_no_v1=all", "boot.env has cgroup_no_v1=all")
    else:
        validate_str_contains(boot_env, "unified_cgroup_hierarchy=0", "boot.env has unified_cgroup_hierarchy=0")
