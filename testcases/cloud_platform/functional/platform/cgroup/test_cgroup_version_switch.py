"""Test cgroup version switching via service parameter.

Detects current version and switches to the opposite (v1→v2 or v2→v1).
Validates the switch completed successfully with a single reboot.
"""

import pytest

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from testcases.cloud_platform.functional.platform.cgroup.helper_cgroup import (
    CGROUP_V1,
    CGROUP_V2,
    HelperCgroup,
)


def test_switch_cgroup_version(request: pytest.FixtureRequest) -> None:
    """Switch cgroup version (v1→v2 if currently v1, else v2→v1).

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
    helper = HelperCgroup()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    logger = get_logger()
    original = helper.detect_cgroup_version()
    target_v2 = original == CGROUP_V1
    target_version = CGROUP_V2 if target_v2 else CGROUP_V1

    logger.log_info(f"Current: {original}, switching to: {target_version}")

    # Switch
    helper.switch_cgroup_version(enable_v2=target_v2)

    # Validate new version is active
    new_version = helper.detect_cgroup_version()
    validate_equals(new_version, target_version, "cgroup version after switch")

    # Validate service parameter updated
    param_value = helper.get_cgroup_service_parameter()
    expected_param = "true" if target_v2 else "false"
    validate_equals(param_value, expected_param, "cgroup_v2_enabled parameter after switch")

    # Validate kubelet and pods
    helper.validate_kubelet_active()
    helper.validate_pods_healthy()

    logger.log_info(f"Successfully switched from {original} to {target_version}")
