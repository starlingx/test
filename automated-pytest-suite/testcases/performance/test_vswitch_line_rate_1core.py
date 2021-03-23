###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test to measure the passthrough value of moving
# a file of 1 GB size from one instance to another with
# open source virtual switch with DPDK running in 1 core.
#
###

from pytest import mark, fixture

from keywords import host_helper, keystone_helper, network_helper, vm_helper
from utils.tis_log import LOG

FILE_SIZE = 10  # 10G
IMAGE_USER = 'cirros'
IMAGE_PASS = 'gocubsgo'


# TODO move to utils?
def get_host_and_ns(netid, host_list):
    for host in host_list:
        with host_helper.ssh_to_host(host) as node_ssh:
            cmd = 'ip netns | grep --color=never {}'.format(netid)
            ns = node_ssh.exec_cmd(cmd=cmd)[1]
            if ns and netid in ns.split()[0]:
                return (host, ns.split()[0])
    return (None, None)

@fixture(scope="module")
def create_instances(create_flavors_and_images, create_network_performance):
    LOG.fixture_step("Creating instances")
    net_id_list = list()
    net_id_list.append({"net-id": create_network_performance[0]})
    host = host_helper.get_hypervisors()[1]
    vm_id_1 = vm_helper.boot_vm(flavor=create_flavors_and_images["flavor"],
                                nics=net_id_list, source="image",
                                source_id=create_flavors_and_images["image"],
                                vm_host=host, cleanup="module")[1]
    vm_id_2 = vm_helper.boot_vm(flavor=create_flavors_and_images["flavor"],
                                nics=net_id_list, source="image",
                                source_id=create_flavors_and_images["image"],
                                vm_host=host, cleanup="module")[1]
    vm_ip_1 = vm_helper.get_vm_values(vm_id=vm_id_1, fields='addresses')[0].split("=")[1]
    vm_ip_2 = vm_helper.get_vm_values(vm_id=vm_id_2, fields='addresses')[0].split("=")[1]
    return {"vm_id_1": vm_id_1,
            "vm_id_2": vm_id_2,
            "vm_ip_1": vm_ip_1,
            "vm_ip_2": vm_ip_2}


@mark.robotperformance
def test_vswitch_line_rate_1core(ovs_dpdk_1_core, create_instances, create_network_performance,
                                 no_simplex, no_duplex):

    LOG.tc_step("Add icmp and tcp rules")
    project_id = keystone_helper.get_projects(name='admin')[0]
    security_group = network_helper.get_security_groups(project=project_id)[0]
    network_helper.add_icmp_and_tcp_rules(security_group=security_group)

    LOG.tc_step("Get original vswitch_type and assigned_function properties")
    host_list = host_helper.get_hypervisors()

    LOG.tc_step("Sync instance with compute containing ns for ssh")
    host, ns = get_host_and_ns(netid=create_network_performance[0], host_list=host_list)
    assert ns is not None, "namespace not found on host list {}".format(host_list)
    if host_list[1] != host:
        vm_helper.live_migrate_vm(vm_id=create_instances["vm_id_1"], destination_host=host)
        vm_helper.live_migrate_vm(vm_id=create_instances["vm_id_2"], destination_host=host)

    LOG.tc_step("Connect to compute node containing images")
    with host_helper.ssh_to_host(host) as node_ssh:
        LOG.tc_step("Create huge file on {}".format(create_instances["vm_id_1"]))
        ssh_cmd = ('ip netns exec {}'
                   ' ssh-keygen -R "{}"'
                   ''.format(ns, create_instances["vm_ip_1"]))
        node_ssh.send_sudo(cmd=ssh_cmd)
        node_ssh.expect()
        ssh_cmd = ('ip netns exec {} '
                    'ssh -o StrictHostKeyChecking=no '
                    '{}@{} "dd if=/dev/zero of=/tmp/test_file count={} bs=1G"'
                    ''.format(ns,
                              IMAGE_USER,
                              create_instances["vm_ip_1"],
                              FILE_SIZE))
        node_ssh.send_sudo(cmd=ssh_cmd)
        node_ssh.expect(['password:', 'Password:'], timeout=10, searchwindowsize=100)
        node_ssh.send(cmd=IMAGE_PASS)
        index = node_ssh.expect([r'{}\+0 records out'.format(FILE_SIZE)], timeout=180)
        assert index == 0, "File created successfully"

        LOG.tc_step("Copy created file from {} to {}".format(create_instances["vm_id_1"],
                                                             create_instances["vm_id_2"]))

        res = list()

        for i in range(2):
            LOG.tc_step("Start of iter {}".format(i))
            ssh_cmd = ('ip netns exec {}'
                    ' ssh-keygen -R "{}"'
                    ''.format(ns, create_instances["vm_ip_1"]))
            node_ssh.send_sudo(cmd=ssh_cmd)
            node_ssh.expect()
            ssh_cmd = ('ip netns exec {} '
                        'ssh -o StrictHostKeyChecking=no '
                        '{}@{} "ls -lrtsh /tmp/test_file;'
                        ' echo start=$(date +%s%N);'
                        ' time scp -vvv /tmp/test_file {}@{};'
                        ' echo end=$(date +%s%N)"'
                        ''.format(ns,
                                IMAGE_USER,
                                create_instances["vm_ip_1"],
                                IMAGE_USER,
                                create_instances["vm_ip_2"]))
            node_ssh.send_sudo(cmd=ssh_cmd)
            node_ssh.expect(['password:', 'Password:'], timeout=10, searchwindowsize=100)
            node_ssh.send(cmd=IMAGE_PASS)
            index = node_ssh.expect(timeout=120)
            assert index == 0, "File tranfered successfully"
            real_time = None
            for line in node_ssh.cmd_output.split("\n"):
                if "real" in line:
                    real_time = int(line.split()[1][:1]) * 60 + float(line.split()[2][:-1])
            LOG.info("real time = {}".format(real_time))
            rate = FILE_SIZE * 1000 / real_time
            res.append(rate)

    final_res = sum(res) / len(res)
    LOG.info("Avg time is : {} MB/s".format(round(final_res, 3)))
