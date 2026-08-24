"""Test cgroup version switching via service parameter.

Detects current version and switches to the opposite (v1->v2 or v2->v1).
Validates the switch completed successfully with a single reboot.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.cgroup.cgroup_keywords import (
    CGROUP_V1,
    CGROUP_V2,
    CgroupKeywords,
)
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


@mark.p1
def test_switch_cgroup_version(request: FixtureRequest) -> None:
    """Switch cgroup version (v1->v2 if currently v1, else v2->v1).

    Steps:
        1. Detect current version
        2. system service-parameter-modify platform config cgroup_v2_enabled=<opposite>
        3. system service-parameter-apply platform
        4. system host-lock + system host-unlock (single reboot)
        5. Verify new cgroup version active
        6. Verify kubelet active and pods healthy

    Teardown:
        Revert to original cgroup version.
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    original = cgroup_kw.detect_cgroup_version()
    target_version = CGROUP_V2 if original == CGROUP_V1 else CGROUP_V1

    request.addfinalizer(lambda: cgroup_kw.revert_cgroup_version(original))

    logger.log_info(f"Current: {original}, switching to: {target_version}")
    cgroup_kw.switch_cgroup_version(target_version)

    # Reconnect after reboot
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    # Validate new version is active
    new_version = cgroup_kw.detect_cgroup_version()
    validate_equals(new_version, target_version, "cgroup version after switch")

    # Validate service parameter updated
    param_value = cgroup_kw.get_cgroup_service_parameter()
    expected_param = "true" if target_version == CGROUP_V2 else "false"
    validate_equals(param_value, expected_param, "cgroup_v2_enabled parameter after switch")

    # Validate kubelet and pods
    cgroup_kw.validate_kubelet_active()

    pods_kw = KubectlGetPodsKeywords(ssh)
    unhealthy_pods = pods_kw.get_unhealthy_pods()
    validate_equals(
        len(unhealthy_pods.get_pods()), 0, "no unhealthy pods after cgroup switch"
    )

    logger.log_info(f"Successfully switched from {original} to {target_version}")
