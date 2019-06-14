#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, skip, param

from utils.tis_log import LOG
from consts.stx import HostAvailState
from testfixtures.recover_hosts import HostsToRecover
from keywords import host_helper, system_helper


@mark.parametrize('host_type', [
    param('controller', marks=mark.platform),
    param('compute', marks=mark.platform),
    param('storage', marks=mark.platform),
])
def test_force_reboot_host(host_type):
    """
    Verify lock unlock host

    Test Steps:
        - Select a host per given type. If type is controller, select standby
            controller.
        - Lock selected host and ensure it is successfully locked
        - Unlock selected host and ensure it is successfully unlocked

    """

    LOG.tc_step("Select a {} node from system if any".format(host_type))
    hosts = system_helper.get_hosts(availability=(HostAvailState.AVAILABLE,
                                                  HostAvailState.DEGRADED),
                                    personality=host_type)
    if not hosts:
        skip("No available or degraded {} host found on system".format(
            host_type))

    host = hosts[0]
    LOG.tc_step("Force reboot {} host: {}".format(host_type, host))
    HostsToRecover.add(host)
    host_helper.reboot_hosts(hostnames=host)
    host_helper.wait_for_hosts_ready(host)
