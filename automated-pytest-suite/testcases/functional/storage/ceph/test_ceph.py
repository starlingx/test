"""
This file contains CEPH-related storage test cases.
"""

import time

from pytest import mark, param

from consts.stx import EventLogID
from keywords import host_helper, system_helper, storage_helper
from utils.tis_log import LOG

PROC_RESTART_TIME = 30  # number of seconds between process restarts


# Tested on PV1.  Runtime: 278.40  Date: Aug 2nd, 2017.  Status: Pass


@mark.parametrize('monitor', [
    param('controller-0', marks=mark.nightly),
    'controller-1',
    'storage-0'])
# Tested on PV0.  Runtime: 222.34 seconds.  Date: Aug 4, 2017  Status: Pass
@mark.usefixtures('ceph_precheck')
def test_ceph_mon_process_kill(monitor):
    """
    us69932_tc2_ceph_mon_process_kill from us69932_ceph_monitoring.odt

    Verify that ceph mon processes recover when they are killed.

    Args:
        - Nothing

    Setup:
        - Requires system with storage nodes

    Test Steps:
        1.  Run CEPH pre-check fixture to check:
            - system has storage nodes
            - health of the ceph cluster is okay
            - that we have OSDs provisioned
        2.  Pick one ceph monitor and remove it from the quorum
        3.  Kill the monitor process
        4.  Check that the appropriate alarms are raised
        5.  Restore the monitor to the quorum
        6.  Check that the alarms clear
        7.  Ensure the ceph monitor is restarted under a different pid

    Potential flaws:
        1.  We're not checking if unexpected alarms are raised (TODO)

    Teardown:
        - None

    """
    LOG.tc_step('Get process ID of ceph monitor')
    mon_pid = storage_helper.get_mon_pid(monitor)

    with host_helper.ssh_to_host(monitor) as host_ssh:
        with host_ssh.login_as_root() as root_ssh:
            LOG.tc_step('Remove the monitor')
            cmd = 'ceph mon remove {}'.format(monitor)
            root_ssh.exec_cmd(cmd)

            LOG.tc_step('Stop the ceph monitor')
            cmd = 'service ceph stop mon.{}'.format(monitor)
            root_ssh.exec_cmd(cmd)

    LOG.tc_step('Check that ceph monitor failure alarm is raised')
    system_helper.wait_for_alarm(alarm_id=EventLogID.STORAGE_DEGRADE, timeout=300)

    with host_helper.ssh_to_host(monitor) as host_ssh:
        with host_ssh.login_as_root() as root_ssh:
            LOG.tc_step('Get cluster fsid')
            cmd = 'ceph fsid'
            fsid = host_ssh.exec_cmd(cmd)[0]
            ceph_conf = '/etc/ceph/ceph.conf'

            LOG.tc_step('Remove old ceph monitor directory')
            cmd = 'rm -rf /var/lib/ceph/mon/ceph-{}'.format(monitor)
            root_ssh.exec_cmd(cmd)

            LOG.tc_step('Re-add the monitor')
            cmd = 'ceph-mon -i {} -c {} --mkfs --fsid {}'.format(monitor, ceph_conf, fsid)
            root_ssh.exec_cmd(cmd)

    LOG.tc_step('Check the ceph storage alarm condition clears')
    system_helper.wait_for_alarm_gone(alarm_id=EventLogID.STORAGE_DEGRADE, timeout=360)

    LOG.tc_step('Check the ceph-mon process is restarted with a different pid')
    mon_pid2 = None
    for i in range(0, PROC_RESTART_TIME):
        mon_pid2 = storage_helper.get_mon_pid(monitor, fail_ok=True)
        if mon_pid2 and mon_pid2 != mon_pid:
            break
        time.sleep(5)

    LOG.info('Old pid is {} and new pid is {}'.format(mon_pid, mon_pid2))
    msg = 'Process did not restart in time'
    assert mon_pid2 and mon_pid2 != mon_pid, msg


# Testd on PV0.  Ruentime: 1899.93 seconds.  Date: Aug 4, 2017.  Status: Pass


# Tested on PV0.  Runtime: 2770.23 seconds sec.  Date: Aug 4, 2017  Status: # Pass


# Tested on PV1.  Runtime: 762.41 secs  Date: Aug 2nd, 2017.  Status: Pass


# Tested on PV1.  Runtime: 1212.55 secs Date: Aug 2nd, 2017.  Status: Pass


# Tested on PV0.  Runtime: 58.82 seconds.  Status: Pass  Date: Aug 8, 2017
