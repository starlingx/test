"""Tests for kubelet configuration matching cgroup version.

Verifies /var/lib/kubelet/config.yaml has the correct cgroupDriver
and cgroupRoot for the detected cgroup version.
"""

from testcases.cloud_platform.functional.platform.cgroup.helper_cgroup import HelperCgroup


def test_kubelet_cgroup_driver_matches_version():
    """Verify kubelet cgroupDriver matches detected cgroup version.

    v1: cgroupfs
    v2: systemd
    """
    helper = HelperCgroup()
    helper.setup_method()
    helper.validate_kubelet_config()


def test_kubelet_service_active():
    """Verify kubelet service is active."""
    helper = HelperCgroup()
    helper.setup_method()
    helper.validate_kubelet_active()
