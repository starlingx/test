#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import pytest

from utils.tis_log import LOG
from utils.rest import Rest
from keywords import system_helper, host_helper, storage_helper


@pytest.fixture(scope='module')
def sysinv_rest():
    r = Rest('sysinv', platform=True)
    return r


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_networks_valid(sysinv_rest, authorize_valid, resource_valid,
                            expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/networks/{}"
    if resource_valid:
        network_list = system_helper.get_system_networks()
    else:
        network_list = ['ffffffffffff-ffff-ffff-ffff-ffffffffffff']

    for network in network_list:
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(path))
        res = path.format(network)
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_clusters_valid(sysinv_rest, authorize_valid, resource_valid,
                            expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/clusters/{}"
    if resource_valid:
        cluster_list = system_helper.get_clusters()
    else:
        cluster_list = ['ffffffff-ffff-ffff-ffff-ffffffffffff']

    for cluster in cluster_list:
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(path))
        res = path.format(cluster)
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_ialarms_valid(sysinv_rest, authorize_valid, resource_valid,
                           expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/ialarms/{}"
    if resource_valid:
        alarm_list = system_helper.get_alarms_table()
    else:
        alarm_list = {'values': [['ffffffff-ffff-ffff-ffff-ffffffffffff']]}

    for alarm in alarm_list['values']:
        alarm_uuid = alarm
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(path))
        res = path.format(alarm_uuid)
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = \
                "Expected code of expected_status - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_devices(sysinv_rest, authorize_valid, resource_valid,
                     expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/devices/{}"

    hostnames = system_helper.get_hosts()
    for host in hostnames:
        res = path.format(host)
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(res))
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, message.format(
                expected_status, status_code, text)


def test_GET_idisks(sysinv_rest):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/idisks/{}"
    hostnames = system_helper.get_hosts()
    for host in hostnames:
        disk_uuids = storage_helper.get_host_disks(host)
        for disk_uuid in disk_uuids:
            res = path.format(disk_uuid)
            message = "Using requests GET {} with proper authentication"
            LOG.tc_step(message.format(res))
            status_code, text = r.get(resource=res, auth=True)
            message = "Retrieved: status_code: {} message: {}"
            LOG.debug(message.format(status_code, text))
            if status_code == 404:
                pytest.skip("Unsupported resource in this configuration.")
            else:
                message = "Determine if expected code of 200 is received"
                LOG.tc_step(message)
                message = "Expected code of 200 - received {} and message {}"
                assert status_code == 200, message.format(status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_lldp_agents(sysinv_rest, authorize_valid, resource_valid,
                         expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/lldp_agents/{}"
    hostnames = system_helper.get_hosts()
    for host in hostnames:
        LOG.info(host)
        if resource_valid:
            lldp_table = host_helper.get_host_lldp_agents(host)
        else:
            lldp_table = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
        LOG.info(lldp_table)
        for lldp_uuid in lldp_table:
            res = path.format(lldp_uuid)
            message = "Using requests GET {} with proper authentication"
            LOG.tc_step(message.format(res))
            status_code, text = r.get(resource=res, auth=authorize_valid)
            message = "Retrieved: status_code: {} message: {}"
            LOG.debug(message.format(status_code, text))
            if status_code == 404:
                pytest.skip("Unsupported resource in this configuration.")
            else:
                message = "Determine if expected code of {} is received"
                LOG.tc_step(message.format(expected_status))
                message = "Expected code of {} - received {} and message {}"
                assert status_code == expected_status, message.format(
                    expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_lldp_neighbors(sysinv_rest, authorize_valid, resource_valid,
                            expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/lldp_neighbors/{}"
    hostnames = system_helper.get_hosts()
    for host in hostnames:
        LOG.info(host)
        if resource_valid:
            lldp_table = host_helper.get_host_lldp_neighbors(host)
        else:
            lldp_table = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
        LOG.info(lldp_table)
        for lldp_uuid in lldp_table:
            res = path.format(lldp_uuid)
            message = "Using requests GET {} with proper authentication"
            LOG.tc_step(message.format(res))
            status_code, text = r.get(resource=res, auth=authorize_valid)
            message = "Retrieved: status_code: {} message: {}"
            LOG.debug(message.format(status_code, text))
            if status_code == 404:
                pytest.skip("Unsupported resource in this configuration.")
            else:
                message = "Determine if expected code of {} is received"
                LOG.tc_step(message.format(expected_status))
                message = "Expected code of {} - received {} and message {}"
                assert status_code == expected_status, \
                    message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_services(sysinv_rest, authorize_valid, resource_valid,
                      expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/services/{}"
    if resource_valid:
        service_list = system_helper.get_services()
    else:
        service_list = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
    for service in service_list:
        LOG.info(service)
        res = path.format(service)
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(res))
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
]
                         )
def test_GET_servicenodes(sysinv_rest, authorize_valid, resource_valid,
                          expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/servicenodes/{}"
    if resource_valid:
        service_list = system_helper.get_servicenodes()
    else:
        service_list = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
    for service in service_list:
        LOG.info(service)
        res = path.format(service)
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(res))
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_servicegroup(sysinv_rest, authorize_valid, resource_valid,
                          expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        authorize_valid - whether to use authentication or not
        resource_valid - whether the pathvariable is valid or not
        expected_status - what status is expected

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/servicegroup/{}"
    if resource_valid:
        service_list = system_helper.get_servicegroups()
    else:
        service_list = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
    for service in service_list:
        LOG.info(service)
        res = path.format(service)
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(res))
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)


@pytest.mark.parametrize(('authorize_valid', 'resource_valid',
                          'expected_status'), [
    (True, True, 200),
    (True, False, 400),
    (False, True, 401)
])
def test_GET_service_parameter(sysinv_rest, authorize_valid, resource_valid,
                               expected_status):
    """
    Test GET of <resource> with valid authentication.

    Args:
        authorize_valid - whether to use authentication or not
        resource_valid - whether the pathvariable is valid or not
        expected_status - what status is expected

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    path = "/service_parameter/{}"
    if resource_valid:
        service_list = system_helper.get_service_parameter_values(field='uuid')
    else:
        service_list = ['ffffffff-ffff-ffff-ffff-ffffffffffff']
    for service in service_list:
        LOG.info(service)
        res = path.format(service)
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(res))
        status_code, text = r.get(resource=res, auth=authorize_valid)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, text))
        if status_code == 404:
            pytest.skip("Unsupported resource in this configuration.")
        else:
            message = "Determine if expected code of {} is received"
            LOG.tc_step(message.format(expected_status))
            message = "Expected code of {} - received {} and message {}"
            assert status_code == expected_status, \
                message.format(expected_status, status_code, text)
