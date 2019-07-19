#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture

from utils.tis_log import LOG
from utils import exceptions

from consts.auth import Tenant
from keywords import nova_helper, vm_helper, cinder_helper, glance_helper, \
    network_helper, system_helper
from testfixtures.fixture_resources import ResourceCleanup, GuestLogs


# SIMPLEX_RECOVERED = False


@fixture(scope='function', autouse=True)
def delete_resources_func(request):
    """
    Function level fixture to delete created resources after each caller
    testcase.

    Notes: Auto used fixture - import it to a conftest.py file under a
    feature directory to auto use it on all children testcases.

    Examples:
        - see nova/conftest.py for importing
        - see ResourceCleanup.add function usages in nova/test_shared_cpu.py
        for adding resources to cleanups

    Args:
        request: pytest param present caller test function

    """

    def delete_():
        _delete_resources(ResourceCleanup._get_resources('function'),
                          scope='function')
        ResourceCleanup._reset('function')

    request.addfinalizer(delete_)


@fixture(scope='class', autouse=True)
def delete_resources_class(request):
    """
    Class level fixture to delete created resources after each caller testcase.

    Notes: Auto used fixture - import it to a conftest.py file under a
    feature directory to auto use it on all children
        testcases.

    Examples:
        - see nova/conftest.py for importing
        - see ResourceCleanup.add function usages in nova/test_shared_cpu.py
        for adding resources to cleanups

    Args:
        request: pytest param present caller test function

    """

    def delete_():
        _delete_resources(ResourceCleanup._get_resources('class'),
                          scope='class')
        ResourceCleanup._reset('class')

    request.addfinalizer(delete_)


@fixture(scope='module', autouse=True)
def delete_resources_module(request):
    """
    Module level fixture to delete created resources after each caller testcase.

    Notes: Auto used fixture - import it to a conftest.py file under a
    feature directory to auto use it on all children
        testcases.

    Examples:
        - see nova/conftest.py for importing
        - see ResourceCleanup.add function usages in nova/test_shared_cpu.py
        for adding resources to cleanups

    Args:
        request: pytest param present caller test function

    """

    def delete_():
        _delete_resources(ResourceCleanup._get_resources('module'),
                          scope='module')
        ResourceCleanup._reset('module')

    request.addfinalizer(delete_)


@fixture(scope='session', autouse=True)
def delete_resources_session(request):
    """
    Module level fixture to delete created resources after each caller testcase.

    Notes: Auto used fixture - import it to a conftest.py file under a
    feature directory to auto use it on all children
        testcases.

    Examples:
        - see nova/conftest.py for importing
        - see ResourceCleanup.add function usages in nova/test_shared_cpu.py
        for adding resources to cleanups

    Args:
        request: pytest param present caller test function

    """

    def delete_():
        _delete_resources(ResourceCleanup._get_resources('session'),
                          scope='session')
        ResourceCleanup._reset('session')

    request.addfinalizer(delete_)


@fixture(scope='module')
def flavor_id_module():
    """
    Create basic flavor and volume to be used by test cases as test setup,
    at the beginning of the test module.
    Delete the created flavor and volume as test teardown, at the end of the
    test module.
    """
    flavor = nova_helper.create_flavor()[1]
    ResourceCleanup.add('flavor', resource_id=flavor, scope='module')

    return flavor


def _delete_resources(resources, scope):
    # global SIMPLEX_RECOVERED
    # if not SIMPLEX_RECOVERED and system_helper.is_simplex():
    #     LOG.fixture_step('{} Ensure simplex host is up before cleaning
    #     up'.format(scope))
    #     host_helper.recover_simplex(fail_ok=True)
    #     SIMPLEX_RECOVERED = True

    def __del_aggregate(aggregate_, **kwargs):
        nova_helper.remove_hosts_from_aggregate(aggregate=aggregate_,
                                                check_first=False, **kwargs)
        return nova_helper.delete_aggregates(names=aggregate_, **kwargs)

    # List resources in proper order if there are dependencies!
    del_list = [
        # resource, del_fun, fun_params, whether to delete all resources
        # together.
        ('port_chain', network_helper.delete_sfc_port_chain,
         {'check_first': True}, False),
        ('flow_classifier', network_helper.delete_flow_classifier,
         {'check_first': True}, False),
        ('vm', vm_helper.delete_vms, {'delete_volumes': False}, True),
        ('vm_with_vol', vm_helper.delete_vms, {'delete_volumes': True}, True),
        ('vol_snapshot', cinder_helper.delete_volume_snapshots, {}, True),
        ('volume', cinder_helper.delete_volumes, {}, True),
        ('volume_type', cinder_helper.delete_volume_types, {}, True),
        ('volume_qos', cinder_helper.delete_volume_qos, {}, True),
        ('flavor', nova_helper.delete_flavors, {}, True),
        ('image', glance_helper.delete_images, {}, True),
        ('server_group', nova_helper.delete_server_groups, {}, True),
        ('floating_ip', network_helper.delete_floating_ips, {}, True),
        ('trunk', network_helper.delete_trunks, {}, True),
        ('port_pair_group', network_helper.delete_sfc_port_pair_group,
         {'check_first': True}, False),
        ('port_pair', network_helper.delete_sfc_port_pairs,
         {'check_first': True}, True),
        ('port', network_helper.delete_port, {}, False),
        ('router', network_helper.delete_router, {}, False),
        ('subnet', network_helper.delete_subnets, {}, True),
        ('network_qos', network_helper.delete_qos, {}, False),
        ('network', network_helper.delete_network, {}, False),
        ('security_group_rule', network_helper.delete_security_group_rules, {},
         True),
        ('security_group', network_helper.delete_security_group, {}, False),
        ('aggregate', __del_aggregate, {}, False),
        ('datanetwork', system_helper.delete_data_network, {}, False),
    ]

    err_msgs = []
    for item in del_list:
        resource_type, del_fun, fun_kwargs, del_all = item
        resource_ids = resources.get(resource_type, [])
        if not resource_ids:
            continue

        LOG.fixture_step("({}) Attempt to delete following {}: "
                         "{}".format(scope, resource_type, resource_ids))
        if 'auth_info' not in fun_kwargs:
            fun_kwargs['auth_info'] = Tenant.get('admin')

        if del_all:
            resource_ids = [resource_ids]
        for resource_id in resource_ids:
            try:
                code, msg = del_fun(resource_id, fail_ok=True, **fun_kwargs)[
                            0:2]
                if code > 0:
                    err_msgs.append(msg)
            except exceptions.TiSError as e:
                err_msgs.append(e.__str__())

    # Attempt all deletions before raising exception.
    if err_msgs:
        LOG.error("ERROR: Failed to delete resource(s). \nDetails: {}".format(
            err_msgs))
        # raise exceptions.CommonError("Failed to delete resource(s).
        # Details: {}".format(err_msgs))


@fixture(scope='function', autouse=True)
def guest_logs_func(request):
    """
    Collect guest logs for guests in collect list. Applicable to guest
    heartbeat, server group, vm scaling test cases.
     - Use fixture_resources.GuestLogs.add() to add a guest to collect list
     - Use fixture_resources.GuestLogs.remove() to remove a guest from
     collect list if test passed

    Examples:
        see testcases/functional/mtc/guest_heartbeat/test_vm_voting
        .py for usage

    """

    def _collect():
        _collect_guest_logs(scope='function')

    request.addfinalizer(_collect)


@fixture(scope='class', autouse=True)
def guest_logs_class(request):
    def _collect():
        _collect_guest_logs(scope='class')

    request.addfinalizer(_collect)


@fixture(scope='module', autouse=True)
def guest_logs_module(request):
    def _collect():
        _collect_guest_logs(scope='module')

    request.addfinalizer(_collect)


def _collect_guest_logs(scope):
    guests = GuestLogs._get_guests(scope=scope)
    if guests:
        LOG.fixture_step(
            "({}) Attempt to collect guest logs for: {}".format(scope, guests))
        for guest in guests:
            vm_helper.collect_guest_logs(vm_id=guest)
        GuestLogs._reset(scope=scope)
