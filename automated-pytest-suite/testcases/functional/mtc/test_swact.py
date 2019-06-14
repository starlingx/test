#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, skip

from utils.tis_log import LOG
from consts.reasons import SkipSysType
from keywords import host_helper, system_helper, vm_helper, network_helper, \
    kube_helper


@mark.sanity
@mark.cpe_sanity
def test_swact_controllers(wait_for_con_drbd_sync_complete):
    """
    Verify swact active controller

    Test Steps:
        - Boot a vm on system and check ping works
        - Swact active controller
        - Verify standby controller and active controller are swapped
        - Verify vm is still pingable

    """
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    if not wait_for_con_drbd_sync_complete:
        skip(SkipSysType.LESS_THAN_TWO_CONTROLLERS)

    LOG.tc_step('retrieve active and available controllers')
    pre_active_controller, pre_standby_controller = \
        system_helper.get_active_standby_controllers()
    assert pre_standby_controller, "No standby controller available"

    pre_res_sys, pre_msg_sys = system_helper.wait_for_services_enable(
        timeout=20, fail_ok=True)
    up_hypervisors = host_helper.get_up_hypervisors()
    pre_res_neutron, pre_msg_neutron = network_helper.wait_for_agents_healthy(
        up_hypervisors, timeout=20, fail_ok=True)

    LOG.tc_step("Boot a vm from image and ping it")
    vm_id_img = vm_helper.boot_vm(name='swact_img', source='image',
                                  cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id_img)

    LOG.tc_step("Boot a vm from volume and ping it")
    vm_id_vol = vm_helper.boot_vm(name='swact', cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id_vol)

    LOG.tc_step("Swact active controller and ensure active controller is "
                "changed")
    host_helper.swact_host(hostname=pre_active_controller)

    LOG.tc_step("Verify standby controller and active controller are swapped")
    post_active_controller = system_helper.get_active_controller_name()
    post_standby_controller = system_helper.get_standby_controller_name()

    assert pre_standby_controller == post_active_controller, \
        "Prev standby: {}; Post active: {}".format(
            pre_standby_controller, post_active_controller)
    assert pre_active_controller == post_standby_controller, \
        "Prev active: {}; Post standby: {}".format(
            pre_active_controller, post_standby_controller)

    LOG.tc_step("Check boot-from-image vm still pingable after swact")
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id_img, timeout=30)
    LOG.tc_step("Check boot-from-volume vm still pingable after swact")
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id_vol, timeout=30)

    LOG.tc_step("Check system services and neutron agents after swact "
                "from {}".format(pre_active_controller))
    post_res_sys, post_msg_sys = \
        system_helper.wait_for_services_enable(fail_ok=True)
    post_res_neutron, post_msg_neutron = \
        network_helper.wait_for_agents_healthy(hosts=up_hypervisors,
                                               fail_ok=True)

    assert post_res_sys, "\nPost-evac system services stats: {}" \
                         "\nPre-evac system services stats: {}". \
        format(post_msg_sys, pre_msg_sys)
    assert post_res_neutron, "\nPost evac neutron agents stats: {}" \
                             "\nPre-evac neutron agents stats: {}". \
        format(pre_msg_neutron, post_msg_neutron)

    LOG.tc_step("Check hosts are Ready in kubectl get nodes after swact")
    kube_helper.wait_for_nodes_ready(hosts=(pre_active_controller,
                                            pre_standby_controller), timeout=30)


@mark.platform_sanity
def test_swact_controller_platform(wait_for_con_drbd_sync_complete):
    """
    Verify swact active controller

    Test Steps:
        - Swact active controller
        - Verify standby controller and active controller are swapped
        - Verify nodes are ready in kubectl get nodes

    """
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    if not wait_for_con_drbd_sync_complete:
        skip(SkipSysType.LESS_THAN_TWO_CONTROLLERS)

    LOG.tc_step('retrieve active and available controllers')
    pre_active_controller, pre_standby_controller = \
        system_helper.get_active_standby_controllers()
    assert pre_standby_controller, "No standby controller available"

    LOG.tc_step("Swact active controller and ensure active controller "
                "is changed")
    host_helper.swact_host(hostname=pre_active_controller)

    LOG.tc_step("Check hosts are Ready in kubectl get nodes after swact")
    kube_helper.wait_for_nodes_ready(hosts=(pre_active_controller,
                                            pre_standby_controller), timeout=30)
