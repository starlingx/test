###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performance test to check the time untill detection of failed VM
###

import datetime
import re
import time
from pytest import mark

from consts.auth import HostLinuxUser
from keywords import host_helper, vm_helper
from utils import exceptions
from utils.clients import ssh
from utils.tis_log import LOG


@mark.robotperformance
def test_detection_of_failed_instance(launch_instances):
    con_ssh = ssh.ControllerClient.get_active_controller()
    start_date_cmd = ("python -c \"import datetime; "
                      "print str(datetime.datetime.now())[:-3]\"")
    kill_cmd = (start_date_cmd + "&& sudo pkill -SIGKILL qemu")
    vm_host = vm_helper.get_vm_host(launch_instances)
    vm_name = vm_helper.get_vm_name_from_id(launch_instances)
    end_date_cmd = ("grep -r \"{}\" /var/log/nfv-vim.log | "
                    "grep \"powering-off\" | "
                    "tail -1 | "
                    "awk '{{print$1}}'".format(vm_name))

    res = list()

    for i in range(20):
        LOG.tc_step("Start of iter {}".format(i))
        try:
            st = str()
            et = str()

            vm_helper.get_vms()

            with host_helper.ssh_to_host(vm_host, con_ssh=con_ssh) as con_0_ssh:
                end_time = time.time() + 120
                while time.time() < end_time:
                    con_0_ssh.send(cmd="pgrep qemu")
                    con_0_ssh.expect()
                    matches = re.findall("\n([0-9]+)\n", con_0_ssh.cmd_output)
                    time.sleep(5)
                    if matches:
                        break
                else:
                    raise exceptions.TimeoutException("Timed out waiting for qemu process")

                con_0_ssh.send(cmd=kill_cmd)
                index = con_0_ssh.expect(["Password:", con_0_ssh.prompt])
                st = con_0_ssh.cmd_output.splitlines()[1]
                if index == 0:
                    con_0_ssh.send(HostLinuxUser.get_password())
                    con_0_ssh.expect()

            st_date = datetime.datetime.strptime(st, '%Y-%m-%d %H:%M:%S.%f')
            et_date = None

            end_time = time.time() + 120
            while time.time() < end_time:
                et = con_ssh.exec_cmd(cmd=end_date_cmd)[1]
                try:
                    et_date = datetime.datetime.strptime(et, '%Y-%m-%dT%H:%M:%S.%f')
                    if et_date < st_date:
                        time.sleep(5)
                        continue
                except ValueError:
                    time.sleep(5)
                    continue
                break
            else:
                raise exceptions.TimeoutException("Timed out waiting for end time")

            diff = et_date - st_date
            LOG.info("\nstart time = {}\nend time = {}".format(st, et))
            LOG.info("\ndiff = {}".format(diff))
            res.append(diff)
        finally:
            time.sleep(5)
            vm_helper.start_vms(launch_instances)

    def calc_avg(lst):
        rtrn_sum = datetime.timedelta()
        for i in lst:
            LOG.info("Iter {}: {}".format(lst.index(i), i))
            rtrn_sum += i
        return rtrn_sum/len(lst)

    final_res = calc_avg(res)
    LOG.info("Avg time is : {}".format(final_res))
