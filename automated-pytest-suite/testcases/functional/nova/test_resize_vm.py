#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time
import math

from pytest import fixture, mark, skip, param

from utils.tis_log import LOG

from keywords import vm_helper, nova_helper, host_helper, check_helper, \
    glance_helper
from testfixtures.fixture_resources import ResourceCleanup
from consts.stx import FlavorSpec, GuestImages
from consts.reasons import SkipStorageBacking


def id_gen(val):
    if isinstance(val, (tuple, list)):
        val = '_'.join([str(val_) for val_ in val])
    return val


def touch_files_under_vm_disks(vm_id, ephemeral=0, swap=0, vm_type='volume',
                               disks=None):
    expt_len = 1 + int(bool(ephemeral)) + int(bool(swap)) + (
        1 if 'with_vol' in vm_type else 0)

    LOG.tc_step("Auto mount non-root disk(s)")
    mounts = vm_helper.auto_mount_vm_disks(vm_id=vm_id, disks=disks)
    assert expt_len == len(mounts)

    if bool(swap):
        mounts.remove('none')

    LOG.tc_step("Create files under vm disks: {}".format(mounts))
    file_paths, content = vm_helper.touch_files(vm_id=vm_id, file_dirs=mounts)
    return file_paths, content


def get_expt_disk_increase(origin_flavor, dest_flavor, boot_source,
                           storage_backing):
    root_diff = dest_flavor[0] - origin_flavor[0]
    ephemeral_diff = dest_flavor[1] - origin_flavor[1]
    swap_diff = (dest_flavor[2] - origin_flavor[2]) / 1024

    if storage_backing == 'remote':
        expected_increase = 0
        expect_to_check = True
    else:
        if boot_source == 'volume':
            expected_increase = ephemeral_diff + swap_diff
            expect_to_check = False
        else:
            expected_increase = root_diff + ephemeral_diff + swap_diff
            expect_to_check = expected_increase >= 2

    return expected_increase, expect_to_check


def get_disk_avail_least(host):
    return \
        host_helper.get_hypervisor_info(hosts=host,
                                        field='disk_available_least')[host]


def check_correct_post_resize_value(original_disk_value, expected_increase,
                                    host, sleep=True):
    if sleep:
        time.sleep(65)

    post_resize_value = get_disk_avail_least(host)
    LOG.info(
        "{} original_disk_value: {}. post_resize_value: {}. "
        "expected_increase: {}".format(
            host, original_disk_value, post_resize_value, expected_increase))
    expt_post = original_disk_value + expected_increase

    if expected_increase < 0:
        # vm is on this host, backup image files may be created if not
        # already existed
        backup_val = math.ceil(
            glance_helper.get_image_size(guest_os=GuestImages.DEFAULT['guest'],
                                         virtual_size=False))
        assert expt_post - backup_val <= post_resize_value <= expt_post
    elif expected_increase > 0:
        # vm moved away from this host, or resized to smaller disk on same
        # host, backup files will stay
        assert expt_post - 1 <= post_resize_value <= expt_post + 1, \
            "disk_available_least on {} expected: {}+-1, actual: {}".format(
                host, expt_post, post_resize_value)
    else:
        assert expt_post == post_resize_value, \
            "{} disk_available_least value changed to {} unexpectedly".format(
                host, post_resize_value)

    return post_resize_value


@fixture(scope='module')
def get_hosts_per_backing(add_admin_role_module):
    return host_helper.get_hosts_per_storage_backing()


class TestResizeSameHost:
    @fixture(scope='class')
    def add_hosts_to_zone(self, request, add_stxauto_zone,
                          get_hosts_per_backing):
        hosts_per_backing = get_hosts_per_backing
        avail_hosts = {key: vals[0] for key, vals in hosts_per_backing.items()
                       if vals}

        if not avail_hosts:
            skip("No host in any storage aggregate")

        nova_helper.add_hosts_to_aggregate(aggregate='stxauto',
                                           hosts=list(avail_hosts.values()))

        def remove_hosts_from_zone():
            nova_helper.remove_hosts_from_aggregate(aggregate='stxauto',
                                                    check_first=False)

        request.addfinalizer(remove_hosts_from_zone)
        return avail_hosts

    @mark.parametrize(('storage_backing', 'origin_flavor', 'dest_flavor',
                       'boot_source'), [
                          ('remote', (4, 0, 0), (5, 1, 512), 'image'),
                          ('remote', (4, 1, 512), (5, 2, 1024), 'image'),
                          ('remote', (4, 1, 512), (4, 1, 0), 'image'),
                          # LP1762423
                          param('remote', (4, 0, 0), (1, 1, 512), 'volume',
                                marks=mark.priorities('nightly', 'sx_nightly')),
                          ('remote', (4, 1, 512), (8, 2, 1024), 'volume'),
                          ('remote', (4, 1, 512), (0, 1, 0), 'volume'),
                          ('local_image', (4, 0, 0), (5, 1, 512), 'image'),
                          param('local_image', (4, 1, 512), (5, 2, 1024),
                                'image',
                                marks=mark.priorities('nightly', 'sx_nightly')),
                          ('local_image', (5, 1, 512), (5, 1, 0), 'image'),
                          ('local_image', (4, 0, 0), (5, 1, 512), 'volume'),
                          ('local_image', (4, 1, 512), (0, 2, 1024), 'volume'),
                          ('local_image', (4, 1, 512), (1, 1, 0), 'volume'),
                          # LP1762423
                      ], ids=id_gen)
    def test_resize_vm_positive(self, add_hosts_to_zone, storage_backing,
                                origin_flavor, dest_flavor, boot_source):
        """
        Test resizing disks of a vm
        - Resize root disk is allowed except 0 & boot-from-image
        - Resize to larger or same ephemeral is allowed
        - Resize swap to any size is allowed including removing

        Args:
            storage_backing: The host storage backing required
            origin_flavor: The flavor to boot the vm from, listed by GBs for
            root, ephemeral, and swap disks, i.e. for a
                           system with a 2GB root disk, a 1GB ephemeral disk,
                           and no swap disk: (2, 1, 0)
            boot_source: Which source to boot the vm from, either 'volume' or
            'image'
            add_hosts_to_zone
            dest_flavor

        Skip Conditions:
            - No hosts exist with required storage backing.
        Test setup:
            - Put a single host of each backing in stxautozone to prevent
            migration and instead force resize.
            - Create two flavors based on origin_flavor and dest_flavor
            - Create a volume or image to boot from.
            - Boot VM with origin_flavor
        Test Steps:
            - Resize VM to dest_flavor with revert
            - If vm is booted from image and has a non-remote backing,
            check that the amount of disk space post-revert
            is around the same pre-revert    # TC5155
            - Resize VM to dest_flavor with confirm
            - If vm is booted from image and has a non-remote backing,
            check that the amount of disk space post-confirm
            is reflects the increase in disk-space taken up      # TC5155
        Test Teardown:
            - Delete created VM
            - Delete created volume or image
            - Delete created flavors
            - Remove hosts from stxautozone
            - Delete stxautozone

        """
        vm_host = add_hosts_to_zone.get(storage_backing, None)

        if not vm_host:
            skip(
                SkipStorageBacking.NO_HOST_WITH_BACKING.format(storage_backing))

        expected_increase, expect_to_check = get_expt_disk_increase(
            origin_flavor, dest_flavor,
            boot_source, storage_backing)
        LOG.info("Expected_increase of vm compute occupancy is {}".format(
            expected_increase))

        LOG.tc_step('Create origin flavor')
        origin_flavor_id = _create_flavor(origin_flavor, storage_backing)
        vm_id = _boot_vm_to_test(boot_source, vm_host, origin_flavor_id)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

        vm_disks = vm_helper.get_vm_devices_via_virsh(vm_id)
        root, ephemeral, swap = origin_flavor
        if boot_source == 'volume':
            root = GuestImages.IMAGE_FILES[GuestImages.DEFAULT['guest']][1]
        file_paths, content = touch_files_under_vm_disks(vm_id=vm_id,
                                                         ephemeral=ephemeral,
                                                         swap=swap,
                                                         vm_type=boot_source,
                                                         disks=vm_disks)

        if expect_to_check:
            LOG.tc_step('Check initial disk usage')
            original_disk_value = get_disk_avail_least(vm_host)
            LOG.info("{} space left on compute".format(original_disk_value))

        LOG.tc_step('Create destination flavor')
        dest_flavor_id = _create_flavor(dest_flavor, storage_backing)
        LOG.tc_step('Resize vm to dest flavor and revert')
        vm_helper.resize_vm(vm_id, dest_flavor_id, revert=True, fail_ok=False)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

        swap_size = swap
        LOG.tc_step("Check files after resize revert")
        if storage_backing == 'remote' and swap and dest_flavor[2]:
            swap_size = dest_flavor[2]

        time.sleep(30)
        prev_host = vm_helper.get_vm_host(vm_id)
        check_helper.check_vm_files(vm_id=vm_id,
                                    storage_backing=storage_backing, root=root,
                                    ephemeral=ephemeral,
                                    swap=swap_size, vm_type=boot_source,
                                    vm_action=None, file_paths=file_paths,
                                    content=content, disks=vm_disks,
                                    check_volume_root=True)

        LOG.tc_step('Resize vm to dest flavor and confirm')
        vm_helper.resize_vm(vm_id, dest_flavor_id, revert=False, fail_ok=False)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
        post_host = vm_helper.get_vm_host(vm_id)
        post_root, post_ephemeral, post_swap = dest_flavor
        if boot_source == 'volume':
            post_root = GuestImages.IMAGE_FILES[GuestImages.DEFAULT['guest']][1]
        post_ephemeral = ephemeral if ephemeral else post_ephemeral
        LOG.tc_step("Check files after resize attempt")
        check_helper.check_vm_files(
            vm_id=vm_id, storage_backing=storage_backing,
            ephemeral=post_ephemeral,
            swap=post_swap, vm_type=boot_source,
            vm_action='resize', file_paths=file_paths,
            content=content, prev_host=prev_host,
            post_host=post_host, root=post_root,
            disks=vm_disks,
            post_disks=vm_helper.get_vm_devices_via_virsh(vm_id),
            check_volume_root=True)

    @mark.parametrize(
        ('storage_backing', 'origin_flavor', 'dest_flavor', 'boot_source'), [
            # Root disk can be resized, but cannot be 0
            ('remote', (5, 0, 0), (0, 0, 0), 'image'),
            # check ephemeral disk cannot be smaller than origin
            ('remote', (5, 2, 512), (5, 1, 512), 'image'),
            # check ephemeral disk cannot be smaller than origin
            ('remote', (1, 1, 512), (1, 0, 512), 'volume'),
            # Root disk can be resized, but cannot be 0
            ('local_image', (5, 0, 0), (0, 0, 0), 'image'),
            ('local_image', (5, 2, 512), (5, 1, 512), 'image'),
            ('local_image', (5, 1, 512), (4, 1, 512), 'image'),
            ('local_image', (5, 1, 512), (4, 1, 0), 'image'),
            ('local_image', (1, 1, 512), (1, 0, 512), 'volume'),
        ], ids=id_gen)
    def test_resize_vm_negative(self, add_hosts_to_zone, storage_backing,
                                origin_flavor, dest_flavor, boot_source):
        """
        Test resizing disks of a vm not allowed:
        - Resize to smaller ephemeral flavor is not allowed
        - Resize to zero disk flavor is not allowed     (boot from image only)

        Args:
            storage_backing: The host storage backing required
            origin_flavor: The flavor to boot the vm from, listed by GBs for
            root, ephemeral, and swap disks, i.e. for a
                           system with a 2GB root disk, a 1GB ephemeral disk,
                           and no swap disk: (2, 1, 0)
            boot_source: Which source to boot the vm from, either 'volume' or
            'image'
        Skip Conditions:
            - No hosts exist with required storage backing.
        Test setup:
            - Put a single host of each backing in stxautozone to prevent
            migration and instead force resize.
            - Create two flavors based on origin_flavor and dest_flavor
            - Create a volume or image to boot from.
            - Boot VM with origin_flavor
        Test Steps:
            - Resize VM to dest_flavor with revert
            - Resize VM to dest_flavor with confirm
        Test Teardown:
            - Delete created VM
            - Delete created volume or image
            - Delete created flavors
            - Remove hosts from stxauto zone
            - Delete stxauto zone

        """
        vm_host = add_hosts_to_zone.get(storage_backing, None)

        if not vm_host:
            skip("No available host with {} storage backing".format(
                storage_backing))

        LOG.tc_step('Create origin flavor')
        origin_flavor_id = _create_flavor(origin_flavor, storage_backing)
        LOG.tc_step('Create destination flavor')
        dest_flavor_id = _create_flavor(dest_flavor, storage_backing)
        vm_id = _boot_vm_to_test(boot_source, vm_host, origin_flavor_id)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

        vm_disks = vm_helper.get_vm_devices_via_virsh(vm_id)
        root, ephemeral, swap = origin_flavor
        file_paths, content = touch_files_under_vm_disks(vm_id=vm_id,
                                                         ephemeral=ephemeral,
                                                         swap=swap,
                                                         vm_type=boot_source,
                                                         disks=vm_disks)

        LOG.tc_step('Resize vm to dest flavor')
        code, output = vm_helper.resize_vm(vm_id, dest_flavor_id, fail_ok=True)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

        assert vm_helper.get_vm_flavor(
            vm_id) == origin_flavor_id, 'VM did not keep origin flavor'
        assert code > 0, "Resize VM CLI is not rejected"

        LOG.tc_step("Check files after resize attempt")
        check_helper.check_vm_files(vm_id=vm_id,
                                    storage_backing=storage_backing, root=root,
                                    ephemeral=ephemeral,
                                    swap=swap, vm_type=boot_source,
                                    vm_action=None, file_paths=file_paths,
                                    content=content, disks=vm_disks)


def _create_flavor(flavor_info, storage_backing):
    root_disk = flavor_info[0]
    ephemeral = flavor_info[1]
    swap = flavor_info[2]

    flavor_id = nova_helper.create_flavor(ephemeral=ephemeral, swap=swap,
                                          root_disk=root_disk,
                                          storage_backing=storage_backing)[1]
    ResourceCleanup.add('flavor', flavor_id)
    return flavor_id


def _boot_vm_to_test(boot_source, vm_host, flavor_id):
    LOG.tc_step('Boot a vm with given flavor')
    vm_id = vm_helper.boot_vm(flavor=flavor_id, avail_zone='stxauto',
                              vm_host=vm_host, source=boot_source,
                              cleanup='function')[1]
    return vm_id


def get_cpu_count(hosts_with_backing):
    LOG.fixture_step("Find suitable vm host and cpu count and backing of host")
    compute_space_dict = {}

    vm_host = hosts_with_backing[0]
    numa0_used_cpus, numa0_total_cpus = \
        host_helper.get_vcpus_per_proc(vm_host)[vm_host][0]
    numa0_avail_cpus = len(numa0_total_cpus) - len(numa0_used_cpus)
    for host in hosts_with_backing:
        free_space = get_disk_avail_least(host)
        compute_space_dict[host] = free_space
        LOG.info("{} space on {}".format(free_space, host))

    # increase quota
    LOG.fixture_step("Increase quota of allotted cores")
    vm_helper.ensure_vms_quotas(cores_num=int(numa0_avail_cpus + 30))

    return vm_host, numa0_avail_cpus, compute_space_dict


class TestResizeDiffHost:
    @mark.parametrize('storage_backing', [
        'local_image',
        'remote',
    ])
    def test_resize_different_comp_node(self, storage_backing,
                                        get_hosts_per_backing):
        """
        Test resizing disks of a larger vm onto a different compute node and
        check hypervisor statistics to
        make sure difference in disk usage of both nodes involved is
        correctly reflected

        Args:
            storage_backing: The host storage backing required
        Skip Conditions:
            - 2 hosts must exist with required storage backing.
        Test setup:
            - For each of the two backings tested, the setup will return the
            number of nodes for each backing,
            the vm host that the vm will initially be created on and the
            number of hosts for that backing.
        Test Steps:
            - Create a flavor with a root disk size that is slightly larger
            than the default image used to boot up
            the VM
            - Create a VM with the aforementioned flavor
            - Create a flavor will enough cpus to occupy the rest of the cpus
            on the same host as the first VM
            - Create another VM on the same host as the first VM
            - Create a similar flavor to the first one, except that it has
            one more vcpu
            - Resize the first VM and confirm that it is on a different host
            - Check hypervisor-show on both computes to make sure that disk
            usage goes down on the original host and
              goes up on the new host
        Test Teardown:
            - Delete created VMs
            - Delete created flavors

        """
        hosts_with_backing = get_hosts_per_backing.get(storage_backing, [])
        if len(hosts_with_backing) < 2:
            skip(SkipStorageBacking.LESS_THAN_TWO_HOSTS_WITH_BACKING.format(
                storage_backing))

        origin_host, cpu_count, compute_space_dict = get_cpu_count(
            hosts_with_backing)

        root_disk_size = \
            GuestImages.IMAGE_FILES[GuestImages.DEFAULT['guest']][1] + 5

        # make vm (1 cpu)
        LOG.tc_step("Create flavor with 1 cpu")
        numa0_specs = {FlavorSpec.CPU_POLICY: 'dedicated', FlavorSpec.NUMA_0: 0}
        flavor_1 = \
            nova_helper.create_flavor(ephemeral=0, swap=0,
                                      root_disk=root_disk_size, vcpus=1,
                                      storage_backing=storage_backing)[1]
        ResourceCleanup.add('flavor', flavor_1)
        nova_helper.set_flavor(flavor_1, **numa0_specs)

        LOG.tc_step("Boot a vm with above flavor")
        vm_to_resize = \
            vm_helper.boot_vm(flavor=flavor_1, source='image',
                              cleanup='function', vm_host=origin_host)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm_to_resize)

        # launch another vm
        LOG.tc_step("Create a flavor to occupy vcpus")
        occupy_amount = int(cpu_count) - 1
        second_specs = {FlavorSpec.CPU_POLICY: 'dedicated',
                        FlavorSpec.NUMA_0: 0}
        flavor_2 = nova_helper.create_flavor(vcpus=occupy_amount,
                                             storage_backing=storage_backing)[1]
        ResourceCleanup.add('flavor', flavor_2)
        nova_helper.set_flavor(flavor_2, **second_specs)

        LOG.tc_step("Boot a vm with above flavor to occupy remaining vcpus")
        vm_2 = vm_helper.boot_vm(flavor=flavor_2, source='image',
                                 cleanup='function', vm_host=origin_host)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm_2)

        LOG.tc_step('Check disk usage before resize')
        prev_val_origin_host = get_disk_avail_least(origin_host)
        LOG.info("{} space left on compute".format(prev_val_origin_host))

        # create a larger flavor and resize
        LOG.tc_step("Create a flavor that has an extra vcpu to force resize "
                    "to a different node")
        resize_flavor = nova_helper.create_flavor(
            ephemeral=0, swap=0, root_disk=root_disk_size, vcpus=2,
            storage_backing=storage_backing)[1]
        ResourceCleanup.add('flavor', resize_flavor)
        nova_helper.set_flavor(resize_flavor, **numa0_specs)

        LOG.tc_step("Resize the vm and verify if it is on a different host")
        vm_helper.resize_vm(vm_to_resize, resize_flavor)
        new_host = vm_helper.get_vm_host(vm_to_resize)
        assert new_host != origin_host, "vm did not change hosts " \
                                        "following resize"

        LOG.tc_step('Check disk usage on computes after resize')
        if storage_backing == 'remote':
            LOG.info("Compute disk usage change should be minimal for "
                     "remote storage backing")
            root_disk_size = 0

        check_correct_post_resize_value(prev_val_origin_host, root_disk_size,
                                        origin_host)

        prev_val_new_host = compute_space_dict[new_host]
        check_correct_post_resize_value(prev_val_new_host, -root_disk_size,
                                        new_host, sleep=False)
        vm_helper.wait_for_vm_pingable_from_natbox(vm_to_resize)
