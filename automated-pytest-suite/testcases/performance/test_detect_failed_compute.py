###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test to check the time until detection of failed compute
###

import datetime

from pytest import mark

from consts.timeout import HostTimeout
from consts.stx import HostAdminState, HostOperState, HostAvailState
from keywords import system_helper, host_helper, kube_helper
from utils.clients import ssh
from utils.tis_log import LOG


@mark.robotperformance
def test_detect_failed_compute(no_simplex, no_duplex):
    con_ssh = ssh.ControllerClient.get_active_controller()
    active_controller = system_helper.get_active_controller_name()
    compute_host = system_helper.get_computes(administrative=HostAdminState.UNLOCKED,
                                              operational=HostOperState.ENABLED,
                                              availability=HostAvailState.AVAILABLE)[0]

    compute_su_prompt = r'.*compute\-([0-9]){1,}\:/home/sysadmin#'
    cmd_get_offset = ("ntpq -p | grep {} -A1 | "
                      "tail -1 | awk '{{print$8}}'".format(active_controller))
    cmd_magic_keys_enable = ("echo 1 > /proc/sys/kernel/sysrq")
    cmd_get_start_date = ("python -c \"import datetime; "
                          "print str(datetime.datetime.now())[:-3]\"")
    cmd_get_end_date = ("cat /var/log/mtcAgent.log | "
                        "grep \"{} MNFA new candidate\" | "
                        "tail -1 | awk '{{print$1}}'".format(compute_host))
    cmd_trigger_reboot = ("echo b > /proc/sysrq-trigger")

    res = list()

    for i in range(20):
        LOG.tc_step("Start of iter {}".format(i))
        st = str()
        offset = float()
        with host_helper.ssh_to_host(compute_host) as node_ssh:
            offset = float(node_ssh.exec_cmd(cmd=cmd_get_offset, get_exit_code=False)[1])/1000
            node_ssh.send_sudo(cmd="su")
            node_ssh.expect(compute_su_prompt)
            node_ssh.send_sudo(cmd=cmd_magic_keys_enable)
            node_ssh.expect(compute_su_prompt)
            st = node_ssh.exec_cmd(cmd=cmd_get_start_date, get_exit_code=False,
                                   blob=compute_su_prompt)[1]
            node_ssh.exec_sudo_cmd(cmd_trigger_reboot, get_exit_code=False)

        system_helper.wait_for_hosts_states(compute_host, check_interval=20,
                                            availability=HostAvailState.AVAILABLE)
        pods_health = kube_helper.wait_for_pods_healthy(check_interval=20,
                                                        timeout=HostTimeout.REBOOT)
        assert pods_health is True, "Check PODs health has failed"

        st_date = datetime.datetime.fromtimestamp(
            datetime.datetime.strptime(st, '%Y-%m-%d %H:%M:%S.%f').timestamp() - offset)
        et = con_ssh.exec_cmd(cmd=cmd_get_end_date, get_exit_code=False)[1]
        et_date = datetime.datetime.strptime(et, '%Y-%m-%dT%H:%M:%S.%f')
        diff = et_date - st_date
        LOG.info("\noffset = {}\nstart time = {}\nend time = {}".format(offset, st, et))
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
