#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture, skip, mark

from utils.tis_log import LOG
from consts.reasons import SkipHypervisor

from keywords import vm_helper, host_helper, nova_helper, system_helper, \
    network_helper
from testfixtures.fixture_resources import ResourceCleanup


@fixture(scope='module', autouse=True)
def skip_test_if_less_than_two_hosts(no_simplex):
    hypervisors = host_helper.get_up_hypervisors()
    if len(hypervisors) < 2:
        skip(SkipHypervisor.LESS_THAN_TWO_HYPERVISORS)

    LOG.fixture_step(
        "Update instance and volume quota to at least 10 and 20 respectively")
    vm_helper.ensure_vms_quotas(vms_num=10)

    return len(hypervisors)


class TestDefaultGuest:

    @fixture(scope='class')
    def vms_(self, add_admin_role_class):
        LOG.fixture_step("Create a flavor without ephemeral or swap disks")
        flavor_1 = nova_helper.create_flavor('flv_nolocaldisk')[1]
        ResourceCleanup.add('flavor', flavor_1, scope='class')

        LOG.fixture_step("Create a flavor with ephemeral and swap disks")
        flavor_2 = \
            nova_helper.create_flavor('flv_localdisk', ephemeral=1, swap=512)[1]
        ResourceCleanup.add('flavor', flavor_2, scope='class')

        LOG.fixture_step(
            "Boot vm1 from volume with flavor flv_nolocaldisk and wait for it "
            "pingable from NatBox")
        vm1_name = "vol_nolocal"
        vm1 = vm_helper.boot_vm(vm1_name, flavor=flavor_1, source='volume',
                                cleanup='class')[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm1)

        vm_host = vm_helper.get_vm_host(vm_id=vm1)

        LOG.fixture_step(
            "Boot vm2 from volume with flavor flv_localdisk and wait for it "
            "pingable from NatBox")
        vm2_name = "vol_local"
        vm2 = vm_helper.boot_vm(vm2_name, flavor=flavor_2, source='volume',
                                cleanup='class', avail_zone='nova',
                                vm_host=vm_host)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm2)

        LOG.fixture_step(
            "Boot vm3 from image with flavor flv_nolocaldisk and wait for it "
            "pingable from NatBox")
        vm3_name = "image_novol"
        vm3 = vm_helper.boot_vm(vm3_name, flavor=flavor_1, source='image',
                                cleanup='class', avail_zone='nova',
                                vm_host=vm_host)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm3)

        LOG.fixture_step(
            "Boot vm4 from image with flavor flv_nolocaldisk and wait for it "
            "pingable from NatBox")
        vm4_name = 'image_vol'
        vm4 = vm_helper.boot_vm(vm4_name, flavor_1, source='image',
                                cleanup='class', avail_zone='nova',
                                vm_host=vm_host)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm4)

        LOG.fixture_step(
            "Attach volume to vm4 which was booted from image: {}.".format(vm4))
        vm_helper.attach_vol_to_vm(vm4)

        return [vm1, vm2, vm3, vm4], vm_host

    @mark.trylast
    @mark.sanity
    @mark.cpe_sanity
    def test_evacuate_vms(self, vms_):
        """
        Test evacuated vms
        Args:
            vms_: (fixture to create vms)

        Pre-requisites:
            - At least two up hypervisors on system

        Test Steps:
            - Create vms with various options:
                - vm booted from cinder volume,
                - vm booted from glance image,
                - vm booted from glance image, and have an extra cinder
                volume attached after launch,
                - vm booed from cinder volume with ephemeral and swap disks
            - Move vms onto same hypervisor
            - sudo reboot -f on the host
            - Ensure vms are successfully evacuated to other host
            - Live migrate vms back to original host
            - Check vms can move back, and vms are still reachable from natbox
            - Check system services are enabled and neutron agents are alive

        """
        vms, target_host = vms_

        pre_res_sys, pre_msg_sys = system_helper.wait_for_services_enable(
            timeout=20, fail_ok=True)
        up_hypervisors = host_helper.get_up_hypervisors()
        pre_res_neutron, pre_msg_neutron = \
            network_helper.wait_for_agents_healthy(
                up_hypervisors, timeout=20, fail_ok=True)

        LOG.tc_step(
            "reboot -f on vms host, ensure vms are successfully evacuated and "
            "host is recovered after reboot")
        vm_helper.evacuate_vms(host=target_host, vms_to_check=vms,
                               wait_for_host_up=True, ping_vms=True)

        LOG.tc_step("Check rebooted host can still host vm")
        vm_helper.live_migrate_vm(vms[0], destination_host=target_host)
        vm_helper.wait_for_vm_pingable_from_natbox(vms[0])

        LOG.tc_step("Check system services and neutron agents after {} "
                    "reboot".format(target_host))
        post_res_sys, post_msg_sys = system_helper.wait_for_services_enable(
            fail_ok=True)
        post_res_neutron, post_msg_neutron = \
            network_helper.wait_for_agents_healthy(hosts=up_hypervisors,
                                                   fail_ok=True)

        assert post_res_sys, "\nPost-evac system services stats: {}" \
                             "\nPre-evac system services stats: {}". \
            format(post_msg_sys, pre_msg_sys)
        assert post_res_neutron, "\nPost evac neutron agents stats: {}" \
                                 "\nPre-evac neutron agents stats: {}". \
            format(pre_msg_neutron, post_msg_neutron)
