"""Tests adding and modifying the supported sysctl parameter "net.core.netdev_max_backlog".

Validates the parameter across active controller, standby controller, compute nodes,
and storage nodes, including swact, lock/unlock, and Redfish reboot scenarios.
"""

import pytest
from pytest import mark

from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from testcases.cloud_platform.functional.platform.sysctl.helper_sysctl_service_parameters import CONST, HelperSysctlServiceParameters

TEST_PARAMETER = SystemServiceParameterObject(service=CONST.SERVICE, section=CONST.SECTION, name="net.core.netdev_max_backlog", value="5", modified_value="10")


def test_add_service_parameter_active_controller_success(request: pytest.FixtureRequest) -> None:
    """Test that adding the sysctl parameter succeeds on the active controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_active_controller_success(TEST_PARAMETER)


def test_modify_service_parameter_active_controller_success(request: pytest.FixtureRequest) -> None:
    """Test that modifying the sysctl parameter succeeds on the active controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.modify_service_parameter_active_controller_success(TEST_PARAMETER)


@mark.lab_has_standby_controller
def test_add_service_parameter_standby_controller_success(request: pytest.FixtureRequest) -> None:
    """Test that adding the sysctl parameter succeeds on the standby controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_standby_controller_success(TEST_PARAMETER)


@mark.lab_has_standby_controller
def test_add_service_parameter_and_swact_success(request: pytest.FixtureRequest) -> None:
    """Test that the sysctl parameter persists after a host swact."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_and_swact_success(TEST_PARAMETER)


@mark.lab_has_standby_controller
def test_modify_service_parameter_standby_controller_success(request: pytest.FixtureRequest) -> None:
    """Test that modifying the sysctl parameter succeeds on the standby controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.modify_service_parameter_standby_controller_success(TEST_PARAMETER)


@mark.lab_has_standby_controller
def test_add_service_parameter_and_lock_unlock_standby_success(request: pytest.FixtureRequest) -> None:
    """Test that the sysctl parameter persists after lock/unlock of the standby controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_and_lock_unlock_standby_success(TEST_PARAMETER)


@mark.lab_is_virtual
@mark.lab_has_bmc_redfish
@mark.lab_has_standby_controller
def test_add_service_parameter_redfish_reboot_standby_virtual_lab_success(request: pytest.FixtureRequest) -> None:
    """Test that the sysctl parameter persists after a Redfish power-cycle of the standby controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_redfish_reboot_standby_virtual_lab_success(TEST_PARAMETER)


@mark.lab_has_compute
def test_add_service_parameter_compute_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that adding the sysctl parameter succeeds on all compute nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_compute_nodes_success(TEST_PARAMETER)


@mark.lab_has_compute
def test_modify_service_parameter_compute_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that modifying the sysctl parameter succeeds on all compute nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.modify_service_parameter_compute_nodes_success(TEST_PARAMETER)


@mark.lab_has_storage
def test_add_service_parameter_storage_nodes(request: pytest.FixtureRequest) -> None:
    """Test that adding the sysctl parameter succeeds on all storage nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_storage_nodes_success(TEST_PARAMETER)


@mark.lab_has_storage
def test_modify_service_parameter_storage_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that modifying the sysctl parameter succeeds on all storage nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.modify_service_parameter_storage_nodes_success(TEST_PARAMETER)
