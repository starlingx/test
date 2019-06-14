#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture, mark, skip, param

from utils.tis_log import LOG
from consts.stx import FlavorSpec, EventLogID
# Don't remove this import, used by eval()
from consts.cli_errs import LiveMigErr
from keywords import vm_helper, nova_helper, host_helper, cinder_helper, \
    glance_helper, check_helper, system_helper
from testfixtures.fixture_resources import ResourceCleanup


@fixture(scope='module')
def check_system():
    up_hypervisors = host_helper.get_up_hypervisors()
    if len(up_hypervisors) < 2:
        skip("Less than two up hypervisors")


@fixture(scope='module')
def hosts_per_stor_backing(check_system):
    hosts_per_backing = host_helper.get_hosts_per_storage_backing()
    LOG.fixture_step("Hosts per storage backing: {}".format(hosts_per_backing))

    return hosts_per_backing


def touch_files_under_vm_disks(vm_id, ephemeral=0, swap=0, vm_type='volume',
                               disks=None):
    expt_len = 1 + int(bool(ephemeral)) + int(bool(swap)) + (
        1 if 'with_vol' in vm_type else 0)

    LOG.tc_step("Auto mount ephemeral, swap, and attached volume if any")
    mounts = vm_helper.auto_mount_vm_disks(vm_id=vm_id, disks=disks)
    assert expt_len == len(mounts)

    LOG.tc_step("Create files under vm disks: {}".format(mounts))
    file_paths, content = vm_helper.touch_files(vm_id=vm_id, file_dirs=mounts)
    return file_paths, content


@mark.parametrize(('storage_backing', 'ephemeral', 'swap', 'cpu_pol', 'vcpus',
                   'vm_type', 'block_mig'), [
                      param('local_image', 0, 0, None, 1, 'volume', False,
                            marks=mark.p1),
                      param('local_image', 0, 0, 'dedicated', 2, 'volume',
                            False, marks=mark.p1),
                      ('local_image', 1, 0, 'dedicated', 2, 'volume', False),
                      ('local_image', 0, 512, 'shared', 1, 'volume', False),
                      ('local_image', 1, 512, 'dedicated', 2, 'volume', True),
                      # Supported from Newton
                      param('local_image', 0, 0, 'shared', 2, 'image', True,
                            marks=mark.domain_sanity),
                      param('local_image', 1, 512, 'dedicated', 1, 'image',
                            False, marks=mark.domain_sanity),
                      ('local_image', 0, 0, None, 2, 'image_with_vol', False),
                      ('local_image', 0, 0, 'dedicated', 1, 'image_with_vol',
                       True),
                      ('local_image', 1, 512, 'dedicated', 2, 'image_with_vol',
                       True),
                      ('local_image', 1, 512, 'dedicated', 1, 'image_with_vol',
                       False),
                      param('remote', 0, 0, None, 2, 'volume', False,
                            marks=mark.p1),
                      param('remote', 1, 0, 'dedicated', 1, 'volume', False,
                            marks=mark.p1),
                      param('remote', 1, 512, None, 1, 'image', False,
                            marks=mark.domain_sanity),
                      param('remote', 0, 512, 'dedicated', 2, 'image_with_vol',
                            False, marks=mark.domain_sanity),
                  ])
def test_live_migrate_vm_positive(hosts_per_stor_backing, storage_backing,
                                  ephemeral, swap, cpu_pol, vcpus, vm_type,
                                  block_mig):
    """
    Skip Condition:
        - Less than two hosts have specified storage backing

    Test Steps:
        - create flavor with specified vcpus, cpu_policy, ephemeral, swap,
        storage_backing
        - boot vm from specified boot source with above flavor
        - (attach volume to vm if 'image_with_vol', specified in vm_type)
        - Live migrate the vm with specified block_migration flag
        - Verify VM is successfully live migrated to different host

    Teardown:
        - Delete created vm, volume, flavor

    """
    if len(hosts_per_stor_backing.get(storage_backing, [])) < 2:
        skip("Less than two hosts have {} storage backing".format(
            storage_backing))

    vm_id = _boot_vm_under_test(storage_backing, ephemeral, swap, cpu_pol,
                                vcpus, vm_type)

    prev_vm_host = vm_helper.get_vm_host(vm_id)
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    vm_disks = vm_helper.get_vm_devices_via_virsh(vm_id)
    file_paths, content = touch_files_under_vm_disks(vm_id=vm_id,
                                                     ephemeral=ephemeral,
                                                     swap=swap, vm_type=vm_type,
                                                     disks=vm_disks)

    LOG.tc_step("Live migrate VM and ensure it succeeded")
    # block_mig = True if boot_source == 'image' else False
    code, output = vm_helper.live_migrate_vm(vm_id, block_migrate=block_mig)
    assert 0 == code, "Live migrate is not successful. Details: {}".format(
        output)

    post_vm_host = vm_helper.get_vm_host(vm_id)
    assert prev_vm_host != post_vm_host

    LOG.tc_step("Ensure vm is pingable from NatBox after live migration")
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    LOG.tc_step("Check files after live migrate")
    check_helper.check_vm_files(vm_id=vm_id, storage_backing=storage_backing,
                                ephemeral=ephemeral, swap=swap,
                                vm_type=vm_type, vm_action='live_migrate',
                                file_paths=file_paths, content=content,
                                disks=vm_disks, prev_host=prev_vm_host,
                                post_host=post_vm_host)


@mark.parametrize(('storage_backing', 'ephemeral', 'swap', 'vm_type',
                   'block_mig', 'expt_err'), [
                      param('local_image', 0, 0, 'volume', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                      param('remote', 0, 0, 'volume', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                      param('remote', 1, 0, 'volume', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                      param('remote', 0, 512, 'volume', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                      param('remote', 0, 512, 'image', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                      param('remote', 0, 0, 'image_with_vol', True,
                            'LiveMigErr.BLOCK_MIG_UNSUPPORTED'),
                  ])
def test_live_migrate_vm_negative(storage_backing, ephemeral, swap, vm_type,
                                  block_mig, expt_err,
                                  hosts_per_stor_backing, no_simplex):
    """
    Skip Condition:
        - Less than two hosts have specified storage backing

    Test Steps:
        - create flavor with specified vcpus, cpu_policy, ephemeral, swap,
        storage_backing
        - boot vm from specified boot source with above flavor
        - (attach volume to vm if 'image_with_vol', specified in vm_type)
        - Live migrate the vm with specified block_migration flag
        - Verify VM is successfully live migrated to different host

    Teardown:
        - Delete created vm, volume, flavor

    """
    if len(hosts_per_stor_backing.get(storage_backing, [])) < 2:
        skip("Less than two hosts have {} storage backing".format(
            storage_backing))

    vm_id = _boot_vm_under_test(storage_backing, ephemeral, swap, None, 1,
                                vm_type)
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    prev_vm_host = vm_helper.get_vm_host(vm_id)
    vm_disks = vm_helper.get_vm_devices_via_virsh(vm_id)
    file_paths, content = touch_files_under_vm_disks(vm_id=vm_id,
                                                     ephemeral=ephemeral,
                                                     swap=swap, vm_type=vm_type,
                                                     disks=vm_disks)

    LOG.tc_step(
        "Live migrate VM and ensure it's rejected with proper error message")
    # block_mig = True if boot_source == 'image' else False
    code, output = vm_helper.live_migrate_vm(vm_id, block_migrate=block_mig)
    assert 2 == code, "Expect live migration to have expected fail. Actual: " \
                      "{}".format(output)

    # Remove below code due to live-migration is async in newton
    # assert 'Unexpected API Error'.lower() not in output.lower(),
    # "'Unexpected API Error' returned."
    #
    # # remove extra spaces in error message
    # output = re.sub(r'\s\s+', " ", output)
    # assert eval(expt_err) in output, "Expected error message {} is not in
    # actual error message: {}".\
    #     format(eval(expt_err), output)

    post_vm_host = vm_helper.get_vm_host(vm_id)
    assert prev_vm_host == post_vm_host, "VM host changed even though live " \
                                         "migration request rejected."

    LOG.tc_step(
        "Ensure vm is pingable from NatBox after live migration rejected")
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    LOG.tc_step("Check files after live migrate attempt")
    check_helper.check_vm_files(vm_id=vm_id, storage_backing=storage_backing,
                                ephemeral=ephemeral, swap=swap,
                                vm_type=vm_type, vm_action='live_migrate',
                                file_paths=file_paths, content=content,
                                disks=vm_disks, prev_host=prev_vm_host,
                                post_host=post_vm_host)


@mark.parametrize(('storage_backing', 'ephemeral', 'swap', 'cpu_pol',
                   'vcpus', 'vm_type', 'resize'), [
    param('local_image', 0, 0, None, 1, 'volume', 'confirm'),
    param('local_image', 0, 0, 'dedicated', 2, 'volume', 'confirm'),
    param('local_image', 1, 0, 'shared', 2, 'image', 'confirm'),
    param('local_image', 0, 512, 'dedicated', 1, 'image', 'confirm'),
    param('local_image', 0, 0, None, 1, 'image_with_vol', 'confirm'),
    param('remote', 0, 0, None, 2, 'volume', 'confirm'),
    param('remote', 1, 0, None, 1, 'volume', 'confirm'),
    param('remote', 1, 512, None, 1, 'image', 'confirm'),
    param('remote', 0, 0, None, 2, 'image_with_vol', 'confirm'),
    param('local_image', 0, 0, None, 2, 'volume', 'revert'),
    param('local_image', 0, 0, 'dedicated', 1, 'volume', 'revert'),
    param('local_image', 1, 0, 'shared', 2, 'image', 'revert'),
    param('local_image', 0, 512, 'dedicated', 1, 'image', 'revert'),
    param('local_image', 0, 0, 'dedicated', 2, 'image_with_vol', 'revert'),
    param('remote', 0, 0, None, 2, 'volume', 'revert'),
    param('remote', 1, 512, None, 1, 'volume', 'revert'),
    param('remote', 0, 0, None, 1, 'image', 'revert'),
    param('remote', 1, 0, None, 2, 'image_with_vol', 'revert'),
])
def test_cold_migrate_vm(storage_backing, ephemeral, swap, cpu_pol, vcpus,
                         vm_type, resize, hosts_per_stor_backing,
                         no_simplex):
    """
    Skip Condition:
        - Less than two hosts have specified storage backing

    Test Steps:
        - create flavor with specified vcpus, cpu_policy, ephemeral, swap,
        storage_backing
        - boot vm from specified boot source with above flavor
        - (attach volume to vm if 'image_with_vol', specified in vm_type)
        - Cold migrate vm
        - Confirm/Revert resize as specified
        - Verify VM is successfully cold migrated and confirmed/reverted resize
        - Verify that instance files are not found on original host. (TC6621)

    Teardown:
        - Delete created vm, volume, flavor

    """
    if len(hosts_per_stor_backing.get(storage_backing, [])) < 2:
        skip("Less than two hosts have {} storage backing".format(
            storage_backing))

    vm_id = _boot_vm_under_test(storage_backing, ephemeral, swap, cpu_pol,
                                vcpus, vm_type)
    prev_vm_host = vm_helper.get_vm_host(vm_id)
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    vm_disks = vm_helper.get_vm_devices_via_virsh(vm_id)
    file_paths, content = touch_files_under_vm_disks(vm_id=vm_id,
                                                     ephemeral=ephemeral,
                                                     swap=swap, vm_type=vm_type,
                                                     disks=vm_disks)

    LOG.tc_step("Cold migrate VM and {} resize".format(resize))
    revert = True if resize == 'revert' else False
    code, output = vm_helper.cold_migrate_vm(vm_id, revert=revert)
    assert 0 == code, "Cold migrate {} is not successful. Details: {}".format(
        resize, output)

    # Below steps are unnecessary as host is already checked in
    # cold_migrate_vm keyword. Add steps below just in case.
    LOG.tc_step(
        "Check VM host is as expected after cold migrate {}".format(resize))
    post_vm_host = vm_helper.get_vm_host(vm_id)
    if revert:
        assert prev_vm_host == post_vm_host, "vm host changed after cold " \
                                             "migrate revert"
    else:
        assert prev_vm_host != post_vm_host, "vm host did not change after " \
                                             "cold migrate"
        LOG.tc_step("Check that source host no longer has instance files")
        with host_helper.ssh_to_host(prev_vm_host) as prev_ssh:
            assert not prev_ssh.file_exists(
                '/var/lib/nova/instances/{}'.format(vm_id)), \
                "Instance files found on previous host {} after cold migrate " \
                "to {}".format(prev_vm_host, post_vm_host)

    LOG.tc_step("Ensure vm is pingable from NatBox after cold migration "
                "{}".format(resize))
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    LOG.tc_step("Check files after cold migrate {}".format(resize))
    action = None if revert else 'cold_migrate'
    check_helper.check_vm_files(vm_id=vm_id, storage_backing=storage_backing,
                                ephemeral=ephemeral, swap=swap,
                                vm_type=vm_type, vm_action=action,
                                file_paths=file_paths, content=content,
                                disks=vm_disks, prev_host=prev_vm_host,
                                post_host=post_vm_host)


def _boot_vm_under_test(storage_backing, ephemeral, swap, cpu_pol, vcpus,
                        vm_type):
    LOG.tc_step(
        "Create a flavor with {} vcpus, {}G ephemera disk, {}M swap "
        "disk".format(vcpus, ephemeral, swap))
    flavor_id = nova_helper.create_flavor(
        name='migration_test', ephemeral=ephemeral, swap=swap, vcpus=vcpus,
        storage_backing=storage_backing, cleanup='function')[1]

    if cpu_pol is not None:
        specs = {FlavorSpec.CPU_POLICY: cpu_pol}

        LOG.tc_step("Add following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor=flavor_id, **specs)

    boot_source = 'volume' if vm_type == 'volume' else 'image'
    LOG.tc_step("Boot a vm from {}".format(boot_source))
    vm_id = vm_helper.boot_vm('migration_test',
                              flavor=flavor_id, source=boot_source,
                              reuse_vol=False,
                              cleanup='function')[1]

    if vm_type == 'image_with_vol':
        LOG.tc_step("Attach volume to vm")
        vm_helper.attach_vol_to_vm(vm_id=vm_id, mount=False)

    return vm_id


@mark.parametrize(('guest_os', 'mig_type', 'cpu_pol'), [
    ('ubuntu_14', 'live', 'dedicated'),
    # Live migration with pinned VM may not be unsupported
    param('ubuntu_14', 'cold', 'dedicated',
          marks=mark.priorities('sanity', 'cpe_sanity')),
    param('tis-centos-guest', 'live', None,
          marks=mark.priorities('sanity', 'cpe_sanity')),
    ('tis-centos-guest', 'cold', None),
])
def test_migrate_vm(check_system, guest_os, mig_type, cpu_pol):
    """
    Test migrate vms for given guest type
    Args:
        check_system:
        guest_os:
        mig_type:
        cpu_pol:

    Test Steps:
        - Create a glance image from given guest type
        - Create a vm from cinder volume using above image
        - Live/cold migrate the vm
        - Ensure vm moved to other host and in good state (active and
            reachabe from NatBox)

    """
    LOG.tc_step("Create a flavor with 1 vcpu")
    flavor_id = \
        nova_helper.create_flavor(name='{}-mig'.format(mig_type), vcpus=1,
                                  root_disk=9, cleanup='function')[1]

    if cpu_pol is not None:
        specs = {FlavorSpec.CPU_POLICY: cpu_pol}
        LOG.tc_step("Add following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor=flavor_id, **specs)

    LOG.tc_step("Create a volume from {} image".format(guest_os))
    image_id = glance_helper.get_guest_image(guest_os=guest_os)

    vol_id = cinder_helper.create_volume(source_id=image_id, size=9,
                                         guest_image=guest_os)[1]
    ResourceCleanup.add('volume', vol_id)

    LOG.tc_step("Boot a vm from above flavor and volume")
    vm_id = vm_helper.boot_vm(guest_os, flavor=flavor_id, source='volume',
                              source_id=vol_id, cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    if guest_os == 'ubuntu_14':
        system_helper.wait_for_alarm_gone(alarm_id=EventLogID.CINDER_IO_CONGEST,
                                          entity_id='cinder_io_monitor',
                                          strict=False, timeout=300,
                                          fail_ok=False)

    LOG.tc_step("{} migrate vm and check vm is moved to different host".format(
        mig_type))
    prev_vm_host = vm_helper.get_vm_host(vm_id)

    if mig_type == 'live':
        code, output = vm_helper.live_migrate_vm(vm_id)
        if code == 1:
            assert False, "No host to live migrate to. System may not be in " \
                          "good state."
    else:
        vm_helper.cold_migrate_vm(vm_id)

    vm_host = vm_helper.get_vm_host(vm_id)
    assert prev_vm_host != vm_host, "vm host did not change after {} " \
                                    "migration".format(mig_type)

    LOG.tc_step("Ping vm from NatBox after {} migration".format(mig_type))
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
