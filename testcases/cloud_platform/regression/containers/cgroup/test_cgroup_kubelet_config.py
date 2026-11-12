"""Tests for kubelet configuration under cgroup v2.

Verifies /var/lib/kubelet/config.yaml has the cgroupDriver and cgroupRoot
expected for cgroup v2.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p2
def test_kubelet_cgroup_v2_config() -> None:
    """Verify kubelet cgroupDriver and cgroupRoot are set for cgroup v2.

    Test Steps:
        - Confirm the system is running cgroup v2
        - Validate kubelet cgroupDriver is systemd and cgroupRoot is /k8sinfra
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    cgroup_kw.validate_cgroup_v2()

    get_logger().log_test_case_step("Validate kubelet cgroupDriver and cgroupRoot")
    cgroup_kw.validate_kubelet_config()


@mark.p2
def test_kubelet_service_active() -> None:
    """Verify kubelet service is active.

    Test Steps:
        - Check the kubelet service is active
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Check kubelet service is active")
    cgroup_kw.validate_kubelet_active()
