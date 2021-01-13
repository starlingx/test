###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test dpdk live migrate latency
###

import datetime
from pytest import mark

from keywords import vm_helper
from utils import cli
from utils.clients import ssh
from utils.tis_log import LOG


@mark.robotperformance
def test_dpdk_live_migrate_latency(ovs_dpdk_1_core, launch_instances, no_simplex, no_duplex):
    con_ssh = ssh.ControllerClient.get_active_controller()
    prev_st = None
    prev_et = None
    res = list()

    for i in range(20):
        LOG.tc_step("Start of iter {}".format(i))
        vm_host = vm_helper.get_vm_host(launch_instances)
        cmd_get_pod_name = ("kubectl get pods -n openstack | "
                            "grep --color=never nova-compute-{} | "
                            "awk '{{print$1}}'".format(vm_host))
        pod_name = con_ssh.exec_cmd(cmd=cmd_get_pod_name)[1].rstrip().lstrip()
        cmd_get_start_date = ("kubectl -n openstack logs {} -c nova-compute | "
                              "grep --color=never 'instance: {}' | "
                              "grep --color=never 'pre_live_migration on destination host' | "
                              "tail -1 | "
                              "awk '{{print $1 \" \" $2}}'".format(pod_name, launch_instances))
        cmd_get_end_date = ("kubectl -n openstack logs {} -c nova-compute | "
                            "grep --color=never 'instance: {}' | "
                            "egrep --color=never "
                            "'Migrating instance to [a-zA-Z]+-[0-9] finished successfully' | "
                            "tail -1 | "
                            "awk '{{print $1 \" \" $2}}'".format(pod_name, launch_instances))

        vm_helper.live_migrate_vm(vm_id=launch_instances)

        st = con_ssh.exec_cmd(cmd=cmd_get_start_date)[1]
        et = con_ssh.exec_cmd(cmd=cmd_get_end_date)[1]
        st_date = datetime.datetime.strptime(st, '%Y-%m-%d %H:%M:%S.%f')
        et_date = datetime.datetime.strptime(et, '%Y-%m-%d %H:%M:%S.%f')
        if i == 0:
            prev_st = st_date
            prev_et = et_date
        elif i > 0:
            if st_date <= prev_st or et_date <= prev_et:
                msg = ("new start time {} is less "
                       "or equal than old start time {}\n"
                       "or new end time {} is less "
                       "or equal than old end time "
                       "{}".format(st_date, prev_st, et_date, prev_et))
                LOG.error(msg)
                raise Exception(msg)
            else:
                prev_st = st_date
                prev_et = et_date
        diff = et_date - st_date
        LOG.info("\nstart time = {}\nend time = {}".format(st, et))
        LOG.info("\ndiff = {}".format(diff))
        res.append(diff)

    def calc_avg(lst):
        rtrn_sum = datetime.timedelta()
        for i in lst:
            LOG.info("Iter {}: {}".format(lst.index(i), i))
            rtrn_sum += i
        return rtrn_sum/len(lst)

    final_res = calc_avg(res)
    LOG.info("Avg time is : {}".format(final_res))
