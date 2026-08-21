"""Tests for containerd configuration matching cgroup version.

Verifies /etc/containerd/config.toml has the correct SystemdCgroup setting.
"""

from pytest import mark

from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p2
def test_containerd_systemd_cgroup_matches_version() -> None:
    """Verify containerd SystemdCgroup setting matches detected cgroup version.

    v1: SystemdCgroup = false
    v2: SystemdCgroup = true
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    cgroup_kw.validate_containerd_config()
