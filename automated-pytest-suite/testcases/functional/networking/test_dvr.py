#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time

from pytest import mark, fixture, skip, param

from utils.tis_log import LOG

from consts.auth import Tenant
from consts.stx import RouterStatus
from keywords import network_helper, vm_helper, system_helper, host_helper, \
    cinder_helper
from testfixtures.fixture_resources import ResourceCleanup

result_ = None


@fixture(scope='module')
def router_info(request, stx_openstack_required):
    global result_
    result_ = False

    LOG.fixture_step(
        "Disable SNAT and update router to DVR if not already done.")

    router_id = network_helper.get_tenant_router()
    network_helper.set_router_gateway(router_id, enable_snat=False)
    is_dvr = network_helper.get_router_values(router_id, fields='distributed',
                                              auth_info=Tenant.get('admin'))[0]

    def teardown():
        post_dvr = \
            network_helper.get_router_values(router_id, fields='distributed',
                                             auth_info=Tenant.get('admin'))[0]
        if post_dvr != is_dvr:
            network_helper.set_router_mode(router_id, distributed=is_dvr)

    request.addfinalizer(teardown)

    if not is_dvr:
        network_helper.set_router_mode(router_id, distributed=True,
                                       enable_on_failure=False)

    result_ = True
    return router_id


@fixture()
def _bring_up_router(request):
    def _router_up():
        if result_ is False:
            router_id = network_helper.get_tenant_router()
            network_helper.set_router(router=router_id, fail_ok=False,
                                      enable=True)

    request.addfinalizer(_router_up)


@mark.domain_sanity
def test_dvr_update_router(router_info, _bring_up_router):
    """
    Test update router to distributed and non-distributed

    Args:
        router_info (str): router_id (str)

    Setups:
        - Get the router id and original distributed setting

    Test Steps:
        - Boot a vm before updating router and ping vm from NatBox
        - Change the distributed value of the router and verify it's updated
        successfully
        - Verify router is in ACTIVE state
        - Verify vm can still be ping'd from NatBox
        - Repeat the three steps above with the distributed value reverted to
        original value

    Teardown:
        - Delete vm
        - Revert router to it's original distributed setting if not already
        done so

    """
    global result_
    result_ = False
    router_id = router_info

    LOG.tc_step("Boot a vm before updating router and ping vm from NatBox")
    vm_id = vm_helper.boot_vm(name='dvr_update', reuse_vol=False,
                              cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)

    for update_to_val in [False, True]:
        LOG.tc_step("Update router distributed to {}".format(update_to_val))
        network_helper.set_router_mode(router_id, distributed=update_to_val,
                                       enable_on_failure=False)

        # Wait for 30 seconds to allow the router update completes
        time.sleep(30)
        LOG.tc_step(
            "Verify router is in active state and vm can be ping'd from NatBox")
        assert RouterStatus.ACTIVE == \
            network_helper.get_router_values(router_id,
                                             fields='status')[0], \
            "Router is not in active state after updating distributed to " \
            "{}.".format(update_to_val)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)

    result_ = True


@mark.parametrize(('vms_num', 'srv_grp_policy'), [
    param(2, 'affinity', marks=mark.p2),
    param(2, 'anti-affinity', marks=mark.nightly),
    param(3, 'affinity', marks=mark.p2),
    param(3, 'anti-affinity', marks=mark.p2),
])
def test_dvr_vms_network_connection(vms_num, srv_grp_policy, server_groups,
                                    router_info):
    """
    Test vms East West connection by pinging vms' data network from vm

    Args:
        vms_num (int): number of vms to boot
        srv_grp_policy (str): affinity to boot vms on same host,
            anti-affinity to boot vms on different hosts
        server_groups: test fixture to return affinity and anti-affinity
            server groups
        router_info (str): id of tenant router

    Skip Conditions:
        - Only one nova host on the system

    Setups:
        - Enable DVR    (module)

    Test Steps
        - Update router to distributed if not already done
        - Boot given number of vms with specific server group policy to
            schedule vms on same or different host(s)
        - Ping vms' over data and management networks from one vm to test NS
        and EW traffic

    Teardown:
        - Delete vms
        - Revert router to

    """
    # Increase instance quota count if needed
    current_vms = len(vm_helper.get_vms(strict=False))
    quota_needed = current_vms + vms_num
    vm_helper.ensure_vms_quotas(quota_needed)

    if srv_grp_policy == 'anti-affinity' and len(
            host_helper.get_up_hypervisors()) == 1:
        skip("Only one nova host on the system.")

    LOG.tc_step("Update router to distributed if not already done")
    router_id = router_info
    is_dvr = network_helper.get_router_values(router_id, fields='distributed',
                                              auth_info=Tenant.get('admin'))[0]
    if not is_dvr:
        network_helper.set_router_mode(router_id, distributed=True)

    LOG.tc_step("Boot {} vms with server group policy {}".format(
        vms_num, srv_grp_policy))
    affinity_grp, anti_affinity_grp = server_groups(soft=True)
    srv_grp_id = affinity_grp if srv_grp_policy == 'affinity' else \
        anti_affinity_grp

    vms = []
    tenant_net_id = network_helper.get_tenant_net_id()
    mgmt_net_id = network_helper.get_mgmt_net_id()
    internal_net_id = network_helper.get_internal_net_id()

    internal_vif = {'net-id': internal_net_id}
    if system_helper.is_avs():
        internal_vif['vif-model'] = 'avp'

    nics = [{'net-id': mgmt_net_id}, {'net-id': tenant_net_id}, internal_vif]
    for i in range(vms_num):
        vol = cinder_helper.create_volume()[1]
        ResourceCleanup.add(resource_type='volume', resource_id=vol)
        vm_id = \
            vm_helper.boot_vm('dvr_ew_traffic', source='volume', source_id=vol,
                              nics=nics, cleanup='function',
                              hint={'group': srv_grp_id})[1]
        vms.append(vm_id)
        LOG.tc_step("Wait for vm {} pingable from NatBox".format(vm_id))
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)

    from_vm = vms[0]
    LOG.tc_step(
        "Ping vms over management and data networks from vm {}, and "
        "verify ping successful.".format(from_vm))
    vm_helper.ping_vms_from_vm(to_vms=vms, from_vm=from_vm, fail_ok=False,
                               net_types=['data', 'mgmt', 'internal'])
