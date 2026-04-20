"""Tests that the unsupported sysctl parameter "kernel.random.boot_id" cannot be added or modified.

This is a read-only kernel parameter.
"""

import pytest

from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from testcases.cloud_platform.functional.platform.sysctl.helper_sysctl_service_parameters import CONST, HelperSysctlServiceParameters

TEST_PARAMETER = SystemServiceParameterObject(service=CONST.SERVICE, section=CONST.SECTION, name="kernel.random.boot_id", value="b1a048d3-6dc2-4974-b46c-90b3c040c0e4", modified_value="b1a048d3-6dc2-4974-b46c-90b3c040c0e4")


def test_add_service_parameter_fails(request: pytest.FixtureRequest) -> None:
    """Test that adding the unsupported sysctl parameter is rejected."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_fails(TEST_PARAMETER)


def test_modify_service_parameter_fails(request: pytest.FixtureRequest) -> None:
    """Test that modifying the unsupported sysctl parameter is rejected."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.modify_service_parameter_fails(TEST_PARAMETER)
