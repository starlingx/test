#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time
from pytest import mark, skip, param

from utils.tis_log import LOG

from consts.stx import VMStatus
from consts.timeout import VMTimeout
from keywords import host_helper, system_helper, vm_helper, network_helper
from testfixtures.recover_hosts import HostsToRecover


@mark.usefixtures('check_alarms')
@mark.parametrize('host_type', [
    param('controller', marks=mark.sanity),
    'compute',
    # 'storage'
])
def test_system_persist_over_host_reboot(host_type):
    """
    Validate Inventory summary over reboot of one of the controller see if
    data persists over reboot

    Test Steps:
        - capture Inventory summary for list of hosts on system service-list
            and neutron agent-list
        - reboot the current Controller-Active
        - Wait for reboot to complete
        - Validate key items from inventory persist over reboot

    """
    if host_type == 'controller':
        host = system_helper.get_active_controller_name()
    elif host_type == 'compute':
        if system_helper.is_aio_system():
            skip("No compute host for AIO system")

        host = None
    else:
        hosts = system_helper.get_hosts(personality='storage')
        if not hosts:
            skip(msg="Lab has no storage nodes. Skip rebooting storage node.")

        host = hosts[0]

    LOG.tc_step("Pre-check for system status")
    system_helper.wait_for_services_enable()
    up_hypervisors = host_helper.get_up_hypervisors()
    network_helper.wait_for_agents_healthy(hosts=up_hypervisors)

    LOG.tc_step("Launch a vm")
    vm_id = vm_helper.boot_vm(cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    if host is None:
        host = vm_helper.get_vm_host(vm_id)

    LOG.tc_step("Reboot a {} node and wait for reboot completes: "
                "{}".format(host_type, host))
    HostsToRecover.add(host)
    host_helper.reboot_hosts(host)
    host_helper.wait_for_hosts_ready(host)

    LOG.tc_step("Check vm is still active and pingable after {} "
                "reboot".format(host))
    vm_helper.wait_for_vm_status(vm_id, status=VMStatus.ACTIVE, fail_ok=False)
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id=vm_id,
                                               timeout=VMTimeout.DHCP_RETRY)

    LOG.tc_step("Check neutron agents and system services are in good state "
                "after {} reboot".format(host))
    network_helper.wait_for_agents_healthy(up_hypervisors)
    system_helper.wait_for_services_enable()

    if host in up_hypervisors:
        LOG.tc_step("Check {} can still host vm after reboot".format(host))
        if not vm_helper.get_vm_host(vm_id) == host:
            time.sleep(30)
            vm_helper.live_migrate_vm(vm_id, destination_host=host)
