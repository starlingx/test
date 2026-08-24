"""Tests for kubelet configuration matching cgroup version.

Verifies /var/lib/kubelet/config.yaml has the correct cgroupDriver
and cgroupRoot for the detected cgroup version.
"""

from pytest import mark

from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p2
def test_kubelet_cgroup_driver_matches_version() -> None:
    """Verify kubelet cgroupDriver matches detected cgroup version.

    v1: cgroupfs
    v2: systemd
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    cgroup_kw.validate_kubelet_config()


@mark.p2
def test_kubelet_service_active() -> None:
    """Verify kubelet service is active."""
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    cgroup_kw.validate_kubelet_active()
