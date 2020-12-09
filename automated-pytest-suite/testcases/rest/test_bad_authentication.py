#
# Copyright (c) 2019-2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import pytest
from utils.tis_log import LOG
from utils.rest import Rest


@pytest.fixture(scope='module')
def sysinv_rest():
    r = Rest('sysinv', platform=True)
    return r


def normalize(resource_name):
    import re
    if resource_name:
        return re.sub(r'__((\w|_)+)__', r'{\1}', resource_name)
    return ''


def attempt(operation, resource):
    print("Testing {} with {}".format(operation, resource))
    if operation == operation:
        return True
    else:
        return False


def get(sysinv_rest, resource):
    """
    Test GET of <resource> with invalid authentication.

    Args:
        sysinv_rest
        resource

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> without proper authentication
        - Determine if expected status_code of 401 is received
    Test Teardown:
        n/a
    """
    message = "Using requests GET {} without proper authentication"
    LOG.tc_step(message.format(resource))

    status_code, text = sysinv_rest.get(resource=resource, auth=False)
    message = "Retrieved: status_code: {} message: {}"
    LOG.debug(message.format(status_code, text))

    LOG.tc_step("Determine if expected status_code of 401 is received")
    message = "Expected status_code of 401 - received {} and message {}"
    assert status_code == 401, message.format(status_code, text)


def delete(sysinv_rest, resource):
    """
    Test DELETE of <resource> with invalid authentication.

    Args:
        sysinv_rest
        resource

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests DELETE <resource> without proper authentication
        - Determine if expected status_code of 401 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    LOG.tc_step("DELETE <resource> without proper authentication")
    status_code, text = r.delete(resource=resource, auth=False)
    LOG.info("Retrieved: status_code: {} message: {}".format(status_code, text))
    LOG.tc_step("Determine if expected status_code of 401 is received")

    message = "Expected status_code of 401 - received {} and message {}"
    assert status_code == 401, message.format(status_code, text)


def post(sysinv_rest, resource):
    """
    Test POST of <resource> with invalid authentication.

    Args:
        sysinv_rest
        resource

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests POST <resource>
        - Determine if expected status_code of 401 is received
    Test Teardown:
        n/a
    """
    LOG.tc_step("POST {}".format(resource))
    status_code, text = sysinv_rest.post(resource=resource, json_data={},
                                         auth=False)
    message = "Retrieved: status_code: {} message: {}"
    LOG.info(message.format(status_code, text))
    LOG.tc_step("Determine if expected_code of 401 is received")
    message = "Expected code of 401 - received {} and message {}"
    assert status_code == 401, \
        message.format(status_code, text)


def patch(sysinv_rest, resource):
    """
    Test PATCH of <resource>  with invalid authentication.

    Args:
        sysinv_rest
        resource

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests PATCH <resource> without proper authentication
        - Determine if expected status_code of 401 is received
    Test Teardown:
        n/a
    """
    LOG.tc_step("PATCH {} with bad authentication".format(resource))
    status_code, text = sysinv_rest.patch(resource=resource, json_data={},
                                          auth=False)

    message = "Retrieved: status_code: {} message: {}"
    LOG.info(message.format(status_code, text))
    LOG.tc_step("Determine if expected status_code of 401 is received")
    message = "Expected code of 401 - received {} and message {}"
    assert status_code == 401, message.format(status_code, text)


def put(sysinv_rest, resource):
    """
    Test PUT of <resource> with invalid authentication.

    Args:
        sysinv_rest
        resource

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests PUT <resource> without proper authentication
        - Determine if expected status_code of 401 is received
    Test Teardown:
        n/a
    """
    r = sysinv_rest
    LOG.tc_step("PUT {} with bad authentication".format(resource))
    status_code, text = r.put(resource=resource,
                              json_data={}, auth=False)
    message = "Retrieved: status_code: {} message: {}"
    LOG.debug(message.format(status_code, text))

    LOG.tc_step("Determine if expected status_code of 401 is received")
    message = "Expected code of 401 - received {} and message {}"
    assert status_code == 401, message.format(status_code, text)


@pytest.mark.parametrize(
    'operation,resource', [
        ('DELETE', '/addrpools/__pool_id__'),
        ('DELETE', '/ialarms/__alarm_uuid__'),
        ('DELETE', '/ihosts/__host_id__/addresses/__address_id__'),
        ('DELETE', '/ihosts/__host_id__'),
        ('DELETE', '/ihosts/__host_id__/routes/__route_id__'),
        ('DELETE', '/iinterfaces/__interface_id__'),
        ('DELETE', '/ilvgs/__volumegroup_id__'),
        ('DELETE', '/iprofiles/__profile_id__'),
        ('DELETE', '/ipvs/__physicalvolume_id__'),
        ('DELETE', '/istors/__stor_id__'),
        ('DELETE', '/loads/__load_id__'),
        ('DELETE', '/sdn_controller/__controller_id__'),
        ('DELETE', '/service_parameter/__parameter_id__'),
        ('DELETE', '/tpmconfig/__tpmconfig_id__'),
        ('DELETE', '/upgrade'),
        ('GET', '/addrpools'),
        ('GET', '/addrpools/__pool_id__'),
        ('GET', '/ceph_mon'),
        ('GET', '/ceph_mon/__ceph_mon_id__'),
        ('GET', '/clusters'),
        ('GET', '/clusters/__uuid__'),
        ('GET', '/controller_fs'),
        ('GET', '/devices/__device_id__'),
        ('GET', '/drbdconfig'),
        ('GET', '/event_log'),
        ('GET', '/event_log/__log_uuid__'),
        ('GET', '/event_suppression'),
        ('GET', '/health'),
        ('GET', '/health/upgrade'),
        ('GET', '/ialarms/__alarm_uuid__'),
        ('GET', '/ialarms'),
        ('GET', '/icpus/__cpu_id__'),
        ('GET', '/idisks/__disk_id__'),
        ('GET', '/idns'),
        ('GET', '/iextoam'),
        ('GET', '/ihosts'),
        ('GET', '/ihosts/bulk_export'),
        ('GET', '/ihosts/__host_id__/addresses/__address_id__'),
        ('GET', '/ihosts/__host_id__/addresses'),
        ('GET', '/ihosts/__host_id__'),
        ('GET', '/ihosts/__host_id__/idisks'),
        ('GET', '/ihosts/__host_id__/ilvgs'),
        ('GET', '/ihosts/__host_id__/imemorys'),
        ('GET', '/ihosts/__host_id__/ipvs'),
        ('GET', '/ihosts/__host_id__/isensorgroups'),
        ('GET', '/ihosts/__host_id__/isensors'),
        ('GET', '/ihosts/__host_id__/istors'),
        ('GET', '/ihosts/__host_id__/pci_devices'),
        ('GET', '/ihosts/__host_id__/routes'),
        ('GET', '/ihosts/__host_id__/routes/__route_id__'),
        ('GET', '/iinfra'),
        ('GET', '/iinterfaces/__interface_id__'),
        ('GET', '/ilvgs/__volumegroup_id__'),
        ('GET', '/imemorys/__memory_id__'),
        ('GET', '/intp'),
        ('GET', '/ipm'),
        ('GET', '/iprofiles'),
        ('GET', '/iprofiles/__profile_id__'),
        ('GET', '/iprofiles/__profile_id__/icpus'),
        ('GET', '/iprofiles/__profile_id__/iinterfaces'),
        ('GET', '/iprofiles/__profile_id__/ports'),
        ('GET', '/ipvs/__physicalvolume_id__'),
        ('GET', '/isensorgroups/__sensorgroup_id__'),
        ('GET', '/isensors/__sensor_id__'),
        ('GET', '/istorconfig'),
        ('GET', '/istors/__stor_id__'),
        ('GET', '/isystems'),
        ('GET', '/lldp_agents'),
        ('GET', '/lldp_agents/__lldp_agent_id__'),
        ('GET', '/lldp_neighbors'),
        ('GET', '/lldp_neighbors/__lldp_neighbor_id__'),
        ('GET', '/loads'),
        ('GET', '/loads/__load_id__'),
        ('GET', '/networks'),
        ('GET', '/networks/__network_id__'),
        ('GET', '/ports/__port_id__'),
        ('GET', '/remotelogging'),
        ('GET', '/sdn_controller'),
        ('GET', '/sdn_controller/__controller_id__'),
        ('GET', '/servicegroup'),
        ('GET', '/servicegroup/__servicegroup_id__'),
        ('GET', '/servicenodes'),
        ('GET', '/servicenodes/__node_id__'),
        ('GET', '/service_parameter'),
        ('GET', '/service_parameter/__parameter_id__'),
        ('GET', '/services'),
        ('GET', '/services/__service_id__'),
        ('GET', '/storage_backend'),
        ('GET', '/storage_backend/usage'),
        ('GET', '/storage_ceph'),
        ('GET', '/storage_lvm'),
        ('GET', '/tpmconfig'),
        ('GET', '/upgrade'),
        ('PATCH', '/addrpools/__pool_id__'),
        ('PATCH', '/ceph_mon/__ceph_mon_id__'),
        ('PATCH', '/controller_fs/__controller_fs_id__'),
        ('PATCH', '/devices/__device_id__'),
        ('PATCH', '/drbdconfig/__drbdconfig_id__'),
        ('PATCH', '/event_suppression/__event_suppression_uuid__'),
        ('PATCH', '/idns/__dns_id__'),
        ('PATCH', '/iextoam/__extoam_id__'),
        ('PATCH', '/ihosts/__host_id__'),
        ('PATCH', '/ihosts/__host_id__'),
        ('PATCH', '/iinfra/__infra_id__'),
        ('PATCH', '/iinterfaces/__interface_id__'),
        ('PATCH', '/ilvgs/__volumegroup_id__'),
        ('PATCH', '/imemorys/__memory_id__'),
        ('PATCH', '/intp/__ntp_id__'),
        ('PATCH', '/ipm/__pm_id__'),
        ('PATCH', '/isensorgroups/__sensorgroup_id__'),
        ('PATCH', '/isensors/__sensor_id__'),
        ('PATCH', '/istors/__stor_id__'),
        ('PATCH', '/isystems'),
        ('PATCH', '/remotelogging/__remotelogging_id__'),
        ('PATCH', '/sdn_controller/__controller_id__'),
        ('PATCH', '/service_parameter/__parameter_id__'),
        ('PATCH', '/services/__service_name__'),
        ('PATCH', '/storage_ceph/__storage_ceph_id__'),
        ('PATCH', '/storage_lvm/__storage_lvm_id__'),
        ('PATCH', '/tpmconfig/__tpmconfig_id__'),
        ('PATCH', '/upgrade'),
        ('POST', '/addrpools'),
        ('POST', '/firewallrules/import_firewall_rules'),
        ('POST', '/ihosts'),
        ('POST', '/ihosts/bulk_add'),
        ('POST', '/ihosts/__host_id__/addresses'),
        ('POST', '/ihosts/__host_id__/downgrade'),
        ('POST', '/ihosts/__host_id__/iinterfaces'),
        ('POST', '/ihosts/__host_id__/istors'),
        ('POST', '/ihosts/__host_id__/routes'),
        ('POST', '/ihosts/__host_id__/upgrade'),
        ('POST', '/iinfra'),
        ('POST', '/ilvgs'),
        ('POST', '/iprofiles'),
        ('POST', '/ipvs'),
        ('POST', '/loads/import_load'),
        ('POST', '/sdn_controller'),
        ('POST', '/service_parameter/apply'),
        ('POST', '/service_parameter'),
        ('POST', '/storage_ceph'),
        ('POST', '/tpmconfig'),
        ('POST', '/upgrade'),
        ('PUT', '/ihosts/__host_id__/state/host_cpus_modify')
    ]
)
def test_bad_authentication(sysinv_rest, operation, resource):
    resource = normalize(resource)

    if operation == "GET":
        LOG.info("getting... {}".format(resource))
        get(sysinv_rest, resource)
    elif operation == "DELETE":
        LOG.info("deleting... {}".format(resource))
        delete(sysinv_rest, resource)
    elif operation == "PATCH":
        LOG.info("patching... {} {}".format(operation, resource))
        patch(sysinv_rest, resource)
    elif operation == "POST":
        LOG.info("posting... {} {}".format(operation, resource))
        post(sysinv_rest, resource)
    elif operation == "PUT":
        LOG.info("putting... {} {}".format(operation, resource))
        put(sysinv_rest, resource)
