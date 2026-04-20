"""Tests adding multiple sysctl service parameters at once across various node types.

Validates bulk add operations on the active controller, standby controller,
compute nodes, and storage nodes, including swact scenarios.
"""

import json

import pytest
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sysctl.sysctl_keywords import SysctlKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from testcases.cloud_platform.functional.platform.sysctl.helper_sysctl_service_parameters import CONST, TESTDATA, HelperSysctlServiceParameters


def _get_test_parameters(supported: bool) -> dict[str, SystemServiceParameterObject]:
    """Get a collection of test parameters.

    Filters the TESTDATA based on whether or not the parameters are supported.

    Args:
        supported (bool): If True returns only supported parameters,
                   if False returns only unsupported parameters.

    Returns:
        dict[str, SystemServiceParameterObject]: A dictionary of parameters.
    """
    parameters: dict[str, SystemServiceParameterObject] = {}
    for name, add_value, _supported, modify_value in TESTDATA:
        if supported == _supported:
            obj = SystemServiceParameterObject(service=CONST.SERVICE, section=CONST.SECTION, name=name, value=add_value, modified_value=modify_value)
            parameters[name] = obj
    return parameters


def test_add_multiple_service_parameters_success(request: pytest.FixtureRequest) -> None:
    """Test that adding all supported sysctl parameters at once succeeds on the active controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    sysctl_keywords = SysctlKeywords(helper.ssh_oam_connection)
    parameters = _get_test_parameters(supported=True)
    parameter_names: list[str] = [*parameters]
    expected_values: dict[str, str] = {parameter.get_name(): parameter.get_value() for parameter in parameters.values()}

    def get_sysctl_values():
        return sysctl_keywords.get_multiple_sysctl_values(parameter_names)

    current_values = sysctl_keywords.get_multiple_sysctl_values(parameter_names)
    get_logger().log_info(f"Current Values on Active Controller are: \n{json.dumps(current_values, indent=2)}")

    parameters_list = [f'{parameter.get_name()}="{parameter.get_value()}"' for parameter in parameters.values()]
    parameters_str = " ".join(parameters_list)
    added_parameters = helper.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str).get_parameters()
    expected_count = len(parameters)
    observed_count = len(added_parameters)
    validate_equals(observed_value=observed_count, expected_value=expected_count, validation_description="All parameters were added")
    listed_parameters = helper.service_parameter_keywords.list_service_parameters(
        service=CONST.SERVICE,
        section=CONST.SECTION,
    ).get_parameters()
    listed_count = len(listed_parameters)
    validate_equals(observed_value=listed_count, expected_value=expected_count, validation_description="All parameters were added and listed")
    validate_equals_with_retry(
        function_to_execute=get_sysctl_values,
        expected_value=expected_values,
        validation_description="Sysctl values on Active Controller should match",
        timeout=45,
    )


@mark.lab_has_standby_controller
def add_multiple_service_parameters_and_swact_success(request: pytest.FixtureRequest) -> None:
    """Test that all supported sysctl parameters persist after two consecutive swacts."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    sysctl_keywords = SysctlKeywords(helper.ssh_oam_connection)
    parameters = _get_test_parameters(supported=True)
    parameter_names: list[str] = [*parameters]
    expected_values: dict[str, str] = {parameter.get_name(): parameter.get_value() for parameter in parameters.values()}

    def get_sysctl_values():
        return sysctl_keywords.get_multiple_sysctl_values(parameter_names)

    current_values = sysctl_keywords.get_multiple_sysctl_values(parameter_names)
    get_logger().log_info(f"Current Values on Active Controller are: \n{json.dumps(current_values, indent=2)}")

    parameters_list = [f'{parameter.get_name()}="{parameter.get_value()}"' for parameter in parameters.values()]
    parameters_str = " ".join(parameters_list)
    added_parameters = helper.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str).get_parameters()
    expected_count = len(parameters)
    observed_count = len(added_parameters)
    validate_equals(observed_value=observed_count, expected_value=expected_count, validation_description="All parameters were added")

    def swact_and_validate():
        swact_success = SystemHostSwactKeywords(helper.ssh_oam_connection).host_swact()
        validate_equals(observed_value=swact_success, expected_value=True, validation_description="Swact was successful")
        listed_parameters = helper.service_parameter_keywords.list_service_parameters(
            service=CONST.SERVICE,
            section=CONST.SECTION,
        ).get_parameters()
        listed_count = len(listed_parameters)
        validate_equals(observed_value=listed_count, expected_value=expected_count, validation_description="All parameters were added and listed")
        validate_equals_with_retry(
            function_to_execute=get_sysctl_values,
            expected_value=expected_values,
            validation_description="Sysctl values on Active Controller should match",
            timeout=45,
        )

    swact_and_validate()
    swact_and_validate()


@mark.lab_has_standby_controller
def test_add_multiple_service_parameters_standby_controller_success(request: pytest.FixtureRequest) -> None:
    """Test that adding all supported sysctl parameters at once succeeds on the standby controller."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    parameters = _get_test_parameters(supported=True)
    parameter_names: list[str] = [*parameters]
    standby_connection = LabConnectionKeywords().get_standby_controller_ssh()
    sysctl_keywords_standby = SysctlKeywords(standby_connection)
    current_values = sysctl_keywords_standby.get_multiple_sysctl_values(parameter_names)
    get_logger().log_info(f"Current Values on the Standby Controller are: \n{json.dumps(current_values, indent=2)}")

    parameters_list = [f'{parameter.get_name()}="{parameter.get_value()}"' for parameter in parameters.values()]
    parameters_str = " ".join(parameters_list)
    added_parameters = helper.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str).get_parameters()
    expected_count = len(parameters)
    observed_count = len(added_parameters)
    validate_equals(observed_value=observed_count, expected_value=expected_count, validation_description="All parameters were added")
    listed_parameters = helper.service_parameter_keywords.list_service_parameters(
        service=CONST.SERVICE,
        section=CONST.SECTION,
    ).get_parameters()
    listed_count = len(listed_parameters)
    validate_equals(observed_value=listed_count, expected_value=expected_count, validation_description="All parameters were added and listed")

    expected_values: dict[str, str] = {parameter.get_name(): parameter.get_value() for parameter in parameters.values()}

    def get_sysctl_values():
        return sysctl_keywords_standby.get_multiple_sysctl_values(parameter_names)

    validate_equals_with_retry(
        function_to_execute=get_sysctl_values,
        expected_value=expected_values,
        validation_description="Sysctl values on Standby Controller should match",
        timeout=45,
    )


@mark.lab_has_compute
def test_add_multiple_service_parameters_compute_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that adding all supported sysctl parameters at once succeeds on all compute nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    parameters = _get_test_parameters(supported=True)
    parameter_names: list[str] = [*parameters]
    host_list_keywords = SystemHostListKeywords(helper.ssh_oam_connection)
    compute_connections: dict[str, SSHConnection] = {compute.get_host_name(): LabConnectionKeywords().get_compute_ssh(compute.get_host_name()) for compute in host_list_keywords.get_computes()}

    for compute_name, compute_connection in compute_connections.items():
        sysctl_keywords = SysctlKeywords(compute_connection)
        current_values = sysctl_keywords.get_multiple_sysctl_values(parameter_names)
        get_logger().log_info(f"Current Values on {compute_name} are: \n{json.dumps(current_values, indent=2)}")

    parameters_list = [f'{parameter.get_name()}="{parameter.get_value()}"' for parameter in parameters.values()]
    parameters_str = " ".join(parameters_list)
    added_parameters = helper.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str).get_parameters()
    expected_count = len(parameters)
    observed_count = len(added_parameters)
    validate_equals(observed_value=observed_count, expected_value=expected_count, validation_description="All parameters were added")
    listed_parameters = helper.service_parameter_keywords.list_service_parameters(
        service=CONST.SERVICE,
        section=CONST.SECTION,
    ).get_parameters()
    listed_count = len(listed_parameters)
    validate_equals(observed_value=listed_count, expected_value=expected_count, validation_description="All parameters were added and listed")

    expected_values: dict[str, str] = {parameter.get_name(): parameter.get_value() for parameter in parameters.values()}

    for compute_name, compute_connection in compute_connections.items():
        sysctl_keywords = SysctlKeywords(compute_connection)

        def get_sysctl_values():
            return sysctl_keywords.get_multiple_sysctl_values(parameter_names)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_values,
            expected_value=expected_values,
            validation_description=f"Sysctl values on '{compute_name}' should match",
            timeout=45,
        )


@mark.lab_has_storage
def test_add_multiple_service_parameters_storage_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that adding all supported sysctl parameters at once succeeds on all storage nodes."""
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    parameters = _get_test_parameters(supported=True)
    parameter_names: list[str] = [*parameters]
    host_list_keywords = SystemHostListKeywords(helper.ssh_oam_connection)
    storage_connections: dict[str, SSHConnection] = {storage.get_host_name(): LabConnectionKeywords().get_storage_ssh(storage.get_host_name()) for storage in host_list_keywords.get_storages()}

    for storage_name, storage_connection in storage_connections.items():
        sysctl_keywords = SysctlKeywords(storage_connection)
        current_values = sysctl_keywords.get_multiple_sysctl_values(parameter_names)
        get_logger().log_info(f"Current Values on {storage_name} are: \n{json.dumps(current_values, indent=2)}")

    parameters_list = [f'{parameter.get_name()}="{parameter.get_value()}"' for parameter in parameters.values()]
    parameters_str = " ".join(parameters_list)
    added_parameters = helper.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str).get_parameters()
    expected_count = len(parameters)
    observed_count = len(added_parameters)
    validate_equals(observed_value=observed_count, expected_value=expected_count, validation_description="All parameters were added")
    listed_parameters = helper.service_parameter_keywords.list_service_parameters(
        service=CONST.SERVICE,
        section=CONST.SECTION,
    ).get_parameters()
    listed_count = len(listed_parameters)
    validate_equals(observed_value=listed_count, expected_value=expected_count, validation_description="All parameters were added and listed")

    expected_values: dict[str, str] = {parameter.get_name(): parameter.get_value() for parameter in parameters.values()}

    for storage_name, storage_connection in storage_connections.items():
        sysctl_keywords = SysctlKeywords(storage_connection)

        def get_sysctl_values():
            return sysctl_keywords.get_multiple_sysctl_values(parameter_names)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_values,
            expected_value=expected_values,
            validation_description=f"Sysctl values on '{storage_name}' should match",
            timeout=45,
        )
