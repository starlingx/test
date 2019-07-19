#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time

from pytest import fixture, skip, mark

from consts.stx import VMStatus, GuestImages
from keywords import host_helper, vm_helper, cinder_helper, glance_helper, \
    system_helper, network_helper
from testfixtures.fixture_resources import ResourceCleanup
from utils import table_parser, exceptions
from utils.tis_log import LOG


@fixture(scope='module', autouse=True)
def check_system():
    if not cinder_helper.is_volumes_pool_sufficient(min_size=80):
        skip("Cinder volume pool size is smaller than 80G")

    if len(host_helper.get_up_hypervisors()) < 2:
        skip("at least two computes are required")

    if len(host_helper.get_storage_backing_with_max_hosts()[1]) < 2:
        skip("at least two hosts with the same storage backing are required")


@fixture(scope='function', autouse=True)
def pre_alarm_():
    """
    Text fixture to get pre-test existing alarm list.
    Args:None

    Returns: list of alarms

    """
    pre_alarms = system_helper.get_alarms_table()
    pre_list = table_parser.get_all_rows(pre_alarms)
    # Time stamps are removed before comparing alarms with post test alarms.
    # The time stamp  is the last item in each alarm row.
    for n in pre_list:
        n.pop()
    return pre_list


@fixture(scope='module')
def image_():
    """
    Text fixture to get guest image
    Args:

    Returns: the guest image id

    """
    return glance_helper.get_image_id_from_name()


@fixture(scope='function')
def volumes_(image_):
    """
    Text fixture to create two large cinder volumes with size of 20 and 40 GB.
    Args:
        image_: the guest image_id

    Returns: list of volume dict as following:
        {'id': <volume_id>,
         'display_name': <vol_inst1 or vol_inst2>,
         'size': <20 or 40>
        }
    """

    volumes = []
    cinder_params = [{'name': 'vol_inst1',
                      'size': 20},
                     {'name': 'vol_inst2',
                      'size': 40}]

    for param in cinder_params:
        volume_id = \
            cinder_helper.create_volume(name=param['name'], source_id=image_,
                                        size=param['size'])[1]
        volume = {
            'id': volume_id,
            'display_name': param['name'],
            'size': param['size']
        }
        volumes.append(volume)
        ResourceCleanup.add('volume', volume['id'], scope='function')

    return volumes


@fixture(scope='function')
def vms_(volumes_):
    """
    Text fixture to create cinder volume with specific 'display-name',
    and 'size'
    Args:
        volumes_: list of two large volumes dict created by volumes_ fixture

    Returns: volume dict as following:
        {'id': <volume_id>,
         'display_name': <vol_inst1 or vol_inst2>,
         'size': <20 or 40>
        }
    """
    vms = []
    vm_names = ['test_inst1', 'test_inst2']
    index = 0
    for vol_params in volumes_:
        instance_name = vm_names[index]
        vm_id = vm_helper.boot_vm(name=instance_name, source='volume',
                                  source_id=vol_params['id'],
                                  cleanup='function')[
            1]  # , user_data=get_user_data_file())[1]
        vm = {
            'id': vm_id,
            'display_name': instance_name,
        }
        vms.append(vm)
        index += 1
    return vms


@mark.storage_sanity
def test_vm_with_a_large_volume_live_migrate(vms_, pre_alarm_):
    """
    Test instantiate a vm with a large volume ( 20 GB and 40 GB) and live
    migrate:
    Args:
        vms_ (dict): vms created by vms_ fixture
        pre_alarm_ (list): alarm lists obtained by pre_alarm_ fixture

    Test Setups:
    - get tenant1 and management networks which are already created for lab
    setup
    - get or create a "small" flavor
    - get the guest image id
    - create two large volumes (20 GB and 40 GB) in cinder
    - boot two vms ( test_inst1, test_inst2) using  volumes 20 GB and 40 GB
    respectively


    Test Steps:
    - Verify VM status is ACTIVE
    - Validate that VMs boot, and that no timeouts or error status occur.
    - Verify the VM can be pinged from NATBOX
    - Verify login to VM and rootfs (dev/vda) filesystem is rw mode
    - Attempt to live migrate of VMs
    - Validate that the VMs migrated and no errors or alarms are present
    - Log into both VMs and validate that file systems are read-write
    - Terminate VMs

    Skip conditions:
    - less than two computes
    - no storage node

    """
    for vm in vms_:
        vm_id = vm['id']

        LOG.tc_step(
            "Checking VM status; VM Instance id is: {}......".format(vm_id))
        vm_state = vm_helper.get_vm_status(vm_id)

        assert vm_state == VMStatus.ACTIVE, 'VM {} state is {}; Not in ' \
                                            'ACTIVATE state as expected' \
            .format(vm_id, vm_state)

        LOG.tc_step("Verify  VM can be pinged from NAT box...")
        rc, boot_time = check_vm_boot_time(vm_id)
        assert rc, "VM is not pingable after {} seconds ".format(boot_time)

        LOG.tc_step("Verify Login to VM and check filesystem is rw mode....")
        assert is_vm_filesystem_rw(
            vm_id), 'rootfs filesystem is not RW as expected for VM {}' \
            .format(vm['display_name'])

        LOG.tc_step(
            "Attempting  live migration; vm id = {}; vm_name = {} ....".format(
                vm_id, vm['display_name']))

        code, msg = vm_helper.live_migrate_vm(vm_id=vm_id, fail_ok=False)
        LOG.tc_step("Verify live migration succeeded...")
        assert code == 0, "Expected return code 0. Actual return code: {}; " \
                          "details: {}".format(code, msg)

        LOG.tc_step("Verifying  filesystem is rw mode after live migration....")
        assert is_vm_filesystem_rw(
            vm_id), 'After live migration rootfs filesystem is not RW as ' \
                    'expected for VM {}'. \
            format(vm['display_name'])


@mark.domain_sanity
def test_vm_with_large_volume_and_evacuation(vms_, pre_alarm_):
    """
   Test instantiate a vm with a large volume ( 20 GB and 40 GB) and evacuate:

    Args:
        vms_ (dict): vms created by vms_ fixture
        pre_alarm_ (list): alarm lists obtained by pre_alarm_ fixture

    Test Setups:
    - get tenant1 and management networks which are already created for lab
    setup
    - get or create a "small" flavor
    - get the guest image id
    - create two large volumes (20 GB and 40 GB) in cinder
    - boot two vms ( test_inst1, test_inst2) using  volumes 20 GB and 40 GB
    respectively


    Test Steps:
    - Verify VM status is ACTIVE
    - Validate that VMs boot, and that no timeouts or error status occur.
    - Verify the VM can be pinged from NATBOX
    - Verify login to VM and rootfs (dev/vda) filesystem is rw mode
    - live migrate, if required, to bring both VMs to the same compute
    - Validate  migrated VM and no errors or alarms are present
    - Reboot compute host to initiate evacuation
    - Verify VMs are evacuated
    - Check for any system alarms
    - Verify login to VM and rootfs (dev/vda) filesystem is still rw mode
    after evacuation
    - Terminate VMs

    Skip conditions:
    - less that two computes
    - no  storage node

    """
    vm_ids = []
    for vm in vms_:
        vm_id = vm['id']
        vm_ids.append(vm_id)
        LOG.tc_step(
            "Checking VM status; VM Instance id is: {}......".format(vm_id))
        vm_state = vm_helper.get_vm_status(vm_id)
        assert vm_state == VMStatus.ACTIVE, 'VM {} state is {}; Not in ' \
                                            'ACTIVATE state as expected' \
            .format(vm_id, vm_state)

        LOG.tc_step("Verify  VM can be pinged from NAT box...")
        rc, boot_time = check_vm_boot_time(vm_id)
        assert rc, "VM is not pingable after {} seconds ".format(boot_time)

        LOG.tc_step("Verify Login to VM and check filesystem is rw mode....")
        assert is_vm_filesystem_rw(
            vm_id), 'rootfs filesystem is not RW as expected for VM {}' \
            .format(vm['display_name'])

    LOG.tc_step(
        "Checking if live migration is required to put the vms to a single "
        "compute....")
    host_0 = vm_helper.get_vm_host(vm_ids[0])
    host_1 = vm_helper.get_vm_host(vm_ids[1])

    if host_0 != host_1:
        LOG.tc_step("Attempting to live migrate  vm {} to host {} ....".format(
            (vms_[1])['display_name'], host_0))
        code, msg = vm_helper.live_migrate_vm(vm_ids[1],
                                              destination_host=host_0)
        LOG.tc_step("Verify live migration succeeded...")
        assert code == 0, "Live migration of vm {} to host {} did not " \
                          "success".format((vms_[1])['display_name'], host_0)

    LOG.tc_step("Verify both VMs are in same host....")
    assert host_0 == vm_helper.get_vm_host(
        vm_ids[1]), "VMs are not in the same compute host"

    LOG.tc_step(
        "Rebooting compute {} to initiate vm evacuation .....".format(host_0))
    vm_helper.evacuate_vms(host=host_0, vms_to_check=vm_ids, ping_vms=True)

    LOG.tc_step("Login to VM and to check filesystem is rw mode....")
    assert is_vm_filesystem_rw((vms_[0])[
                                   'id']), 'After evacuation the rootfs ' \
                                           'filesystem is not RW as expected ' \
                                           'for VM {}'.format(
        (vms_[0])['display_name'])

    LOG.tc_step("Login to VM and to check filesystem is rw mode....")
    assert is_vm_filesystem_rw((vms_[1])['id']), \
        'After evacuation the rootfs filesystem is not RW as expected ' \
        'for VM {}'.format((vms_[1])['display_name'])


@mark.domain_sanity
def test_instantiate_a_vm_with_a_large_volume_and_cold_migrate(vms_,
                                                               pre_alarm_):
    """
    Test instantiate a vm with a large volume ( 20 GB and 40 GB) and cold
    migrate:
    Args:
        vms_ (dict): vms created by vms_ fixture
        pre_alarm_ (list): alarm lists obtained by pre_alarm_ fixture

    Test Setups:
    - get tenant1 and management networks which are already created for lab
    setup
    - get or create a "small" flavor
    - get the guest image id
    - create two large volumes (20 GB and 40 GB) in cinder
    - boot two vms ( test_inst1, test_inst2) using  volumes 20 GB and 40 GB
    respectively


    Test Steps:
    - Verify VM status is ACTIVE
    - Validate that VMs boot, and that no timeouts or error status occur.
    - Verify the VM can be pinged from NATBOX
    - Verify login to VM and rootfs (dev/vda) filesystem is rw mode
    - Attempt to cold migrate of VMs
    - Validate that the VMs migrated and no errors or alarms are present
    - Log into both VMs and validate that file systems are read-write
    - Terminate VMs

    Skip conditions:
    - less than two hosts with the same storage backing
    - less than two computes
    - no storage node

    """
    LOG.tc_step("Instantiate a vm with large volume.....")

    vms = vms_

    for vm in vms:
        vm_id = vm['id']

        LOG.tc_step(
            "Checking VM status; VM Instance id is: {}......".format(vm_id))
        vm_state = vm_helper.get_vm_status(vm_id)

        assert vm_state == VMStatus.ACTIVE, 'VM {} state is {}; Not in ' \
                                            'ACTIVATE state as expected' \
            .format(vm_id, vm_state)

        LOG.tc_step("Verify  VM can be pinged from NAT box...")
        rc, boot_time = check_vm_boot_time(vm_id)
        assert rc, "VM is not pingable after {} seconds ".format(boot_time)

        LOG.tc_step("Verify Login to VM and check filesystem is rw mode....")
        assert is_vm_filesystem_rw(
            vm_id), 'rootfs filesystem is not RW as expected for VM {}' \
            .format(vm['display_name'])

        LOG.tc_step(
            "Attempting  cold migration; vm id = {}; vm_name = {} ....".format(
                vm_id, vm['display_name']))

        code, msg = vm_helper.cold_migrate_vm(vm_id=vm_id, fail_ok=True)
        LOG.tc_step("Verify cold migration succeeded...")
        assert code == 0, "Expected return code 0. Actual return code: {}; " \
                          "details: {}".format(code, msg)

        LOG.tc_step("Verifying  filesystem is rw mode after cold migration....")
        assert is_vm_filesystem_rw(
            vm_id), 'After cold migration rootfs filesystem is not RW as ' \
                    'expected for ' \
                    'VM {}'.format(vm['display_name'])

        # LOG.tc_step("Checking for any system alarm ....")
        # rc, new_alarm = is_new_alarm_raised(pre_alarms)
        # assert not rc, " alarm(s) found: {}".format(new_alarm)


def test_instantiate_a_vm_with_multiple_volumes_and_migrate():
    """
    Test  a vm with a multiple volumes live, cold  migration and evacuation:

    Test Setups:
    - get guest image_id
    - get or create 'small' flavor_id
    - get tenenat and managment network ids

    Test Steps:
    - create volume for boot and another extra size 8GB
    - boot vms from the created volume
    - Validate that VMs boot, and that no timeouts or error status occur.
    - Verify VM status is ACTIVE
    - Attach the second volume to VM
    - Attempt live migrate  VM
    - Login to VM and verify the filesystem is rw mode on both volumes
    - Attempt cold migrate  VM
    - Login to VM and verify the filesystem is rw mode on both volumes
    - Reboot the compute host to initiate evacuation
    - Login to VM and verify the filesystem is rw mode on both volumes
    - Terminate VMs

    Skip conditions:
    - less than two computes
    - less than one storage

    """
    # skip("Currently not working. Centos image doesn't see both volumes")
    LOG.tc_step("Creating a volume size=8GB.....")
    vol_id_0 = cinder_helper.create_volume(size=8)[1]
    ResourceCleanup.add('volume', vol_id_0, scope='function')

    LOG.tc_step("Creating a second volume size=8GB.....")
    vol_id_1 = cinder_helper.create_volume(size=8, bootable=False)[1]
    LOG.tc_step("Volume id is: {}".format(vol_id_1))
    ResourceCleanup.add('volume', vol_id_1, scope='function')

    LOG.tc_step("Booting instance vm_0...")

    vm_id = vm_helper.boot_vm(name='vm_0', source='volume', source_id=vol_id_0,
                              cleanup='function')[1]
    time.sleep(5)

    LOG.tc_step("Verify  VM can be pinged from NAT box...")
    rc, boot_time = check_vm_boot_time(vm_id)
    assert rc, "VM is not pingable after {} seconds ".format(boot_time)

    LOG.tc_step("Login to VM and to check filesystem is rw mode....")
    assert is_vm_filesystem_rw(
        vm_id), 'vol_0 rootfs filesystem is not RW as expected.'

    LOG.tc_step("Attemping to attach a second volume to VM...")
    vm_helper.attach_vol_to_vm(vm_id, vol_id_1)

    LOG.tc_step(
        "Login to VM and to check filesystem is rw mode for both volumes....")
    assert is_vm_filesystem_rw(vm_id, rootfs=['vda',
                                              'vdb']), 'volumes rootfs ' \
                                                       'filesystem is not RW ' \
                                                       'as expected.'

    LOG.tc_step("Attemping live migrate VM...")
    vm_helper.live_migrate_vm(vm_id=vm_id)

    LOG.tc_step(
        "Login to VM and to check filesystem is rw mode after live "
        "migration....")
    assert is_vm_filesystem_rw(vm_id, rootfs=['vda',
                                              'vdb']), 'After live migration ' \
                                                       'rootfs filesystem is ' \
                                                       'not RW'

    LOG.tc_step("Attempting  cold migrate VM...")
    vm_helper.cold_migrate_vm(vm_id)

    LOG.tc_step(
        "Login to VM and to check filesystem is rw mode after live "
        "migration....")
    assert is_vm_filesystem_rw(vm_id, rootfs=['vda',
                                              'vdb']), 'After cold migration ' \
                                                       'rootfs filesystem is ' \
                                                       'not RW'
    LOG.tc_step("Testing VM evacuation.....")
    before_host_0 = vm_helper.get_vm_host(vm_id)

    LOG.tc_step("Rebooting compute {} to initiate vm evacuation .....".format(
        before_host_0))
    vm_helper.evacuate_vms(host=before_host_0, vms_to_check=vm_id,
                           ping_vms=True)

    LOG.tc_step(
        "Login to VM and to check filesystem is rw mode after live "
        "migration....")
    assert is_vm_filesystem_rw(vm_id, rootfs=['vda',
                                              'vdb']), 'After evacuation ' \
                                                       'filesystem is not RW'


def check_vm_boot_time(vm_id):
    start_time = time.time()
    output = vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)
    elapsed_time = time.time() - start_time
    return output, elapsed_time


def is_vm_filesystem_rw(vm_id, rootfs='vda', vm_image_name=None):
    """

    Args:
        vm_id:
        rootfs (str|list):
        vm_image_name (None|str):

    Returns:

    """
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id, timeout=240)

    if vm_image_name is None:
        vm_image_name = GuestImages.DEFAULT['guest']

    router_host = dhcp_host = None
    try:
        LOG.info(
            "---------Collecting router and dhcp agent host info-----------")
        router_host = network_helper.get_router_host()
        mgmt_net = network_helper.get_mgmt_net_id()
        dhcp_host = network_helper.get_network_agents(field='Host',
                                                      network=mgmt_net)

        with vm_helper.ssh_to_vm_from_natbox(vm_id, vm_image_name=vm_image_name,
                                             retry_timeout=300) as vm_ssh:
            if isinstance(rootfs, str):
                rootfs = [rootfs]
            for fs in rootfs:
                cmd = "mount | grep {} | grep rw | wc -l".format(fs)
                cmd_output = vm_ssh.exec_sudo_cmd(cmd)[1]
                if cmd_output != '1':
                    LOG.info("Filesystem /dev/{} is not rw for VM: "
                             "{}".format(fs, vm_id))
                    return False
            return True
    except exceptions.SSHRetryTimeout:
        LOG.error("Failed to ssh, collecting vm console log.")
        vm_helper.get_console_logs(vm_ids=vm_id)
        LOG.info("Router host: {}. dhcp agent host: {}".format(router_host,
                                                               dhcp_host))
        raise
