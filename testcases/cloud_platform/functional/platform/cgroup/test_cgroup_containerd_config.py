"""Tests for containerd configuration matching cgroup version.

Verifies /etc/containerd/config.toml has the correct SystemdCgroup setting.
"""

from testcases.cloud_platform.functional.platform.cgroup.helper_cgroup import HelperCgroup


def test_containerd_systemd_cgroup_matches_version():
    """Verify containerd SystemdCgroup setting matches detected cgroup version.

    v1: SystemdCgroup = false
    v2: SystemdCgroup = true
    """
    helper = HelperCgroup()
    helper.setup_method()
    helper.validate_containerd_config()
