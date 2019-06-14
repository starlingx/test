#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture, skip, mark

import keywords.host_helper
from utils.tis_log import LOG
from consts.timeout import VMTimeout
from consts.stx import VMStatus
from consts.reasons import SkipStorageBacking, SkipHypervisor

from keywords import vm_helper, host_helper, nova_helper, cinder_helper, \
    system_helper, check_helper
from testfixtures.fixture_resources import ResourceCleanup

from testfixtures.recover_hosts import HostsToRecover


@fixture(scope='module', autouse=True)
def update_quotas(add_admin_role_module):
    LOG.fixture_step("Update instance and volume quota to at least 10 and "
                     "20 respectively")
    vm_helper.ensure_vms_quotas()


@fixture(scope='module')
def hosts_per_backing():
    hosts_per_backend = host_helper.get_hosts_per_storage_backing()
    return hosts_per_backend


def touch_files_under_vm_disks(vm_id, ephemeral, swap, vm_type, disks):
    expt_len = 1 + int(bool(ephemeral)) + int(bool(swap)) + \
               (1 if 'with_vol' in vm_type else 0)

    LOG.info("\n--------------------------Auto mount non-root disks if any")
    mounts = vm_helper.auto_mount_vm_disks(vm_id=vm_id, disks=disks)
    assert expt_len == len(mounts)

    if bool(swap):
        mounts.remove('none')

    LOG.info("\n--------------------------Create files under vm disks: "
             "{}".format(mounts))
    file_paths, content = vm_helper.touch_files(vm_id=vm_id, file_dirs=mounts)
    return file_paths, content


class TestDefaultGuest:

    @fixture(scope='class', autouse=True)
    def skip_test_if_less_than_two_hosts(self):
        if len(host_helper.get_up_hypervisors()) < 2:
            skip(SkipHypervisor.LESS_THAN_TWO_HYPERVISORS)

    @mark.parametrize('storage_backing', [
        'local_image',
        'remote',
    ])
    def test_evacuate_vms_with_inst_backing(self, hosts_per_backing,
                                            storage_backing):
        """
        Test evacuate vms with various vm storage configs and host instance
        backing configs

        Args:
            storage_backing: storage backing under test

        Skip conditions:
            - Less than two hosts configured with storage backing under test

        Setups:
            - Add admin role to primary tenant (module)

        Test Steps:
            - Create flv_rootdisk without ephemeral or swap disks, and set
            storage backing extra spec
            - Create flv_ephemswap with ephemeral AND swap disks, and set
            storage backing extra spec
            - Boot following vms on same host and wait for them to be
            pingable from NatBox:
                - Boot vm1 from volume with flavor flv_rootdisk
                - Boot vm2 from volume with flavor flv_localdisk
                - Boot vm3 from image with flavor flv_rootdisk
                - Boot vm4 from image with flavor flv_rootdisk, and attach a
                volume to it
                - Boot vm5 from image with flavor flv_localdisk
            - sudo reboot -f on vms host
            - Ensure evacuation for all 5 vms are successful (vm host
            changed, active state, pingable from NatBox)

        Teardown:
            - Delete created vms, volumes, flavors
            - Remove admin role from primary tenant (module)

        """
        hosts = hosts_per_backing.get(storage_backing, [])
        if len(hosts) < 2:
            skip(SkipStorageBacking.LESS_THAN_TWO_HOSTS_WITH_BACKING.format(
                storage_backing))

        target_host = hosts[0]

        LOG.tc_step("Create a flavor without ephemeral or swap disks")
        flavor_1 = nova_helper.create_flavor('flv_rootdisk',
                                             storage_backing=storage_backing)[1]
        ResourceCleanup.add('flavor', flavor_1, scope='function')

        LOG.tc_step("Create another flavor with ephemeral and swap disks")
        flavor_2 = nova_helper.create_flavor('flv_ephemswap', ephemeral=1,
                                             swap=512,
                                             storage_backing=storage_backing)[1]
        ResourceCleanup.add('flavor', flavor_2, scope='function')

        LOG.tc_step("Boot vm1 from volume with flavor flv_rootdisk and wait "
                    "for it pingable from NatBox")
        vm1_name = "vol_root"
        vm1 = vm_helper.boot_vm(vm1_name, flavor=flavor_1, source='volume',
                                avail_zone='nova', vm_host=target_host,
                                cleanup='function')[1]

        vms_info = {vm1: {'ephemeral': 0,
                          'swap': 0,
                          'vm_type': 'volume',
                          'disks': vm_helper.get_vm_devices_via_virsh(vm1)}}
        vm_helper.wait_for_vm_pingable_from_natbox(vm1)

        LOG.tc_step("Boot vm2 from volume with flavor flv_localdisk and wait "
                    "for it pingable from NatBox")
        vm2_name = "vol_ephemswap"
        vm2 = vm_helper.boot_vm(vm2_name, flavor=flavor_2, source='volume',
                                avail_zone='nova', vm_host=target_host,
                                cleanup='function')[1]

        vm_helper.wait_for_vm_pingable_from_natbox(vm2)
        vms_info[vm2] = {'ephemeral': 1,
                         'swap': 512,
                         'vm_type': 'volume',
                         'disks': vm_helper.get_vm_devices_via_virsh(vm2)}

        LOG.tc_step("Boot vm3 from image with flavor flv_rootdisk and wait for "
                    "it pingable from NatBox")
        vm3_name = "image_root"
        vm3 = vm_helper.boot_vm(vm3_name, flavor=flavor_1, source='image',
                                avail_zone='nova', vm_host=target_host,
                                cleanup='function')[1]

        vm_helper.wait_for_vm_pingable_from_natbox(vm3)
        vms_info[vm3] = {'ephemeral': 0,
                         'swap': 0,
                         'vm_type': 'image',
                         'disks': vm_helper.get_vm_devices_via_virsh(vm3)}

        LOG.tc_step("Boot vm4 from image with flavor flv_rootdisk, attach a "
                    "volume to it and wait for it "
                    "pingable from NatBox")
        vm4_name = 'image_root_attachvol'
        vm4 = vm_helper.boot_vm(vm4_name, flavor_1, source='image',
                                avail_zone='nova',
                                vm_host=target_host,
                                cleanup='function')[1]

        vol = cinder_helper.create_volume(bootable=False)[1]
        ResourceCleanup.add('volume', vol, scope='function')
        vm_helper.attach_vol_to_vm(vm4, vol_id=vol, mount=False)

        vm_helper.wait_for_vm_pingable_from_natbox(vm4)
        vms_info[vm4] = {'ephemeral': 0,
                         'swap': 0,
                         'vm_type': 'image_with_vol',
                         'disks': vm_helper.get_vm_devices_via_virsh(vm4)}

        LOG.tc_step("Boot vm5 from image with flavor flv_localdisk and wait "
                    "for it pingable from NatBox")
        vm5_name = 'image_ephemswap'
        vm5 = vm_helper.boot_vm(vm5_name, flavor_2, source='image',
                                avail_zone='nova', vm_host=target_host,
                                cleanup='function')[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm5)
        vms_info[vm5] = {'ephemeral': 1,
                         'swap': 512,
                         'vm_type': 'image',
                         'disks': vm_helper.get_vm_devices_via_virsh(vm5)}

        LOG.tc_step("Check all VMs are booted on {}".format(target_host))
        vms_on_host = vm_helper.get_vms_on_host(hostname=target_host)
        vms = [vm1, vm2, vm3, vm4, vm5]
        assert set(vms) <= set(vms_on_host), "VMs booted on host: {}. " \
                                             "Current vms on host: {}". \
            format(vms, vms_on_host)

        for vm_ in vms:
            LOG.tc_step("Touch files under vm disks {}: "
                        "{}".format(vm_, vms_info[vm_]))
            file_paths, content = touch_files_under_vm_disks(vm_,
                                                             **vms_info[vm_])
            vms_info[vm_]['file_paths'] = file_paths
            vms_info[vm_]['content'] = content

        LOG.tc_step("Reboot target host {}".format(target_host))
        vm_helper.evacuate_vms(host=target_host, vms_to_check=vms,
                               ping_vms=True)

        LOG.tc_step("Check files after evacuation")
        for vm_ in vms:
            LOG.info("--------------------Check files for vm {}".format(vm_))
            check_helper.check_vm_files(vm_id=vm_, vm_action='evacuate',
                                        storage_backing=storage_backing,
                                        prev_host=target_host, **vms_info[vm_])
        vm_helper.ping_vms_from_natbox(vms)

    @fixture(scope='function')
    def check_hosts(self):
        storage_backing, hosts = \
            keywords.host_helper.get_storage_backing_with_max_hosts()
        if len(hosts) < 2:
            skip("at least two hosts with the same storage backing are "
                 "required")

        acceptable_hosts = []
        for host in hosts:
            numa_num = len(host_helper.get_host_procs(host))
            if numa_num > 1:
                acceptable_hosts.append(host)
                if len(acceptable_hosts) == 2:
                    break
        else:
            skip("at least two hosts with multiple numa nodes are required")

        target_host = acceptable_hosts[0]
        return target_host


class TestOneHostAvail:
    @fixture(scope='class')
    def get_zone(self, request, add_stxauto_zone):
        if system_helper.is_aio_simplex():
            zone = 'nova'
            return zone

        zone = 'stxauto'
        storage_backing, hosts = \
            keywords.host_helper.get_storage_backing_with_max_hosts()
        host = hosts[0]
        LOG.fixture_step('Select host {} with backing '
                         '{}'.format(host, storage_backing))
        nova_helper.add_hosts_to_aggregate(aggregate='stxauto', hosts=[host])

        def remove_hosts_from_zone():
            nova_helper.remove_hosts_from_aggregate(aggregate='stxauto',
                                                    check_first=False)

        request.addfinalizer(remove_hosts_from_zone)
        return zone

    @mark.sx_sanity
    def test_reboot_only_host(self, get_zone):
        """
        Test reboot only hypervisor on the system

        Args:
            get_zone: fixture to create stxauto aggregate, to ensure vms can
            only on one host

        Setups:
            - If more than 1 hypervisor: Create stxauto aggregate and add
            one host to the aggregate

        Test Steps:
            - Launch various vms on target host
                - vm booted from cinder volume,
                - vm booted from glance image,
                - vm booted from glance image, and have an extra cinder
                volume attached after launch,
                - vm booed from cinder volume with ephemeral and swap disks
            - sudo reboot -f only host
            - Check host is recovered
            - Check vms are recovered and reachable from NatBox

        """
        zone = get_zone

        LOG.tc_step("Launch 5 vms in {} zone".format(zone))
        vms = vm_helper.boot_vms_various_types(avail_zone=zone,
                                               cleanup='function')
        target_host = vm_helper.get_vm_host(vm_id=vms[0])
        for vm in vms[1:]:
            vm_host = vm_helper.get_vm_host(vm)
            assert target_host == vm_host, "VMs are not booted on same host"

        LOG.tc_step("Reboot -f from target host {}".format(target_host))
        HostsToRecover.add(target_host)
        host_helper.reboot_hosts(target_host)

        LOG.tc_step("Check vms are in Active state after host come back up")
        res, active_vms, inactive_vms = vm_helper.wait_for_vms_values(
            vms=vms, value=VMStatus.ACTIVE, timeout=600)

        vms_host_err = []
        for vm in vms:
            if vm_helper.get_vm_host(vm) != target_host:
                vms_host_err.append(vm)

        assert not vms_host_err, "Following VMs are not on the same host {}: " \
                                 "{}\nVMs did not reach Active state: {}". \
            format(target_host, vms_host_err, inactive_vms)

        assert not inactive_vms, "VMs did not reach Active state after " \
                                 "evacuated to other host: " \
                                 "{}".format(inactive_vms)

        LOG.tc_step("Check VMs are pingable from NatBox after evacuation")
        vm_helper.wait_for_vm_pingable_from_natbox(vms,
                                                   timeout=VMTimeout.DHCP_RETRY)
