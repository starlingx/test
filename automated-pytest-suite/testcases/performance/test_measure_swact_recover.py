###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test to check measure how fast the standby controller
#   becomes active and keeps the whole system running as usual
###

import datetime

from pytest import mark

from keywords import host_helper, system_helper, kube_helper
from utils.clients import ssh
from utils.tis_log import LOG


@mark.robotperformance
def test_measure_swact_recover(no_simplex):
    cmd_get_start_date = ("python -c \"import datetime; "
                          "print str(datetime.datetime.now())[:-3]\"")

    res = list()

    try:
        for i in range(2):
            LOG.tc_step("Start of iter {}".format(i))
            con_ssh = ssh.ControllerClient.get_active_controller()

            LOG.info("Get active/standby controllers")
            active_controller, standby_controller = system_helper.get_active_standby_controllers()

            cmd_get_offset = ("ntpq -p | grep {} -A1 | "
                              "tail -1 | awk '{{print$8}}'".format(active_controller))
            cmd_get_start_date = ("cat /var/log/mtcAgent.log | "
                                  "grep \"{} Action=swact\" | "
                                  "tail -1 | awk '{{print$1}}'".format(active_controller))
            cmd_get_end_date = ("cat /var/log/mtcAgent.log | "
                                "grep \"{} Task: Swact: Complete\" | "
                                "tail -1 | awk '{{print$1}}'".format(active_controller))

            LOG.info("Start swact action")
            host_helper.swact_host(hostname=active_controller)
            kube_helper.wait_for_nodes_ready(
                hosts=(active_controller, standby_controller),
                check_interval=20)

            LOG.info("Calculate swact time")
            con_ssh = ssh.ControllerClient.get_active_controller()
            with host_helper.ssh_to_host(active_controller, con_ssh=con_ssh) as con_0_ssh:
                con_0_ssh.exec_cmd(cmd="cat /var/log/mtcAgent.log", get_exit_code=False)
                st = con_0_ssh.exec_cmd(cmd=cmd_get_start_date, get_exit_code=False)[1]
                st_date = datetime.datetime.strptime(st, '%Y-%m-%dT%H:%M:%S.%f')
            offset = float(con_ssh.exec_cmd(cmd=cmd_get_offset, get_exit_code=False)[1])/1000
            et = con_ssh.exec_cmd(cmd=cmd_get_end_date, get_exit_code=False)[1]
            et_date = datetime.datetime.fromtimestamp(
                datetime.datetime.strptime(et, '%Y-%m-%dT%H:%M:%S.%f').timestamp() - offset)
            diff = et_date - st_date
            LOG.info("\nstart time = {}\nend time = {}".format(st, et))
            LOG.info("\ndiff = {}".format(diff))
            res.append(diff)
    finally:
        active_controller, standby_controller = system_helper.get_active_standby_controllers()
        if active_controller != "controller-0":
            host_helper.swact_host(hostname=active_controller)
            kube_helper.wait_for_nodes_ready(
                hosts=(active_controller, standby_controller),
                check_interval=20)

    def calc_avg(lst):
        rtrn_sum = datetime.timedelta()
        for i in lst:
            LOG.info("Iter {}: {}".format(lst.index(i), i))
            rtrn_sum += i
        return rtrn_sum/len(lst)

    final_res = calc_avg(res)
    LOG.info("Avg time is : {}".format(final_res))
