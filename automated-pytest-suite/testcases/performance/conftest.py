# Do NOT remove following imports. Needed for test fixture discovery purpose

import os
import time
from pytest import fixture

from testfixtures.resource_mgmt import delete_resources_func, delete_resources_class, \
    delete_resources_module, delete_resources_session
from testfixtures.recover_hosts import hosts_recover_func, hosts_recover_class
from testfixtures.recover_hosts import hosts_recover_module
from testfixtures.recover_hosts import HostsToRecover
from consts.stx import AppStatus, GuestImages, FlavorSpec
from keywords import container_helper, glance_helper, host_helper
from keywords import network_helper, nova_helper, vm_helper, system_helper
from utils import cli, table_parser
from utils.tis_log import LOG
from consts.stx import FlavorSpec, GuestImages
from testfixtures.verify_fixtures import *
from testfixtures.pre_checks_and_configs import *

CIRROS_PARAMS = {
    "flavor_name": "f1.small",
    "flavor_vcpus": 1,
    "flavor_ram": 2048,
    "flavor_disk": 60,
    "properties": {FlavorSpec.MEM_PAGE_SIZE: 'large'},
    "image_name": "cirros",
    "image_file": os.path.join(GuestImages.DEFAULT["image_dir"], "cirros-0.4.0-x86_64-disk.img"),
    "disk_format": "qcow2"
}
DICT_PARAMS = [CIRROS_PARAMS]


@fixture(params=DICT_PARAMS, scope="module")
def create_flavors_and_images(request):
    # TODO need to check with add_default_specs set to True on baremetal
    LOG.fixture_step("Creating flavor and image")
    fl_id = nova_helper.create_flavor(name=request.param['flavor_name'],
                                      vcpus=request.param['flavor_vcpus'],
                                      ram=request.param['flavor_ram'],
                                      root_disk=request.param['flavor_disk'],
                                      properties=request.param['properties'], is_public=True,
                                      add_default_specs=False, cleanup="module")[1]
    LOG.error(request.param['image_file'])
    im_id = glance_helper.create_image(name=request.param['image_name'],
                                       source_image_file=request.param['image_file'],
                                       disk_format=request.param['disk_format'],
                                       cleanup="module")[1]
    return {
        "flavor": fl_id,
        "image": im_id
    }


@fixture(scope="module")
def create_network_performance():
    """
    Create network and subnetwork used in sanity_openstack tests
    """
    LOG.fixture_step("Creating net and subnet")
    net_id = network_helper.create_network(name="network-1", cleanup="module")[1]
    subnet_id = network_helper.create_subnet(name="subnet", network="network-1",
                                             subnet_range="192.168.0.0/24", dhcp=True,
                                             ip_version=4, cleanup="module")[1]
    return net_id, subnet_id


# this should be modified to call boot_vm_openstack when implemented
@fixture(scope="module")
def launch_instances(create_flavors_and_images, create_network_performance):
    LOG.fixture_step("Creating instances")
    net_id_list = list()
    net_id_list.append({"net-id": create_network_performance[0]})
    host = host_helper.get_hypervisors()[0]
    vm_id = vm_helper.boot_vm(flavor=create_flavors_and_images["flavor"],
                              nics=net_id_list, source="image",
                              source_id=create_flavors_and_images["image"],
                              vm_host=host, cleanup="module")[1]
    # TODO check power state RUNNING?
    return vm_id

# TODO maybe teardown to revert values to older versions
@fixture(scope="module")
def ovs_dpdk_1_core():
    LOG.fixture_step("Review the ovs-dpdk vswitch be in just 1 core")
    vswitch_type = "ovs-dpdk"
    cpu_function = "vswitch"
    proc = "0"
    host_list = host_helper.get_hypervisors()
    for host in host_list:
        with host_helper.ssh_to_host(host) as node_ssh:
            cmd = "cat /proc/meminfo | grep Hugepagesize | awk '{print $2}'"
            hp = int(node_ssh.exec_cmd(cmd=cmd, fail_ok=False, get_exit_code=False)[1])
        mem = host_helper.get_host_memories(host=host,
                                            headers=("app_hp_avail_2M",
                                                     "app_hp_avail_1G",
                                                     "mem_avail(MiB)",
                                                     "vs_hp_total"))
        if hp == 1048576:
            if int(mem[proc][3]) < 2 or mem[proc][1] < 10:
                HostsToRecover.add(hostnames=host, scope="module")
                host_helper.lock_host(host=host)
                if int(mem[proc][3]) < 2:
                    args = ' -f vswitch -1G {} {} {}'.format(2, host, proc)
                    cli.system('host-memory-modify', args)
                    host_helper.modify_host_cpu(host=host, cpu_function=cpu_function,
                                                **{"p{}".format(proc): 1})
                    # TODO maybe find a better option than sleep since we can't wait for applyying
                    # container_helper.wait_for_apps_status(apps='stx-openstack',
                    #                                       status=AppStatus.APPLYING)
                    time.sleep(60)
                    container_helper.wait_for_apps_status(apps='stx-openstack',
                                                            status=AppStatus.APPLIED,
                                                            check_interval=30)
                if mem[proc][1] < 10:
                    args = ' -1G {} {} {}'.format(10, host, proc)
                    cli.system('host-memory-modify', args)
                host_helper.unlock_host(host=host)
        if hp == 2048:
            if int(mem[proc][3]) < 512 or mem[proc][0] < 2500:
                host_helper.lock_host(host=host)
                if int(mem[proc][3]) < 512:
                    system_helper.modify_system(**{"vswitch_type": vswitch_type})
                    vswitch_args = ' -f vswitch -2M {} {} {}'.format(512, host, proc)
                    cli.system('host-memory-modify', vswitch_args)
                    host_helper.modify_host_cpu(host=host, cpu_function=cpu_function,
                                                **{"p{}".format(proc): 1})
                    # TODO maybe find a better option than sleep since we can't wait for applyying
                    # container_helper.wait_for_apps_status(apps='stx-openstack',
                    #                                     status=AppStatus.APPLIED)
                    time.sleep(60)
                    container_helper.wait_for_apps_status(apps='stx-openstack',
                                                        status=AppStatus.APPLIED,
                                                        check_interval=30)
                if mem[proc][0] < 2500:
                    args = ' -2M {} {} {}'.format(2500, host, proc)
                    cli.system('host-memory-modify', args)
                host_helper.unlock_host(host=host)

        test_table = host_helper.get_host_cpu_list_table(host=host)
        curr_assigned_function_list = table_parser.get_values(test_table, "assigned_function")
        assert "vSwitch" in curr_assigned_function_list
