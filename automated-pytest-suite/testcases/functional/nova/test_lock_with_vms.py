#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import random

from pytest import fixture, mark, skip

import keywords.host_helper
from utils.tis_log import LOG
from consts.reasons import SkipStorageBacking
from consts.stx import VMStatus, SysType
from consts.timeout import VMTimeout
from testfixtures.recover_hosts import HostsToRecover
from keywords import vm_helper, nova_helper, host_helper, system_helper


@fixture(scope='module', autouse=True)
def update_instances_quota():
    vm_helper.ensure_vms_quotas()


def _boot_migrable_vms(storage_backing):
    """
    Create vms with specific storage backing that can be live migrated

    Args:
        storage_backing: 'local_image' or 'remote'

    Returns: (vms_info (list), flavors_created (list))
        vms_info : [(vm_id1, block_mig1), (vm_id2, block_mig2), ...]

    """
    vms_to_test = []
    flavors_created = []
    flavor_no_localdisk = nova_helper.create_flavor(
        ephemeral=0, swap=0, storage_backing=storage_backing)[1]
    flavors_created.append(flavor_no_localdisk)

    vm_1 = vm_helper.boot_vm(flavor=flavor_no_localdisk, source='volume')[1]

    block_mig_1 = False
    vms_to_test.append((vm_1, block_mig_1))

    LOG.info("Boot a VM from image if host storage backing is local_image or "
             "remote...")
    vm_2 = vm_helper.boot_vm(flavor=flavor_no_localdisk, source='image')[1]
    block_mig_2 = True
    vms_to_test.append((vm_2, block_mig_2))
    if storage_backing == 'remote':
        LOG.info("Boot a VM from volume with local disks if storage backing "
                 "is remote...")
        ephemeral_swap = random.choice([[0, 512], [1, 512], [1, 0]])
        flavor_with_localdisk = nova_helper.create_flavor(
            ephemeral=ephemeral_swap[0], swap=ephemeral_swap[1])[1]
        flavors_created.append(flavor_with_localdisk)
        vm_3 = vm_helper.boot_vm(flavor=flavor_with_localdisk,
                                 source='volume')[1]
        block_mig_3 = False
        vms_to_test.append((vm_3, block_mig_3))
        LOG.info("Boot a VM from image with volume attached if "
                 "storage backing is remote...")
        vm_4 = vm_helper.boot_vm(flavor=flavor_no_localdisk, source='image')[1]
        vm_helper.attach_vol_to_vm(vm_id=vm_4)
        block_mig_4 = False
        vms_to_test.append((vm_4, block_mig_4))

    return vms_to_test, flavors_created


class TestLockWithVMs:
    @fixture()
    def target_hosts(self):
        """
        Test fixture for test_lock_with_vms().
        Calculate target host(s) to perform lock based on storage backing of
        vms_to_test, and live migrate suitable vms
        to target host before test start.
        """

        storage_backing, target_hosts = \
            keywords.host_helper.get_storage_backing_with_max_hosts()
        if len(target_hosts) < 2:
            skip(SkipStorageBacking.LESS_THAN_TWO_HOSTS_WITH_BACKING.
                 format(storage_backing))

        target_host = target_hosts[0]
        if SysType.AIO_DX == system_helper.get_sys_type():
            target_host = system_helper.get_standby_controller_name()

        return storage_backing, target_host

    @mark.nightly
    def test_lock_with_vms(self, target_hosts, no_simplex, add_admin_role_func):
        """
        Test lock host with vms on it.

        Args:
            target_hosts (list): targeted host(s) to lock that was prepared
            by the target_hosts test fixture.

        Skip Conditions:
            - Less than 2 hypervisor hosts on the system

        Prerequisites:
            - Hosts storage backing are pre-configured to storage backing
            under test
                ie., 2 or more hosts should support the storage backing under
                test.
        Test Setups:
            - Set instances quota to 10 if it was less than 8
            - Determine storage backing(s) under test. i.e.,storage backings
            supported by at least 2 hosts on the system
            - Create flavors with storage extra specs set based on storage
            backings under test
            - Create vms_to_test that can be live migrated using created flavors
            - Determine target host(s) to perform lock based on which host(s)
            have the most vms_to_test
            - Live migrate vms to target host(s)
        Test Steps:
            - Lock target host
            - Verify lock succeeded and vms status unchanged
            - Repeat above steps if more than one target host
        Test Teardown:
            - Delete created vms and volumes
            - Delete created flavors
            - Unlock locked target host(s)

        """
        storage_backing, host = target_hosts
        vms_num = 5
        vm_helper.ensure_vms_quotas(vms_num=vms_num)

        LOG.tc_step("Boot {} vms with various storage settings".format(vms_num))
        vms = vm_helper.boot_vms_various_types(cleanup='function',
                                               vms_num=vms_num,
                                               storage_backing=storage_backing,
                                               target_host=host)

        LOG.tc_step("Attempt to lock target host {}...".format(host))
        HostsToRecover.add(host)
        host_helper.lock_host(host=host, check_first=False, fail_ok=False,
                              swact=True)

        LOG.tc_step("Verify lock succeeded and vms still in good state")
        vm_helper.wait_for_vms_values(vms=vms, fail_ok=False)
        for vm in vms:
            vm_host = vm_helper.get_vm_host(vm_id=vm)
            assert vm_host != host, "VM is still on {} after lock".format(host)

            vm_helper.wait_for_vm_pingable_from_natbox(
                vm_id=vm, timeout=VMTimeout.DHCP_RETRY)

    @mark.sx_nightly
    def test_lock_with_max_vms_simplex(self, simplex_only):
        vms_num = host_helper.get_max_vms_supported(host='controller-0')
        vm_helper.ensure_vms_quotas(vms_num=vms_num)

        LOG.tc_step("Boot {} vms with various storage settings".format(vms_num))
        vms = vm_helper.boot_vms_various_types(cleanup='function',
                                               vms_num=vms_num)

        LOG.tc_step("Lock vm host on simplex system")
        HostsToRecover.add('controller-0')
        host_helper.lock_host('controller-0')

        LOG.tc_step("Ensure vms are in {} state after locked host come "
                    "online".format(VMStatus.STOPPED))
        vm_helper.wait_for_vms_values(vms, value=VMStatus.STOPPED,
                                      fail_ok=False)

        LOG.tc_step("Unlock host on simplex system")
        host_helper.unlock_host(host='controller-0')

        LOG.tc_step("Ensure vms are Active and Pingable from NatBox")
        vm_helper.wait_for_vms_values(vms, value=VMStatus.ACTIVE,
                                      fail_ok=False, timeout=600)
        for vm in vms:
            vm_helper.wait_for_vm_pingable_from_natbox(
                vm, timeout=VMTimeout.DHCP_RETRY)
