"""Tests for cgroup version detection and baseline validation.

Verifies the system correctly reports its cgroup version and that the
service parameter matches the runtime state.
"""

import pytest

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains
from testcases.cloud_platform.functional.platform.cgroup.helper_cgroup import (
    CGROUP_V1,
    CGROUP_V2,
    HelperCgroup,
)


@pytest.fixture
def cgroup_helper():
    """Provide a configured HelperCgroup instance."""
    helper = HelperCgroup()
    helper.setup_method()
    return helper


def test_detect_cgroup_version(cgroup_helper) -> None:
    """Verify cgroup filesystem type is either tmpfs (v1) or cgroup2fs (v2)."""
    version = cgroup_helper.detect_cgroup_version()
    validate_list_contains(
        version,
        [CGROUP_V1, CGROUP_V2],
        "cgroup version is v1 or v2",
    )
    get_logger().log_info(f"System is running cgroup {version}")


def test_cgroup_service_parameter_matches_runtime(cgroup_helper) -> None:
    """Verify cgroup_v2_enabled service parameter matches runtime state."""
    version = cgroup_helper.detect_cgroup_version()
    param_value = cgroup_helper.get_cgroup_service_parameter()

    if version == CGROUP_V2:
        validate_equals(
            param_value,
            "true",
            "cgroup_v2_enabled parameter is 'true' when v2 is active",
        )
    else:
        validate_equals(
            param_value,
            "false",
            "cgroup_v2_enabled parameter is 'false' when v1 is active",
        )
