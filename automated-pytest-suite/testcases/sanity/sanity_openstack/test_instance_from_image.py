###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Create instances from image, perform different power status and set properties,
#   using Cirros OS and Centos OS.
###

import os
from pytest import mark, fixture

from consts.stx import GuestImages, VMStatus, FlavorSpec
from keywords import nova_helper, glance_helper, vm_helper, system_helper
# TODO this will be used in evacuate test
# from testfixtures.pre_checks_and_configs import no_simplex
from utils import cli

# TODO maybe add cirros image name to Guest images and use it from there
VM_IDS = list()
centos_params = {
    "flavor_name_1": "f1.medium",
    "flavor_name_2": "f2.medium",
    "flavor_vcpus": 2,
    "flavor_ram": 4096,
    "flavor_disk": 40,
    "properties": {FlavorSpec.GUEST_HEARTBEAT: 'false',
                   FlavorSpec.CPU_POLICY: 'shared'},
    "image_name": "centos",
    "image_file": os.path.join(GuestImages.DEFAULT['image_dir'],
                               GuestImages.IMAGE_FILES['centos_7'][0]),
    "disk_format": GuestImages.IMAGE_FILES['centos_7'][3]
}
cirros_params = {
    "flavor_name_1": "f1.small",
    "flavor_name_2": "f2.small",
    "flavor_vcpus": 1,
    "flavor_ram": 2048,
    "flavor_disk": 20,
    "properties": None,
    "image_name": "cirros",
    "image_file": os.path.join(GuestImages.DEFAULT["image_dir"], "cirros-0.4.0-x86_64-disk.img"),
    "disk_format": "qcow2"
}

dict_params = (centos_params, cirros_params)

# I think this should be moved into vm_helper
# Does this require a check after to see that only admin is working?
def lock_instance(vm_id):
    """
    Lock server(s). A non-admin user will not be able to execute actions
    """
    cli.openstack(cmd='server lock', positional_args=vm_id)

# I think this should be moved into vm_helper
# Does this require a check after to see that only admin is working?
def unlock_instance(vm_id):
    """
    Unlock server(s)
    """
    cli.openstack(cmd='server unlock', positional_args=vm_id)

@fixture(params=dict_params, scope="module", ids=["centos", "cirros"])
def create_flavors_and_images(request):
    # TODO need to check with add_default_specs set to True on baremetal
    fl_id = nova_helper.create_flavor(name=request.param['flavor_name_1'],
                                      vcpus=request.param['flavor_vcpus'],
                                      ram=request.param['flavor_ram'],
                                      root_disk=request.param['flavor_disk'],
                                      properties=request.param['properties'], is_public=True,
                                      add_default_specs=False, cleanup="module")[1]
    fl_id_2 = nova_helper.create_flavor(name=request.param["flavor_name_2"],
                                        vcpus=request.param["flavor_vcpus"],
                                        ram=request.param["flavor_ram"],
                                        root_disk=request.param["flavor_disk"],
                                        properties=request.param["properties"], is_public=True,
                                        add_default_specs=False, cleanup="module")[1]
    im_id = glance_helper.create_image(name=request.param['image_name'],
                                       source_image_file=request.param['image_file'],
                                       disk_format=request.param['disk_format'],
                                       cleanup="module")[1]
    return {
        "flavor1": fl_id,
        "flavor2": fl_id_2,
        "image": im_id
    }

# this should be modified to call boot_vm_openstack when implemented
@fixture(scope="module")
def launch_instances(create_flavors_and_images, create_network_sanity):
    net_id_list = list()
    net_id_list.append({"net-id": create_network_sanity[0]})
    host = system_helper.get_active_controller_name()
    vm_id = vm_helper.boot_vm(flavor=create_flavors_and_images["flavor1"],
                              nics=net_id_list, source="image",
                              source_id=create_flavors_and_images["image"],
                              vm_host=host, cleanup="module")[1]
    # TODO check power state RUNING
    VM_IDS.append(vm_id)
    return vm_id

@mark.robotsanity
def test_suspend_resume_instances(launch_instances):
    vm_helper.suspend_vm(vm_id=launch_instances)
    vm_helper.resume_vm(vm_id=launch_instances)

@mark.robotsanity
@mark.parametrize(
    ('status'), [
        (VMStatus.ERROR),
        (VMStatus.ACTIVE)
    ]
)
def test_set_error_active_flags_instances(status, launch_instances):
    vm_helper.set_vm(vm_id=launch_instances, state=status)

@mark.robotsanity
def test_pause_unpause_instances(launch_instances):
    vm_helper.pause_vm(vm_id=launch_instances)
    vm_helper.unpause_vm(vm_id=launch_instances)

@mark.robotsanity
def test_stop_start_instances(launch_instances):
    vm_helper.stop_vms(vms=launch_instances)
    vm_helper.start_vms(vms=launch_instances)

@mark.robotsanity
def test_lock_unlock_instances(launch_instances):
    lock_instance(launch_instances)
    unlock_instance(launch_instances)

@mark.robotsanity
def test_reboot_instances(launch_instances):
    vm_helper.reboot_vm(vm_id=launch_instances)

@mark.robotsanity
def test_rebuild_instances(launch_instances, create_flavors_and_images):
    vm_helper.rebuild_vm(vm_id=launch_instances, image_id=create_flavors_and_images["image"])

@mark.robotsanity
def test_resize_instances(launch_instances, create_flavors_and_images):
    vm_helper.resize_vm(vm_id=launch_instances, flavor_id=create_flavors_and_images["flavor2"])
    vm_helper.resize_vm(vm_id=launch_instances, flavor_id=create_flavors_and_images["flavor1"])

@mark.robotsanity
def test_set_unset_properties_instances(launch_instances):
    vm_helper.set_vm(vm_id=launch_instances, **{FlavorSpec.AUTO_RECOVERY: "true",
                                                FlavorSpec.LIVE_MIG_MAX_DOWNTIME: "500",
                                                FlavorSpec.LIVE_MIG_TIME_OUT: "180"})
    vm_helper.unset_vm(vm_id=launch_instances, properties=[FlavorSpec.AUTO_RECOVERY,
                                                           FlavorSpec.LIVE_MIG_MAX_DOWNTIME,
                                                           FlavorSpec.LIVE_MIG_TIME_OUT])

# @mark.robotsanity
# def test_evacuate_instances_from_hosts(no_simplex):
#     TODO this is not yet completed
#     vm_helper.evacuate_vms(host="controller-0", vms_to_check=VM_IDS)
#     vm_helper.evacuate_vms(host="controller-1", vms_to_check=VM_IDS)
#     pass
