#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, skip, param

from utils.tis_log import LOG
from consts.stx import FlavorSpec, VMStatus
from consts.reasons import SkipStorageSpace

from keywords import vm_helper, nova_helper, glance_helper, cinder_helper
from testfixtures.fixture_resources import ResourceCleanup


def id_gen(val):
    if isinstance(val, list):
        return '-'.join(val)


@mark.parametrize(('guest_os', 'cpu_pol', 'actions'), [
    param('tis-centos-guest', 'dedicated', ['pause', 'unpause'],
          marks=mark.priorities('sanity', 'cpe_sanity', 'sx_sanity')),
    param('ubuntu_14', 'shared', ['stop', 'start'], marks=mark.sanity),
    param('ubuntu_14', 'dedicated', ['auto_recover'], marks=mark.sanity),
    param('tis-centos-guest', 'dedicated', ['suspend', 'resume'],
          marks=mark.priorities('sanity', 'cpe_sanity', 'sx_sanity')),
], ids=id_gen)
def test_nova_actions(guest_os, cpu_pol, actions):
    """

    Args:
        guest_os:
        cpu_pol:
        actions:

    Test Steps:
        - Create a glance image from given guest type
        - Create a vm from cinder volume using above image with specified cpu
        policy
        - Perform given nova actions on vm
        - Ensure nova operation succeeded and vm still in good state (active
        and reachable from NatBox)

    """
    if guest_os == 'opensuse_12':
        if not cinder_helper.is_volumes_pool_sufficient(min_size=40):
            skip(SkipStorageSpace.SMALL_CINDER_VOLUMES_POOL)

    img_id = glance_helper.get_guest_image(guest_os=guest_os)

    LOG.tc_step("Create a flavor with 1 vcpu")
    flavor_id = nova_helper.create_flavor(name=cpu_pol, vcpus=1, root_disk=9)[1]
    ResourceCleanup.add('flavor', flavor_id)

    if cpu_pol is not None:
        specs = {FlavorSpec.CPU_POLICY: cpu_pol}
        LOG.tc_step("Add following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor=flavor_id, **specs)

    LOG.tc_step("Create a volume from {} image".format(guest_os))
    vol_id = \
        cinder_helper.create_volume(name='vol-' + guest_os, source_id=img_id,
                                    guest_image=guest_os)[1]
    ResourceCleanup.add('volume', vol_id)

    LOG.tc_step("Boot a vm from above flavor and volume")
    vm_id = vm_helper.boot_vm('nova_actions', flavor=flavor_id, source='volume',
                              source_id=vol_id,
                              cleanup='function')[1]

    LOG.tc_step("Wait for VM pingable from NATBOX")
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)

    for action in actions:
        if action == 'auto_recover':
            LOG.tc_step(
                "Set vm to error state and wait for auto recovery complete, "
                "then verify ping from base vm over "
                "management and data networks")
            vm_helper.set_vm_state(vm_id=vm_id, error_state=True, fail_ok=False)
            vm_helper.wait_for_vm_values(vm_id=vm_id, status=VMStatus.ACTIVE,
                                         fail_ok=True, timeout=600)
        else:
            LOG.tc_step(
                "Perform following action on vm {}: {}".format(vm_id, action))
            vm_helper.perform_action_on_vm(vm_id, action=action)

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
