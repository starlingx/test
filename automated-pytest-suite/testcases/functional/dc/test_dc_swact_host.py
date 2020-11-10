#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from pytest import fixture

from consts.auth import Tenant
from consts.proj_vars import ProjVar
from consts.stx import SubcloudStatus
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG
from keywords import host_helper, dc_helper


@fixture(scope='module')
def swact_precheck(request):
    LOG.info("Gather subcloud management info")
    subcloud = ProjVar.get_var('PRIMARY_SUBCLOUD')

    def revert():
        LOG.fixture_step("Manage {} if unmanaged".format(subcloud))
        dc_helper.manage_subcloud(subcloud)

    request.addfinalizer(revert)

    managed_subclouds = dc_helper.get_subclouds(mgmt=SubcloudStatus.MGMT_MANAGED,
                                                avail=SubcloudStatus.AVAIL_ONLINE,
                                                sync=SubcloudStatus.SYNCED)
    if subcloud in managed_subclouds:
        managed_subclouds.remove(subcloud)

    ssh_map = ControllerClient.get_active_controllers_map()
    managed_subclouds = [subcloud for subcloud in managed_subclouds if subcloud in ssh_map]

    return subcloud, managed_subclouds


def test_dc_swact_host(swact_precheck, check_central_alarms):
    """
    Test host swact on central region
    Args:
        swact_precheck(fixture): check subclouds managed and online
    Setup:
        - Ensure primary subcloud is managed
    Test Steps:
        - Unmanage primary subcloud
        - Swact the host
        - Verify subclouds are managed
    Teardown:
        - Manage unmanaged subclouds
    """
    primary_subcloud, managed_subcloud = swact_precheck
    ssh_central = ControllerClient.get_active_controller(name="RegionOne")

    LOG.tc_step("Unmanage {}".format(primary_subcloud))
    dc_helper.unmanage_subcloud(subcloud=primary_subcloud, check_first=True)

    LOG.tc_step("Swact host on central region")
    central_auth = Tenant.get('admin_platform', dc_region='RegionOne')
    host_helper.swact_host(auth_info=central_auth)

    LOG.tc_step("Check subclouds after host swact on central region")
    for managed_subcloud in managed_subcloud:
        dc_helper.wait_for_subcloud_status(subcloud=managed_subcloud,
                                           avail=SubcloudStatus.AVAIL_ONLINE,
                                           mgmt=SubcloudStatus.MGMT_MANAGED,
                                           sync=SubcloudStatus.SYNCED,
                                           con_ssh=ssh_central)

    LOG.tc_step("Manage {}".format(primary_subcloud))
    dc_helper.manage_subcloud(subcloud=primary_subcloud, check_first=True)
    dc_helper.wait_for_subcloud_status(subcloud=primary_subcloud,
                                       avail=SubcloudStatus.AVAIL_ONLINE,
                                       mgmt=SubcloudStatus.MGMT_MANAGED,
                                       sync=SubcloudStatus.SYNCED,
                                       con_ssh=ssh_central)
