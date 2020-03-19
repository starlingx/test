#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, param

from utils.tis_log import LOG
from consts.stx import FlavorSpec, GuestImages
from keywords import vm_helper, glance_helper, nova_helper, network_helper, \
    cinder_helper


def id_gen(val):
    if not isinstance(val, str):
        new_val = []
        for val_1 in val:
            if not isinstance(val_1, str):
                val_1 = '_'.join([str(val_2).lower() for val_2 in val_1])
            new_val.append(val_1)
        new_val = '_'.join(new_val)
    else:
        new_val = val

    return new_val


def _compose_nics(vifs, net_ids, image_id, guest_os):
    nics = []
    glance_vif = None
    if isinstance(vifs, str):
        vifs = (vifs,)
    for i in range(len(vifs)):
        vif_model = vifs[i]
        nic = {'net-id': net_ids[i]}
        if vif_model in ('e1000', 'rt18139'):
            glance_vif = vif_model
        elif vif_model != 'virtio':
            nic['vif-model'] = vif_model
        nics.append(nic)

    if glance_vif:
        glance_helper.set_image(image=image_id, hw_vif_model=glance_vif,
                                new_name='{}_{}'.format(guest_os, glance_vif))

    return nics


@mark.parametrize(('guest_os', 'vm1_vifs', 'vm2_vifs'), [
    param('default', 'virtio', 'virtio',
          marks=mark.priorities('cpe_sanity', 'sanity', 'sx_sanity')),
    ('ubuntu_14', 'virtio', 'virtio'),
], ids=id_gen)
def test_ping_between_two_vms(stx_openstack_required, guest_os, vm1_vifs, vm2_vifs):
    """
    Ping between two vms with given vif models

    Test Steps:
        - Create a favor with dedicated cpu policy and proper root disk size
        - Create a volume from guest image under test with proper size
        - Boot two vms with given vif models from above volume and flavor
        - Ping VMs from NatBox and between two vms

    Test Teardown:
        - Delete vms, volumes, flavor, glance image created

    """
    if guest_os == 'default':
        guest_os = GuestImages.DEFAULT['guest']

    reuse = False if 'e1000' in vm1_vifs or 'e1000' in vm2_vifs else True
    cleanup = 'function' if not reuse or 'ubuntu' in guest_os else None
    image_id = glance_helper.get_guest_image(guest_os, cleanup=cleanup,
                                             use_existing=reuse)

    LOG.tc_step("Create a favor dedicated cpu policy")
    flavor_id = nova_helper.create_flavor(name='dedicated', guest_os=guest_os,
                                          cleanup='function')[1]
    nova_helper.set_flavor(flavor_id, **{FlavorSpec.CPU_POLICY: 'dedicated'})

    mgmt_net_id = network_helper.get_mgmt_net_id()
    tenant_net_id = network_helper.get_tenant_net_id()
    internal_net_id = network_helper.get_internal_net_id()
    net_ids = (mgmt_net_id, tenant_net_id, internal_net_id)
    vms = []
    for vifs_for_vm in (vm1_vifs, vm2_vifs):
        # compose vm nics
        nics = _compose_nics(vifs_for_vm, net_ids=net_ids, image_id=image_id,
                             guest_os=guest_os)
        net_types = ['mgmt', 'data', 'internal'][:len(nics)]
        LOG.tc_step("Create a volume from {} image".format(guest_os))
        vol_id = cinder_helper.create_volume(name='vol-{}'.format(guest_os),
                                             source_id=image_id,
                                             guest_image=guest_os,
                                             cleanup='function')[1]

        LOG.tc_step(
            "Boot a {} vm with {} vifs from above flavor and volume".format(
                guest_os, vifs_for_vm))
        vm_id = vm_helper.boot_vm('{}_vifs'.format(guest_os), flavor=flavor_id,
                                  cleanup='function',
                                  source='volume', source_id=vol_id, nics=nics,
                                  guest_os=guest_os)[1]

        LOG.tc_step("Ping VM {} from NatBox(external network)".format(vm_id))
        vm_helper.wait_for_vm_pingable_from_natbox(vm_id, fail_ok=False)

        vms.append(vm_id)

    LOG.tc_step(
        "Ping between two vms over management, data, and internal networks")
    vm_helper.ping_vms_from_vm(to_vms=vms[0], from_vm=vms[1],
                               net_types=net_types)
    vm_helper.ping_vms_from_vm(to_vms=vms[1], from_vm=vms[0],
                               net_types=net_types)
