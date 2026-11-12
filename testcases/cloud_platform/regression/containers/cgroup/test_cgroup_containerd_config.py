"""Tests for containerd configuration under cgroup v2.

Verifies /etc/containerd/config.toml has SystemdCgroup = true.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p2
def test_containerd_systemd_cgroup_enabled() -> None:
    """Verify containerd SystemdCgroup is enabled for cgroup v2.

    Test Steps:
        - Confirm the system is running cgroup v2
        - Validate containerd config.toml has SystemdCgroup = true
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    cgroup_kw.validate_cgroup_v2()

    get_logger().log_test_case_step("Validate containerd SystemdCgroup setting")
    cgroup_kw.validate_containerd_config()
