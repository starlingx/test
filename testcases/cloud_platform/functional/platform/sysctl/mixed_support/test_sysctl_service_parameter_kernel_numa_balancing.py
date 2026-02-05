"""Tests the sysctl parameter "kernel.numa_balancing" in a lab with mixed kernel support.

This parameter is supported on standard kernels but not on rt/lowlatency kernels.
"""

import pytest
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sysctl.sysctl_keywords import SysctlKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from testcases.cloud_platform.functional.platform.sysctl.helper_sysctl_service_parameters import CONST, HelperSysctlServiceParameters

TEST_PARAMETER = SystemServiceParameterObject(service=CONST.SERVICE, section=CONST.SECTION, name="kernel.numa_balancing", value="1", modified_value="0")


@mark.lab_has_compute
@mark.lab_has_low_latency
@mark.lab_has_non_low_latency
def test_add_service_parameter_compute_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that adding kernel.numa_balancing is accepted but ignored on lowlatency compute nodes.

    The parameter is added via the service parameter API successfully, but
    lowlatency compute nodes do not support it, so sysctl should fail to
    read the value on those nodes.
    """
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    host_list_keywords = SystemHostListKeywords(helper.ssh_oam_connection)
    compute_connections: dict[str, SSHConnection] = {compute.get_host_name(): LabConnectionKeywords().get_compute_ssh(compute.get_host_name()) for compute in host_list_keywords.get_computes()}

    for compute_name, compute_connection in compute_connections.items():
        sysctl_keywords = SysctlKeywords(compute_connection)
        sysctl_keywords.get_sysctl_value_fails(TEST_PARAMETER.get_name())
        get_logger().log_info(f"'{TEST_PARAMETER.get_name()}' is not supported on '{compute_name}'")

    helper._add_sysctl_parameter_expect_success(parameter=TEST_PARAMETER)

    for compute_name, compute_connection in compute_connections.items():
        sysctl_keywords = SysctlKeywords(compute_connection)
        sysctl_keywords.get_sysctl_value_fails(TEST_PARAMETER.get_name())


@mark.lab_has_storage
@mark.lab_has_low_latency
@mark.lab_has_non_low_latency
def test_add_service_parameter_storage_nodes_success(request: pytest.FixtureRequest) -> None:
    """Test that adding kernel.numa_balancing succeeds on storage nodes.

    Storage nodes run the standard kernel, so this parameter is expected
    to be applied and readable via sysctl.
    """
    helper = HelperSysctlServiceParameters()
    helper.setup_method()

    request.addfinalizer(helper.teardown_method)
    helper.add_service_parameter_storage_nodes_success(TEST_PARAMETER)
