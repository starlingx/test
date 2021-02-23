###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Measure OS latency. The  term latency, when used in the context of the RT Kernel,
# is the time interval between the occurrence of an event and the time when that event is "handled"
#
###

from pytest import mark

from keywords import host_helper
from utils.tis_log import LOG


@mark.robotperformance
@mark.skip(reason="In Progress")
def test_host_guest_latency():
    with host_helper.ssh_to_host("compute-0") as node_ssh:
        # cmd = "cyclictest -m -n -p 95 –D 12h -h 20 -a 3-5 -t 3"
        cmd = "cyclictest -m -n -p 95 -l 1000 -h 20 -a 1-2 -t 3"
        res = node_ssh.exec_sudo_cmd(cmd=cmd, fail_ok=False, expect_timeout=15)[1]
        LOG.info("res = {}".format(res))
        for line in res.splitlines():
            if "Min Latencies:" in line:
                min_lat = line.split(":")[1]
                t1_min, t2_min, t3_min = min_lat.split()
            elif "Avg Latencies:" in line:
                avg_lat = line.split(":")[1]
                t1_avg, t2_avg, t3_avg = avg_lat.split()
            elif "Max Latencies:" in line:
                max_lat = line.split(":")[1]
                t1_max, t2_max, t3_max = max_lat.split()
        LOG.info("\n"
                 "\tT1\tT2\tT3\n"
                 "min:\t{}\t{}\t{}\n"
                 "avg:\t{}\t{}\t{}\n"
                 "max:\t{}\t{}\t{}\n".format(t1_min, t2_min, t3_min,
                                             t1_avg, t2_avg, t3_avg,
                                             t1_max, t2_max, t3_max))
