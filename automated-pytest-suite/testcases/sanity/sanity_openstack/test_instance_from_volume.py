###
# Copyright (C) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Create instances from volume, perform different power status and set properties, using Cirros OS.
# Author(s): Alexandru Dimofte alexandru.dimofte@intel.com
###

import os
from pytest import mark, fixture

from consts.stx import GuestImages, VMStatus, FlavorSpec
from keywords import nova_helper, glance_helper, vm_helper, system_helper
from keywords import network_helper, cinder_helper
from testfixtures.pre_checks_and_configs import no_simplex
from utils import cli

VM_IDS = list()
cirros_params = {
    "flavor_name_1": "f1.small",
    "flavor_name_2": "f2.small",
    "flavor_vcpus": 1,
    "instance_name_1": "vm-cirros-1",
    "instance_name_2": "vm-cirros-2",
    "volume_name_1": "vol-cirros-1",
    "volume_name_2": "vol-cirros-2",
    "flavor_ram": 2048,
    "flavor_disk": 20,
    "properties": None,
    "image_name": "cirros",
    "image_file": os.path.join(GuestImages.DEFAULT["image_dir"], "cirros-0.4.0-x86_64-disk.img"),
    "disk_format": "qcow2"
}

dict_params = ("vol-cirros-1", "vol-cirros-2")

def lock_instance(launch_instances):
    cli.openstack(cmd='server lock', positional_args=launch_instances)


def unlock_instance(launch_instances):
    cli.openstack(cmd='server unlock', positional_args=launch_instances)

@fixture(scope="module")
def create_flavour_and_image():
    fl_id = nova_helper.create_flavor(name=cirros_params['flavor_name_1'],
                                      vcpus=cirros_params['flavor_vcpus'],
                                      ram=cirros_params['flavor_ram'],
                                      root_disk=cirros_params['flavor_disk'],
                                      properties=cirros_params['properties'], is_public=True,
                                      add_default_specs=False,
                                      cleanup="module")[1]
    fl_id_2 = nova_helper.create_flavor(name=cirros_params["flavor_name_2"],
                                        vcpus=cirros_params["flavor_vcpus"],
                                        ram=cirros_params["flavor_ram"],
                                        root_disk=cirros_params["flavor_disk"],
                                        properties=cirros_params["properties"], is_public=True,
                                        add_default_specs=False,
                                        cleanup="module")[1]
    im_id = glance_helper.create_image(name=cirros_params['image_name'],
                                       source_image_file=cirros_params['image_file'],
                                       disk_format=cirros_params['disk_format'],
                                       cleanup="module")[1]
    return {
            "flavor1": fl_id,
            "flavor2": fl_id_2,
            "image": im_id
    }

# Creating Volume For Instances
@fixture(params=dict_params, scope="module")
def volume_from_instance(request, create_flavour_and_image):
    return cinder_helper.create_volume(name=request.param, source_type='image',
                                       source_id=create_flavour_and_image['image'],
                                       size=cirros_params['flavor_disk'], cleanup="module")[1]

@fixture(scope="module")
def launch_instances(create_flavour_and_image, create_network_sanity, volume_from_instance):
    net_id_list = list()
    net_id_list.append({"net-id": create_network_sanity})
    host = system_helper.get_active_controller_name()
    launch_instances = vm_helper.boot_vm(flavor=create_flavour_and_image["flavor1"],
                                         nics=net_id_list, source="volume",
                                         source_id=volume_from_instance,
                                         vm_host=host, cleanup="module")[1]
    VM_IDS.append(launch_instances)
    return launch_instances

# Suspend Resume Instances
@mark.robotsanity
def test_suspend_resume_instances(launch_instances):
    vm_helper.suspend_vm(vm_id=launch_instances)
    vm_helper.resume_vm(vm_id=launch_instances)

# Set error Active Flags Instance
@mark.robotsanity
@mark.parametrize(('status'), [(VMStatus.ERROR), (VMStatus.ACTIVE)])
def test_set_error_active_flags_instances(launch_instances, status):
    vm_helper.set_vm(vm_id=launch_instances, state=status)

# Pause Unpause Instances
@mark.robotsanity
def test_pause_unpause_instances(launch_instances):
    vm_helper.pause_vm(vm_id=launch_instances)
    vm_helper.unpause_vm(vm_id=launch_instances)

# Stop Start Instances
@mark.robotsanity
def test_stop_start_instances(launch_instances):
    vm_helper.stop_vms(vms=launch_instances)
    vm_helper.start_vms(vms=launch_instances)

# Lock Unlock Instances
@mark.robotsanity
def test_lock_unlock_instances(launch_instances):
    lock_instance(launch_instances)
    unlock_instance(launch_instances)

# Reboot Instances
@mark.robotsanity
def test_reboot_instances(launch_instances):
    vm_helper.reboot_vm(vm_id=launch_instances)

# Rebuild Instances (from Volume)
@mark.robotsanity
def test_rebuild_instances(launch_instances, create_flavour_and_image):
    vm_helper.rebuild_vm(vm_id=launch_instances, image_id=create_flavour_and_image["image"])

# Resize Instances
@mark.robotsanity
def test_resize_instances(launch_instances, create_flavour_and_image):
    vm_helper.resize_vm(vm_id=launch_instances, flavor_id=create_flavour_and_image["flavor2"])
    vm_helper.resize_vm(vm_id=launch_instances, flavor_id=create_flavour_and_image["flavor1"])

# Set Unset Properties Instances
@mark.robotsanity
def test_set_unset_properties_instances(launch_instances):
    vm_helper.set_vm(vm_id=launch_instances, **{FlavorSpec.AUTO_RECOVERY: "true",
                                                FlavorSpec.LIVE_MIG_MAX_DOWNTIME: "500",
                                                FlavorSpec.LIVE_MIG_TIME_OUT: "180"})
    vm_helper.unset_vm(vm_id=launch_instances, properties=[FlavorSpec.AUTO_RECOVERY,
                                                           FlavorSpec.LIVE_MIG_MAX_DOWNTIME,
                                                           FlavorSpec.LIVE_MIG_TIME_OUT])

# Evacuate Instances From Hosts
# @mark.robotsanity
# def test_evacuate_instances_from_hosts(no_simplex):
#     TODO this is not yet completed
#     vm_helper.evacuate_vms(host="controller-0", vms_to_check=VM_IDS)
#     vm_helper.evacuate_vms(host="controller-1", vms_to_check=VM_IDS)
#    pass
