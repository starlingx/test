"""Tests for GRUB/boot.env kernel parameters matching cgroup version.

Verifies /proc/cmdline or boot.env contain the correct cgroup kernel
parameters for the detected version.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.cgroup.cgroup_keywords import CGROUP_V2, CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p2
def test_grub_params_match_cgroup_version() -> None:
    """Verify cgroup kernel params present in /proc/cmdline or boot.env.

    On trixie (Debian 13+), cgroup v2 is kernel-native and the explicit
    unified_cgroup_hierarchy param may not appear in /proc/cmdline but
    is present in boot.env. The keyword checks both locations.

    v1: systemd.unified_cgroup_hierarchy=0
    v2: systemd.unified_cgroup_hierarchy=1, cgroup_no_v1=all
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    cgroup_kw.validate_kernel_cmdline()


@mark.p2
def test_boot_env_matches_cgroup_version() -> None:
    """Verify /boot/efi/EFI/BOOT/boot.env contains correct cgroup kernel params."""
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    version = cgroup_kw.detect_cgroup_version()

    file_keywords = FileKeywords(ssh)
    output = file_keywords.read_file_with_sudo("/boot/efi/EFI/BOOT/boot.env")
    boot_env = "\n".join(output) if isinstance(output, list) else output

    logger.log_info(f"Validating boot.env for {version}")

    if version == CGROUP_V2:
        validate_str_contains(boot_env, "unified_cgroup_hierarchy=1", "boot.env has unified_cgroup_hierarchy=1")
        validate_str_contains(boot_env, "cgroup_no_v1=all", "boot.env has cgroup_no_v1=all")
    else:
        validate_str_contains(boot_env, "unified_cgroup_hierarchy=0", "boot.env has unified_cgroup_hierarchy=0")
