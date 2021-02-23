###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test to check the time untill detection of failed controller
###

import datetime

from pytest import mark

from consts.timeout import HostTimeout
from consts.stx import HostAvailState
from keywords import system_helper, host_helper, kube_helper
from utils.clients import ssh
from utils.tis_log import LOG


@mark.robotperformance
def test_detect_failed_controller(no_simplex):
    con_ssh = ssh.ControllerClient.get_active_controller()
    active_controller, controller_host = system_helper.get_active_standby_controllers()

    controller_su_prompt = r'.*controller\-([0-9]){1,}\:/home/sysadmin#'
    cmd_get_offset = ("ntpq -p | grep {} -A1 | "
                      "tail -1 | awk '{{print$8}}'".format(active_controller))
    cmd_magic_keys_enable = ("echo 1 > /proc/sys/kernel/sysrq")
    cmd_get_start_date = ("python -c \"import datetime; "
                          "print str(datetime.datetime.now())[:-3]\"")
    cmd_get_end_date = ("cat /var/log/mtcAgent.log | "
                        "grep --color=never \"{} MNFA new candidate\" | "
                        "tail -1 | awk '{{print$1}}'".format(controller_host))
    cmd_get_recovered_date = ("cat /var/log/mtcAgent.log | "
                              "grep --color=never '{} unlocked-enabled-available' | "
                              "tail -1 | awk '{{print$1}}'".format(controller_host))
    cmd_trigger_reboot = ("echo b > /proc/sysrq-trigger")

    res = list()
    rec_res = list()

    for i in range(20):
        LOG.tc_step("Start of iter {}".format(i))
        st = str()
        offset = float()
        with host_helper.ssh_to_host(controller_host) as node_ssh:
            offset = float(node_ssh.exec_cmd(cmd=cmd_get_offset, get_exit_code=False)[1])/1000
            node_ssh.send_sudo(cmd="su")
            node_ssh.expect(controller_su_prompt)
            node_ssh.send_sudo(cmd=cmd_magic_keys_enable)
            node_ssh.expect(controller_su_prompt)
            st = node_ssh.exec_cmd(cmd=cmd_get_start_date, get_exit_code=False,
                                   blob=controller_su_prompt)[1]
            node_ssh.exec_sudo_cmd(cmd_trigger_reboot, get_exit_code=False)

        system_helper.wait_for_hosts_states(controller_host, check_interval=20,
                                            availability=HostAvailState.AVAILABLE)
        pods_health = kube_helper.wait_for_pods_healthy(check_interval=20,
                                                        timeout=HostTimeout.REBOOT)
        assert pods_health is True, "Check PODs health has failed"

        st_date = datetime.datetime.fromtimestamp(
            datetime.datetime.strptime(st, '%Y-%m-%d %H:%M:%S.%f').timestamp() - offset)
        et = con_ssh.exec_cmd(cmd=cmd_get_end_date, get_exit_code=False)[1]
        et_date = datetime.datetime.strptime(et, '%Y-%m-%dT%H:%M:%S.%f')
        er = con_ssh.exec_cmd(cmd=cmd_get_recovered_date, get_exit_code=False)[1]
        er_date = datetime.datetime.strptime(er, '%Y-%m-%dT%H:%M:%S.%f')
        diff = et_date - st_date
        rec_diff = er_date - st_date
        LOG.info(("\noffset = {}\n"
                  "start time = {}\n"
                  "end time = {}\n"
                  "recover time = {}".format(offset, st, et, er)))
        LOG.info("\ndiff = {}".format(diff))
        LOG.info("\nrecover diff = {}".format(rec_diff))
        res.append(diff)
        rec_res.append(rec_diff)

    def calc_avg(lst):
        rtrn_sum = datetime.timedelta()
        for i in lst:
            LOG.info("Iter {}: {}".format(lst.index(i), i))
            rtrn_sum += i
        return rtrn_sum/len(lst)

    final_res = calc_avg(res)
    final_rec_res = calc_avg(rec_res)
    LOG.info("Avg time is : {}".format(final_res))
    LOG.info("Avg rec time is : {}".format(final_rec_res))
