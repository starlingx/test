from pytest import fixture, skip, mark

from consts.timeout import VMTimeout
from keywords import vm_helper, host_helper, cinder_helper, glance_helper, \
    system_helper
from testfixtures.fixture_resources import ResourceCleanup
from testfixtures.recover_hosts import HostsToRecover
from utils.tis_log import LOG

TEST_STRING = 'Config-drive test file content'


@fixture(scope='module')
def hosts_per_stor_backing():
    hosts_per_backing = host_helper.get_hosts_per_storage_backing()
    LOG.fixture_step("Hosts per storage backing: {}".format(hosts_per_backing))

    return hosts_per_backing


@mark.nightly
@mark.sx_nightly
def test_vm_with_config_drive(hosts_per_stor_backing):
    """
    Skip Condition:
        - no host with local_image backend

    Test Steps:
        - Launch a vm using config drive
        - Add test data to config drive on vm
        - Do some operations (reboot vm for simplex, cold migrate and lock
        host for non-simplex) and
            check test data persisted in config drive after each operation
    Teardown:
        - Delete created vm, volume, flavor

    """
    guest_os = 'cgcs-guest'
    img_id = glance_helper.get_guest_image(guest_os)
    hosts_num = len(hosts_per_stor_backing.get('local_image', []))
    if hosts_num < 1:
        skip("No host with local_image storage backing")

    volume_id = cinder_helper.create_volume(name='vol_inst1', source_id=img_id,
                                            guest_image=guest_os)[1]
    ResourceCleanup.add('volume', volume_id, scope='function')

    block_device = {'source': 'volume', 'dest': 'volume', 'id': volume_id,
                    'device': 'vda'}
    vm_id = vm_helper.boot_vm(name='config_drive', config_drive=True,
                              block_device=block_device,
                              cleanup='function', guest_os=guest_os,
                              meta={'foo': 'bar'})[1]

    LOG.tc_step("Confirming the config drive is set to True in vm ...")
    assert str(vm_helper.get_vm_values(vm_id, "config_drive")[
                   0]) == 'True', "vm config-drive not true"

    LOG.tc_step("Add date to config drive ...")
    check_vm_config_drive_data(vm_id)

    vm_host = vm_helper.get_vm_host(vm_id)
    instance_name = vm_helper.get_vm_instance_name(vm_id)
    LOG.tc_step("Check config_drive vm files on hypervisor after vm launch")
    check_vm_files_on_hypervisor(vm_id, vm_host=vm_host,
                                 instance_name=instance_name)

    if not system_helper.is_aio_simplex():
        LOG.tc_step("Cold migrate VM")
        vm_helper.cold_migrate_vm(vm_id)

        LOG.tc_step("Check config drive after cold migrate VM...")
        check_vm_config_drive_data(vm_id)

        LOG.tc_step("Lock the compute host")
        compute_host = vm_helper.get_vm_host(vm_id)
        HostsToRecover.add(compute_host)
        host_helper.lock_host(compute_host, swact=True)

        LOG.tc_step("Check config drive after locking VM host")
        check_vm_config_drive_data(vm_id, ping_timeout=VMTimeout.DHCP_RETRY)
        vm_host = vm_helper.get_vm_host(vm_id)

    else:
        LOG.tc_step("Reboot vm")
        vm_helper.reboot_vm(vm_id)

        LOG.tc_step("Check config drive after vm rebooted")
        check_vm_config_drive_data(vm_id)

    LOG.tc_step("Check vm files exist after nova operations")
    check_vm_files_on_hypervisor(vm_id, vm_host=vm_host,
                                 instance_name=instance_name)


def check_vm_config_drive_data(vm_id, ping_timeout=VMTimeout.PING_VM):
    """
    Args:
        vm_id:
        ping_timeout

    Returns:

    """
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id, timeout=ping_timeout)
    dev = '/dev/hd'
    with vm_helper.ssh_to_vm_from_natbox(vm_id) as vm_ssh:
        # Run mount command to determine the /dev/hdX is mount at:
        cmd = """mount | grep "{}" | awk '{{print  $3}} '""".format(dev)
        mount = vm_ssh.exec_cmd(cmd)[1]
        assert mount, "{} is not mounted".format(dev)

        file_path = '{}/openstack/latest/meta_data.json'.format(mount)
        content = vm_ssh.exec_cmd('python -m json.tool {} | grep '
                                  'foo'.format(file_path), fail_ok=False)[1]
        assert '"foo": "bar"' in content


def check_vm_files_on_hypervisor(vm_id, vm_host, instance_name):
    with host_helper.ssh_to_host(vm_host) as host_ssh:
        cmd = " ls /var/lib/nova/instances/{}".format(vm_id)
        cmd_output = host_ssh.exec_cmd(cmd)[1]
        for expt_file in ('console.log', 'disk.config'):
            assert expt_file in cmd_output, \
                "{} is not found for config drive vm {} on " \
                "{}".format(expt_file, vm_id, vm_host)

        output = host_ssh.exec_cmd('ls /run/libvirt/qemu')[1]
        libvirt = "{}.xml".format(instance_name)
        assert libvirt in output, "{} is not found in /run/libvirt/qemu on " \
                                  "{}".format(libvirt, vm_host)
