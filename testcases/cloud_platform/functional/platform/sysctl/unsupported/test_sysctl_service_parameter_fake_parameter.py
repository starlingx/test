"""Tests that the unsupported sysctl parameter "fake.parameter" cannot be added or modified.

This parameter is not supported for modification via the service parameter API.
"""

import pytest

from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from testcases.cloud_platform.functional.platform.sysctl.helper_sysctl_service_parameters import CONST, HelperSysctlServiceParameters

TEST_PARAMETER = SystemServiceParameterObject(service=CONST.SERVICE, section=CONST.SECTION, name="fake.parameter", value="fake value", modified_value="fake modified value")


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
