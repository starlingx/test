from pytest import mark

from utils.tis_log import LOG
from keywords import vm_helper
from consts.stx import METADATA_SERVER


@mark.sanity
def test_vm_meta_data_retrieval():
    """
    VM meta-data retrieval

    Test Steps:
        - Launch a boot-from-image vm
        - Retrieve vm meta_data within vm from metadata server
        - Ensure vm uuid from metadata server is the same as nova show

    Test Teardown:
        - Delete created vm and flavor
    """
    LOG.tc_step("Launch a boot-from-image vm")
    vm_id = vm_helper.boot_vm(source='image', cleanup='function')[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)

    LOG.tc_step('Retrieve vm meta_data within vm from metadata server')
    # retrieve meta instance id by ssh to VM from natbox and wget to remote
    # server
    _access_metadata_server_from_vm(vm_id=vm_id)


def _access_metadata_server_from_vm(vm_id):
    with vm_helper.ssh_to_vm_from_natbox(vm_id) as vm_ssh:
        vm_ssh.exec_cmd('ip route')
        command = 'wget http://{}/openstack/latest/meta_data.json'.format(
            METADATA_SERVER)
        vm_ssh.exec_cmd(command, fail_ok=False)
        metadata = vm_ssh.exec_cmd('more meta_data.json', fail_ok=False)[1]

    LOG.tc_step("Ensure vm uuid from metadata server is the same as nova show")
    metadata = metadata.replace('\n', '')
    LOG.info(metadata)
    metadata_uuid = eval(metadata)['uuid']

    assert vm_id == metadata_uuid, "VM UUID retrieved from metadata server " \
                                   "is not the same as nova show"
