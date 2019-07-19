#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time
from pytest import mark, skip, param

from utils.tis_log import LOG
from consts.stx import HostOperState, HostAvailState
from testfixtures.recover_hosts import HostsToRecover
from keywords import host_helper, system_helper


@mark.platform_sanity
def test_lock_active_controller_reject(no_simplex):
    """
    Verify lock unlock active controller. Expected it to fail

    Test Steps:
        - Get active controller
        - Attempt to lock active controller and ensure it's rejected

    """
    LOG.tc_step('Retrieve the active controller from the lab')
    active_controller = system_helper.get_active_controller_name()
    assert active_controller, "No active controller available"

    # lock standby controller node and verify it is successfully locked
    LOG.tc_step("Lock active controller and ensure it fail to lock")
    exit_code, cmd_output = host_helper.lock_host(active_controller,
                                                  fail_ok=True, swact=False,
                                                  check_first=False)
    assert exit_code == 1, 'Expect locking active controller to ' \
                           'be rejected. Actual: {}'.format(cmd_output)
    status = system_helper.get_host_values(active_controller,
                                           'administrative')[0]
    assert status == 'unlocked', "Fail: The active controller was locked."


@mark.parametrize('host_type', [
    param('controller', marks=mark.priorities('platform_sanity',
                                              'sanity', 'cpe_sanity')),
    param('compute', marks=mark.priorities('platform_sanity')),
    param('storage', marks=mark.priorities('platform_sanity')),
])
def test_lock_unlock_host(host_type):
    """
    Verify lock unlock host

    Test Steps:
        - Select a host per given type. If type is controller, select
            standby controller.
        - Lock selected host and ensure it is successfully locked
        - Unlock selected host and ensure it is successfully unlocked

    """
    LOG.tc_step("Select a {} node from system if any".format(host_type))
    if host_type == 'controller':
        if system_helper.is_aio_simplex():
            host = 'controller-0'
        else:
            host = system_helper.get_standby_controller_name()
            assert host, "No standby controller available"

    else:
        if host_type == 'compute' and system_helper.is_aio_system():
            skip("No compute host on AIO system")
        elif host_type == 'storage' and not system_helper.is_storage_system():
            skip("System does not have storage nodes")

        hosts = system_helper.get_hosts(personality=host_type,
                                        availability=HostAvailState.AVAILABLE,
                                        operational=HostOperState.ENABLED)

        assert hosts, "No good {} host on system".format(host_type)
        host = hosts[0]

    LOG.tc_step("Lock {} host - {} and ensure it is successfully "
                "locked".format(host_type, host))
    HostsToRecover.add(host)
    host_helper.lock_host(host, swact=False)

    # wait for services to stabilize before unlocking
    time.sleep(20)

    # unlock standby controller node and verify controller node is
    # successfully unlocked
    LOG.tc_step("Unlock {} host - {} and ensure it is successfully "
                "unlocked".format(host_type, host))
    host_helper.unlock_host(host)
