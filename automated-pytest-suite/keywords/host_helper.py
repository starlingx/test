#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


"""
This module is for helper functions targeting one or more STX host.

Including:
- system host-xxx commands related helper functions
(Note that system host-show, host-list related helper functions are in
system_helper.py)
- Non-system operations targeting specific host, such as ssh to a host,
sudo reboot on given host(s), etc

"""

import ast
import re
import os
import time
import copy
from contextlib import contextmanager
from xml.etree import ElementTree

from consts.proj_vars import ProjVar
from consts.auth import Tenant, TestFileServer, HostLinuxUser
from consts.timeout import HostTimeout, CMDTimeout
from consts.stx import HostAvailState, HostAdminState, HostOperState, \
    Prompt, MELLANOX_DEVICE, MaxVmsSupported, EventLogID, TrafficControl, \
    PLATFORM_NET_TYPES, AppStatus, PLATFORM_AFFINE_INCOMPLETE, FlavorSpec, \
    STORAGE_AGGREGATE
from utils import cli, exceptions, table_parser
from utils.clients.ssh import ControllerClient, SSHFromSSH, SSHClient
from utils.tis_log import LOG
from keywords import system_helper, common, kube_helper, security_helper, \
    nova_helper


@contextmanager
def ssh_to_host(hostname, username=None, password=None, prompt=None,
                con_ssh=None, timeout=60):
    """
    ssh to a host from ssh client.

    Args:
        hostname (str|None): host to ssh to. When None, return active
            controller ssh
        username (str):
        password (str):
        prompt (str):
        con_ssh (SSHClient):
        timeout (int)

    Returns (SSHClient): ssh client of the host

    Examples: with ssh_to_host('controller-1') as host_ssh:
                  host.exec_cmd(cmd)

    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    if not hostname:
        yield con_ssh
        return

    user = username if username else HostLinuxUser.get_user()
    password = password if password else HostLinuxUser.get_password()
    if not prompt:
        prompt = '.*' + hostname + r'\:~\$'
    original_host = con_ssh.get_hostname()
    if original_host != hostname:
        host_ssh = SSHFromSSH(ssh_client=con_ssh, host=hostname, user=user,
                              password=password, initial_prompt=prompt,
                              timeout=timeout)
        host_ssh.connect(prompt=prompt)
        current_host = host_ssh.get_hostname()
        if not current_host == hostname:
            raise exceptions.SSHException("Current host is {} instead of "
                                          "{}".format(current_host, hostname))
        close = True
    else:
        close = False
        host_ssh = con_ssh
    try:
        yield host_ssh
    finally:
        if close:
            host_ssh.close()


def reboot_hosts(hostnames, timeout=HostTimeout.REBOOT, con_ssh=None,
                 fail_ok=False, wait_for_offline=True,
                 wait_for_reboot_finish=True, check_hypervisor_up=True,
                 check_webservice_up=True, force_reboot=True,
                 check_up_time=True, auth_info=Tenant.get('admin_platform')):
    """
    Reboot one or multiple host(s)

    Args:
        hostnames (list|str): hostname(s) to reboot. str input is also
            acceptable when only one host to be rebooted
        timeout (int): timeout waiting for reboot to complete in seconds
        con_ssh (SSHClient): Active controller ssh
        fail_ok (bool): Whether it is okay or not for rebooting to fail on any
            host
        wait_for_offline (bool): Whether to wait for host to be offline after
            reboot
        wait_for_reboot_finish (bool): whether to wait for reboot finishes
            before return
        check_hypervisor_up (bool):
        check_webservice_up (bool):
        force_reboot (bool): whether to add -f, i.e., sudo reboot [-f]
        check_up_time (bool): Whether to ensure active controller uptime is
            more than 15 minutes before rebooting
        auth_info

    Returns (tuple): (rtn_code, message)
        (-1, "Reboot host command sent") Reboot host command is sent, but did
            not wait for host to be back up
        (0, "Host(s) state(s) - <states_dict>.") hosts rebooted and back to
            available/degraded or online state.
        (1, "Host(s) not in expected availability states or task unfinished.
            (<states>) (<task>)" )
        (2, "Hosts not up in nova hypervisor-list: <list of hosts>)"
        (3, "Hosts web-services not active in system servicegroup-list")
    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    if isinstance(hostnames, str):
        hostnames = [hostnames]

    reboot_active = False
    active_con = system_helper.get_active_controller_name(con_ssh=con_ssh,
                                                          auth_info=auth_info)
    hostnames = list(set(hostnames))
    if active_con in hostnames:
        reboot_active = True
        hostnames.remove(active_con)

    system_helper.get_hosts(con_ssh=con_ssh, auth_info=auth_info)

    is_simplex = system_helper.is_aio_simplex(con_ssh=con_ssh,
                                              auth_info=auth_info)
    user, password = security_helper.LinuxUser.get_current_user_password()
    # reboot hosts other than active controller
    cmd = 'sudo reboot -f' if force_reboot else 'sudo reboot'

    for host in hostnames:
        prompt = '.*' + host + r'\:~\$'
        host_ssh = SSHFromSSH(ssh_client=con_ssh, host=host, user=user,
                              password=password, initial_prompt=prompt)
        host_ssh.connect()
        current_host = host_ssh.get_hostname()
        if not current_host == host:
            raise exceptions.SSHException("Current host is {} instead of "
                                          "{}".format(current_host, host))

        LOG.info("Rebooting {}".format(host))
        host_ssh.send(cmd)
        host_ssh.expect(['.*[pP]assword:.*', 'Rebooting'])
        host_ssh.send(password)
        con_ssh.expect(timeout=300)

    # reconnect to lab and wait for system up if rebooting active controller
    if reboot_active:
        if check_up_time:
            LOG.info("Ensure uptime for controller(s) is at least 15 "
                     "minutes before rebooting.")
            time_to_sleep = max(0, 910 - system_helper.get_controller_uptime(
                con_ssh=con_ssh))
            time.sleep(time_to_sleep)

        LOG.info("Rebooting active controller: {}".format(active_con))
        con_ssh.send(cmd)
        index = con_ssh.expect(['.*[pP]assword:.*', 'Rebooting'])
        if index == 0:
            con_ssh.send(password)

        if is_simplex:
            _wait_for_simplex_reconnect(con_ssh=con_ssh, timeout=timeout,
                                        auth_info=auth_info)
        else:
            LOG.info("Active controller reboot started. Wait for 20 seconds "
                     "then attempt to reconnect for "
                     "maximum {}s".format(timeout))
            time.sleep(20)
            con_ssh.connect(retry=True, retry_timeout=timeout)

            LOG.info("Reconnected via fip. Waiting for system show cli to "
                     "re-enable")
            _wait_for_openstack_cli_enable(con_ssh=con_ssh, auth_info=auth_info)

    if not wait_for_offline and not is_simplex:
        msg = "{} cmd sent".format(cmd)
        LOG.info(msg)
        return -1, msg

    if hostnames:
        time.sleep(30)
        hostnames = sorted(hostnames)
        hosts_in_rebooting = system_helper.wait_for_hosts_states(
            hostnames, timeout=HostTimeout.FAIL_AFTER_REBOOT,
            check_interval=10, duration=8, con_ssh=con_ssh,
            availability=[HostAvailState.OFFLINE, HostAvailState.FAILED],
            auth_info=auth_info)

        if not hosts_in_rebooting:
            hosts_info = system_helper.get_hosts_values(
                hostnames,
                ['task', 'availability'],
                con_ssh=con_ssh,
                auth_info=auth_info)
            raise exceptions.HostError("Some hosts are not rebooting. "
                                       "\nHosts info:{}".format(hosts_info))

    if reboot_active:
        hostnames.append(active_con)
        if not is_simplex:
            system_helper.wait_for_hosts_states(
                active_con, timeout=HostTimeout.FAIL_AFTER_REBOOT,
                fail_ok=True, check_interval=10, duration=8,
                con_ssh=con_ssh,
                availability=[HostAvailState.OFFLINE, HostAvailState.FAILED],
                auth_info=auth_info)

    if not wait_for_reboot_finish:
        msg = 'Host(s) in offline state'
        LOG.info(msg)
        return -1, msg

    hosts_, admin_states = \
        system_helper.get_hosts(hostname=hostnames,
                                field=('hostname', 'administrative'),
                                con_ssh=con_ssh, auth_info=auth_info)
    unlocked_hosts = []
    locked_hosts = []
    for i in range(len(hosts_)):
        if admin_states[i] == HostAdminState.UNLOCKED:
            unlocked_hosts.append(hosts_[i])
        elif admin_states[i] == HostAdminState.LOCKED:
            locked_hosts.append(hosts_[i])

    LOG.info("Locked: {}. Unlocked:{}".format(locked_hosts, unlocked_hosts))
    sorted_total_hosts = sorted(locked_hosts + unlocked_hosts)
    if not sorted_total_hosts == hostnames:
        raise exceptions.HostError("Some hosts are neither locked or unlocked. "
                                   "\nHosts Rebooted: {}. Locked: {}; "
                                   "Unlocked: {}".format(hostnames,
                                                         locked_hosts,
                                                         unlocked_hosts))
    unlocked_hosts_in_states = True
    locked_hosts_in_states = True
    if len(locked_hosts) > 0:
        locked_hosts_in_states = \
            system_helper.wait_for_hosts_states(locked_hosts,
                                                timeout=HostTimeout.REBOOT,
                                                check_interval=10,
                                                duration=8, con_ssh=con_ssh,
                                                availability=['online'],
                                                auth_info=auth_info)

    if len(unlocked_hosts) > 0:
        unlocked_hosts_in_states = \
            system_helper.wait_for_hosts_states(unlocked_hosts,
                                                timeout=HostTimeout.REBOOT,
                                                check_interval=10,
                                                con_ssh=con_ssh,
                                                availability=['available',
                                                              'degraded'],
                                                auth_info=auth_info)

        if unlocked_hosts_in_states:
            for host_unlocked in unlocked_hosts:
                LOG.info("Waiting for task clear for {}".format(host_unlocked))
                system_helper.wait_for_host_values(
                    host_unlocked,
                    timeout=HostTimeout.TASK_CLEAR, fail_ok=False,
                    task='', auth_info=auth_info)

            LOG.info(
                "Get available hosts after task clear and wait for "
                "hypervsior/webservice up")
            hosts_avail = system_helper.get_hosts(
                availability=HostAvailState.AVAILABLE,
                hostname=unlocked_hosts,
                con_ssh=con_ssh, auth_info=auth_info)

            if hosts_avail and (check_hypervisor_up or check_webservice_up):

                all_nodes = system_helper.get_hosts_per_personality(
                    con_ssh=con_ssh, auth_info=auth_info)
                computes = list(set(hosts_avail) & set(all_nodes['compute']))
                controllers = list(
                    set(hosts_avail) & set(all_nodes['controller']))
                if system_helper.is_aio_system(con_ssh):
                    computes += controllers

                if check_webservice_up and controllers:
                    res, hosts_webdown = wait_for_webservice_up(
                        controllers, fail_ok=fail_ok, con_ssh=con_ssh,
                        timeout=HostTimeout.WEB_SERVICE_UP, auth_info=auth_info)
                    if not res:
                        err_msg = "Hosts web-services not active in system " \
                                  "servicegroup-list: {}".format(hosts_webdown)
                        if fail_ok:
                            return 3, err_msg
                        else:
                            raise exceptions.HostPostCheckFailed(err_msg)

                if check_hypervisor_up and computes:
                    res, hosts_hypervisordown = wait_for_hypervisors_up(
                        computes, fail_ok=fail_ok, con_ssh=con_ssh,
                        timeout=HostTimeout.HYPERVISOR_UP, auth_info=auth_info)
                    if not res:
                        err_msg = "Hosts not up in nova hypervisor-list: " \
                                  "{}".format(hosts_hypervisordown)
                        if fail_ok:
                            return 2, err_msg
                        else:
                            raise exceptions.HostPostCheckFailed(err_msg)

                hosts_affine_incomplete = []
                for host in list(set(computes) & set(hosts_avail)):
                    if not wait_for_tasks_affined(host, fail_ok=True,
                                                  auth_info=auth_info,
                                                  con_ssh=con_ssh):
                        hosts_affine_incomplete.append(host)

                if hosts_affine_incomplete:
                    err_msg = "Hosts platform tasks affining incomplete: " \
                              "{}".format(hosts_affine_incomplete)
                    LOG.error(err_msg)

    states_vals = {}
    failure_msg = ''
    for host in hostnames:
        vals = system_helper.get_host_values(host,
                                             fields=['task', 'availability'],
                                             rtn_dict=True)
        if not vals['task'] == '':
            failure_msg += " {} still in task: {}.".format(host, vals['task'])
        states_vals[host] = vals
    from keywords.kube_helper import wait_for_nodes_ready
    hosts_not_ready = wait_for_nodes_ready(hostnames, timeout=30,
                                           con_ssh=con_ssh, fail_ok=fail_ok)[1]
    if hosts_not_ready:
        failure_msg += " {} not ready in kubectl get ndoes".format(
            hosts_not_ready)

    message = "Host(s) state(s) - {}.".format(states_vals)

    if locked_hosts_in_states and unlocked_hosts_in_states and \
            failure_msg == '':
        succ_msg = "Hosts {} rebooted successfully".format(hostnames)
        LOG.info(succ_msg)
        return 0, succ_msg

    err_msg = "Host(s) not in expected states or task unfinished. " + \
              message + failure_msg
    if fail_ok:
        LOG.warning(err_msg)
        return 1, err_msg
    else:
        raise exceptions.HostPostCheckFailed(err_msg)


def recover_simplex(con_ssh=None, fail_ok=False,
                    auth_info=Tenant.get('admin_platform')):
    """
    Ensure simplex host is unlocked, available, and hypervisor up
    This function should only be called for simplex system

    Args:
        con_ssh (SSHClient):
        fail_ok (bool)
        auth_info (dict)

    """
    if not con_ssh:
        con_name = auth_info.get('region') if \
            (auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    if not con_ssh.is_connected():
        con_ssh.connect(retry=True, retry_timeout=HostTimeout.REBOOT)

    _wait_for_openstack_cli_enable(con_ssh=con_ssh, timeout=HostTimeout.REBOOT,
                                   auth_info=auth_info)

    host = 'controller-0'
    is_unlocked = \
        system_helper.get_host_values(host=host,
                                      fields='administrative',
                                      auth_info=auth_info,
                                      con_ssh=con_ssh)[0] \
        == HostAdminState.UNLOCKED

    if not is_unlocked:
        unlock_host(host=host, available_only=True, fail_ok=fail_ok,
                    con_ssh=con_ssh, auth_info=auth_info)
    else:
        wait_for_hosts_ready(host, fail_ok=fail_ok, check_task_affinity=False,
                             con_ssh=con_ssh, auth_info=auth_info)


def wait_for_hosts_ready(hosts, fail_ok=False, check_task_affinity=False,
                         con_ssh=None, auth_info=Tenant.get('admin_platform'),
                         timeout=None, check_interval=None):
    """
    Wait for hosts to be in online state if locked, and available and
    hypervisor/webservice up if unlocked
    Args:
        hosts:
        fail_ok: whether to raise exception when fail
        check_task_affinity
        con_ssh:
        auth_info
        timeout
        check_interval

    Returns:

    """
    if isinstance(hosts, str):
        hosts = [hosts]

    expt_online_hosts = system_helper.get_hosts(
        administrative=HostAdminState.LOCKED, hostname=hosts, con_ssh=con_ssh,
        auth_info=auth_info)
    expt_avail_hosts = system_helper.get_hosts(
        administrative=HostAdminState.UNLOCKED, hostname=hosts, con_ssh=con_ssh,
        auth_info=auth_info)

    res_lock = res_unlock = True
    timeout_args = {'timeout': timeout} if timeout else {}
    if check_interval:
        timeout_args['check_interval'] = check_interval
    from keywords import kube_helper, container_helper
    if expt_online_hosts:
        LOG.info("Wait for hosts to be online: {}".format(hosts))
        res_lock = system_helper.wait_for_hosts_states(
            expt_online_hosts,
            availability=HostAvailState.ONLINE,
            fail_ok=fail_ok,
            con_ssh=con_ssh,
            auth_info=auth_info,
            **timeout_args)

        res_kube = kube_helper.wait_for_nodes_ready(hosts=expt_online_hosts,
                                                    timeout=30,
                                                    con_ssh=con_ssh,
                                                    fail_ok=fail_ok)[0]
        res_lock = res_lock and res_kube

    if expt_avail_hosts:
        hypervisors = []
        nova_auth = Tenant.get('admin',
                               dc_region=auth_info.get('region') if
                               auth_info else None)
        hosts_per_personality = system_helper.get_hosts_per_personality(
            con_ssh=con_ssh, auth_info=auth_info)
        if container_helper.is_stx_openstack_deployed(con_ssh=con_ssh,
                                                      auth_info=auth_info):
            hypervisors = list(set(
                get_hypervisors(con_ssh=con_ssh, auth_info=nova_auth)) & set(
                expt_avail_hosts))
            computes = hypervisors
        else:
            computes = list(
                set(hosts_per_personality['compute']) & set(expt_avail_hosts))

        controllers = list(
            set(hosts_per_personality['controller']) & set(expt_avail_hosts))

        LOG.info("Wait for hosts to be available: {}".format(hosts))
        res_unlock = system_helper.wait_for_hosts_states(
            expt_avail_hosts,
            availability=HostAvailState.AVAILABLE,
            fail_ok=fail_ok,
            con_ssh=con_ssh,
            auth_info=auth_info,
            **timeout_args)

        if res_unlock:
            res_1 = wait_for_task_clear_and_subfunction_ready(
                hosts,
                fail_ok=fail_ok,
                auth_info=auth_info,
                con_ssh=con_ssh)
            res_unlock = res_unlock and res_1

        if controllers:
            LOG.info(
                "Wait for webservices up for hosts: {}".format(controllers))
            res_2 = wait_for_webservice_up(controllers, fail_ok=fail_ok,
                                           con_ssh=con_ssh, auth_info=auth_info,
                                           timeout=HostTimeout.WEB_SERVICE_UP)
            res_unlock = res_unlock and res_2
        if hypervisors:
            LOG.info(
                "Wait for hypervisors up for hosts: {}".format(hypervisors))
            res_3 = wait_for_hypervisors_up(hypervisors, fail_ok=fail_ok,
                                            con_ssh=con_ssh,
                                            auth_info=nova_auth,
                                            timeout=HostTimeout.HYPERVISOR_UP)
            res_unlock = res_unlock and res_3

        if computes and check_task_affinity:
            for host in computes:
                # Do not fail the test due to task affining incomplete for
                # now to unblock test case.
                wait_for_tasks_affined(host, fail_ok=True, auth_info=auth_info,
                                       con_ssh=con_ssh)
                # res_4 = wait_for_tasks_affined(host=host, fail_ok=fail_ok,
                # auth_info=auth_info, con_ssh=con_ssh)
                # res_unlock = res_unlock and res_4

        res_kube = \
            kube_helper.wait_for_nodes_ready(hosts=expt_avail_hosts, timeout=30,
                                             con_ssh=con_ssh,
                                             fail_ok=fail_ok)[0]
        res_unlock = res_unlock and res_kube

    return res_lock and res_unlock


def wait_for_task_clear_and_subfunction_ready(
        hosts, fail_ok=False, con_ssh=None,
        timeout=HostTimeout.SUBFUNC_READY,
        auth_info=Tenant.get('admin_platform')):
    if isinstance(hosts, str):
        hosts = [hosts]

    hosts_to_check = list(hosts)
    LOG.info("Waiting for task clear and subfunctions enable/available "
             "(if applicable) for hosts: {}".format(hosts_to_check))
    end_time = time.time() + timeout
    while time.time() < end_time:
        hosts_vals = system_helper.get_hosts_values(
            hosts_to_check,
            ['subfunction_avail', 'subfunction_oper', 'task'],
            con_ssh=con_ssh,
            auth_info=auth_info)
        for host, vals in hosts_vals.items():
            if not vals['task'] and vals['subfunction_avail'] in \
                    ('', HostAvailState.AVAILABLE) and \
                    vals['subfunction_oper'] in ('', HostOperState.ENABLED):
                hosts_to_check.remove(host)

        if not hosts_to_check:
            LOG.info(
                "Hosts task cleared and subfunctions (if applicable) are now "
                "in enabled/available states")
            return True

        time.sleep(10)

    err_msg = "Host(s) subfunctions are not all in enabled/available states: " \
              "{}".format(hosts_to_check)
    if fail_ok:
        LOG.warning(err_msg)
        return False

    raise exceptions.HostError(err_msg)


def lock_host(host, force=False, lock_timeout=HostTimeout.LOCK,
              timeout=HostTimeout.ONLINE_AFTER_LOCK, con_ssh=None,
              fail_ok=False, check_first=True, swact=False,
              check_cpe_alarm=True, auth_info=Tenant.get('admin_platform')):
    """
    lock a host.

    Args:
        host (str): hostname or id in string format
        force (bool):
        lock_timeout (int): max time in seconds waiting for host to goto
        locked state after locking attempt.
        timeout (int): how many seconds to wait for host to go online after lock
        con_ssh (SSHClient):
        fail_ok (bool):
        check_first (bool):
        swact (bool): whether to check if host is active controller and do a
        swact before attempt locking
        check_cpe_alarm (bool): whether to wait for cpu usage alarm gone
        before locking
        auth_info

    Returns: (return_code(int), msg(str))   # 1, 2, 3, 4, 5, 6 only returns
    when fail_ok=True
        (-1, "Host already locked. Do nothing.")
        (0, "Host is locked and in online state."]
        (1, <stderr>)   # Lock host cli rejected
        (2, "Host is not in locked state")  # cli ran okay, but host did not
        reach locked state within timeout
        (3, "Host did not go online within <timeout> seconds after (force)
        lock")   # Locked but didn't go online
        (4, "Lock host <host> is rejected. Details in host-show
        vim_process_status.")
        (5, "Lock host <host> failed due to migrate vm failed. Details in
        host-show vm_process_status.")
        (6, "Task is not cleared within 180 seconds after host goes online")

    """
    host_avail, host_admin = \
        system_helper.get_host_values(host,
                                      ('availability', 'administrative'),
                                      con_ssh=con_ssh, auth_info=auth_info)
    if host_avail in [HostAvailState.OFFLINE, HostAvailState.FAILED]:
        LOG.warning("Host in offline or failed state before locking!")

    if check_first and host_admin == 'locked':
        msg = "{} already locked. Do nothing.".format(host)
        LOG.info(msg)
        return -1, msg

    is_aio_dup = system_helper.is_aio_duplex(con_ssh=con_ssh,
                                             auth_info=auth_info)

    if swact:
        if system_helper.is_active_controller(host, con_ssh=con_ssh,
                                              auth_info=auth_info) and \
                len(system_helper.get_controllers(
                    con_ssh=con_ssh, auth_info=auth_info,
                    operational=HostOperState.ENABLED)) > 1:
            LOG.info("{} is active controller, swact first before attempt to "
                     "lock.".format(host))
            swact_host(host, auth_info=auth_info, con_ssh=con_ssh)
            if is_aio_dup:
                time.sleep(90)

    if check_cpe_alarm and is_aio_dup:
        LOG.info(
            "For AIO-duplex, wait for cpu usage high alarm gone on active "
            "controller before locking standby")
        active_con = system_helper.get_active_controller_name(
            con_ssh=con_ssh, auth_info=auth_info)
        entity_id = 'host={}'.format(active_con)
        system_helper.wait_for_alarms_gone(
            [(EventLogID.CPU_USAGE_HIGH, entity_id)], check_interval=45,
            fail_ok=fail_ok, con_ssh=con_ssh, timeout=300, auth_info=auth_info)

    positional_arg = host
    extra_msg = ''
    if force:
        positional_arg += ' --force'
        extra_msg = 'force '

    LOG.info("Locking {}...".format(host))
    exitcode, output = cli.system('host-lock', positional_arg,
                                  ssh_client=con_ssh,
                                  fail_ok=fail_ok, auth_info=auth_info)

    if exitcode == 1:
        return 1, output

    table_ = table_parser.table(output)
    task_val = table_parser.get_value_two_col_table(table_, field='task')
    admin_val = table_parser.get_value_two_col_table(table_,
                                                     field='administrative')

    if admin_val != HostAdminState.LOCKED:
        if 'Locking' not in task_val:
            system_helper.wait_for_host_values(host=host, timeout=30,
                                               check_interval=0, fail_ok=True,
                                               task='Locking',
                                               con_ssh=con_ssh,
                                               auth_info=auth_info)

        # Wait for task complete. If task stucks, fail the test regardless.
        # Perhaps timeout needs to be increased.
        system_helper.wait_for_host_values(host=host, timeout=lock_timeout,
                                           task='', fail_ok=False,
                                           con_ssh=con_ssh,
                                           auth_info=auth_info)

        if not system_helper.wait_for_host_values(
                host, timeout=20,
                administrative=HostAdminState.LOCKED,
                con_ssh=con_ssh,
                auth_info=auth_info):

            #  vim_progress_status | Lock of host compute-0 rejected because
            #  there are no other hypervisors available.
            vim_status = \
                system_helper.get_host_values(host,
                                              fields='vim_progress_status',
                                              auth_info=auth_info,
                                              con_ssh=con_ssh,
                                              merge_lines=True)[0]
            if re.search('ock .* host .* rejected.*', vim_status):
                msg = "Lock host {} is rejected. Details in host-show " \
                      "vim_process_status.".format(host)
                code = 4
            elif re.search('Migrate of instance .* from host .* failed.*',
                           vim_status):
                msg = "Lock host {} failed due to migrate vm failed. Details " \
                      "in host-show vm_process_status.".format(host)
                code = 5
            else:
                msg = "Host is not in locked state"
                code = 2

            if fail_ok:
                return code, msg
            raise exceptions.HostPostCheckFailed(msg)

    LOG.info("{} is {}locked. Waiting for it to go Online...".format(host,
                                                                     extra_msg))

    if system_helper.wait_for_host_values(host, timeout=timeout,
                                          availability=HostAvailState.ONLINE,
                                          auth_info=auth_info, con_ssh=con_ssh):
        # ensure the online status lasts for more than 5 seconds. Sometimes
        # host goes online then offline to reboot..
        time.sleep(5)
        if system_helper.wait_for_host_values(
                host, timeout=timeout,
                availability=HostAvailState.ONLINE,
                auth_info=auth_info,
                con_ssh=con_ssh):
            if system_helper.wait_for_host_values(
                    host,
                    timeout=HostTimeout.TASK_CLEAR,
                    task='', auth_info=auth_info,
                    con_ssh=con_ssh):
                LOG.info("Host is successfully locked and in online state.")
                return 0, "Host is locked and in online state."
            else:
                msg = "Task is not cleared within {} seconds after host goes " \
                      "online".format(HostTimeout.TASK_CLEAR)
                if fail_ok:
                    LOG.warning(msg)
                    return 6, msg
                raise exceptions.HostPostCheckFailed(msg)

    msg = "Host did not go online within {} seconds after {}lock".format(
        timeout, extra_msg)
    if fail_ok:
        return 3, msg
    else:
        raise exceptions.HostPostCheckFailed(msg)


def _wait_for_simplex_reconnect(con_ssh=None,
                                timeout=HostTimeout.CONTROLLER_UNLOCK,
                                auth_info=Tenant.get('admin_platform'),
                                duplex_direct=False):
    time.sleep(30)
    if not con_ssh:
        con_name = auth_info.get('region') if \
            (auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    con_ssh.wait_for_disconnect(check_interval=10, timeout=300)
    time.sleep(30)
    con_ssh.connect(retry=True, retry_timeout=timeout)
    ControllerClient.set_active_controller(con_ssh)

    if not duplex_direct:
        # Give it sometime before openstack cmds enables on after host
        _wait_for_openstack_cli_enable(con_ssh=con_ssh, auth_info=auth_info,
                                       fail_ok=False, timeout=timeout,
                                       check_interval=10,
                                       reconnect=True, single_node=True)
        time.sleep(10)
        LOG.info("Re-connected via ssh and openstack CLI enabled")


def unlock_host(host, timeout=HostTimeout.CONTROLLER_UNLOCK,
                available_only=True, fail_ok=False, con_ssh=None,
                auth_info=Tenant.get('admin_platform'),
                check_hypervisor_up=True,
                check_webservice_up=True, check_subfunc=True, check_first=True,
                con0_install=False,
                check_containers=True):
    """
    Unlock given host
    Args:
        host (str):
        timeout (int): MAX seconds to wait for host to become available or
        degraded after unlocking
        available_only(bool): if True, wait for host becomes Available after
        unlock; otherwise wait for either
            Degraded or Available
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        check_hypervisor_up (bool): Whether to check if host is up in nova
            hypervisor-list
        check_webservice_up (bool): Whether to check if host's web-service is
            active in system servicegroup-list
        check_subfunc (bool): whether to check subfunction_oper and
            subfunction_avail for CPE system
        check_first (bool): whether to check host state before unlock.
        con0_install (bool)
        check_containers (bool)

    Returns (tuple):  Only -1, 0, 4 senarios will be returned if fail_ok=False
        (-1, "Host already unlocked. Do nothing")
        (0, "Host is unlocked and in available state.")
        (1, <stderr>)   # cli returns stderr. only applicable if fail_ok
        (2, "Host is not in unlocked state")    # only applicable if fail_ok
        (3, "Host state did not change to available or degraded within
            timeout")    # only applicable if fail_ok
        (4, "Host is in degraded state after unlocked.")    # Only applicable
            if available_only=False
        (5, "Task is not cleared within 180 seconds after host goes
            available")        # Applicable if fail_ok
        (6, "Host is not up in nova hypervisor-list")   # Host with compute
            function only. Applicable if fail_ok
        (7, "Host web-services is not active in system servicegroup-list") #
            controllers only. Applicable if fail_ok
        (8, "Failed to wait for host to reach Available state after unlocked
            to Degraded state")
                # only applicable if fail_ok and available_only are True
        (9, "Host subfunctions operational and availability are not enable
            and available system host-show") # CPE only
        (10, "<host> is not ready in kubectl get nodes after unlock")

    """
    LOG.info("Unlocking {}...".format(host))
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    if check_first:
        if system_helper.get_host_values(host, 'availability', con_ssh=con_ssh,
                                         auth_info=auth_info)[0] in \
                [HostAvailState.OFFLINE, HostAvailState.FAILED]:
            LOG.info(
                "Host is offline or failed, waiting for it to go online, "
                "available or degraded first...")
            system_helper.wait_for_host_values(host, availability=[
                HostAvailState.AVAILABLE, HostAvailState.ONLINE,
                HostAvailState.DEGRADED], con_ssh=con_ssh,
                                               fail_ok=False,
                                               auth_info=auth_info)

        if system_helper.get_host_values(host, 'administrative',
                                         con_ssh=con_ssh,
                                         auth_info=auth_info)[0] == \
                HostAdminState.UNLOCKED:
            message = "Host already unlocked. Do nothing"
            LOG.info(message)
            return -1, message

    is_simplex = system_helper.is_aio_simplex(con_ssh=con_ssh,
                                              auth_info=auth_info)

    from keywords import kube_helper, container_helper
    check_stx = prev_bad_pods = None
    if check_containers:
        check_stx = container_helper.is_stx_openstack_deployed(
            applied_only=True, con_ssh=con_ssh, auth_info=auth_info)
        prev_bad_pods = kube_helper.get_unhealthy_pods(node=host,
                                                       con_ssh=con_ssh,
                                                       all_namespaces=True)
    exitcode, output = cli.system('host-unlock', host, ssh_client=con_ssh,
                                  fail_ok=fail_ok, auth_info=auth_info,
                                  timeout=60)
    if exitcode == 1:
        return 1, output

    if is_simplex or con0_install:
        time.sleep(120)
        _wait_for_simplex_reconnect(con_ssh=con_ssh, auth_info=auth_info,
                                    timeout=timeout)

    if not system_helper.wait_for_host_values(
            host, timeout=60,
            administrative=HostAdminState.UNLOCKED,
            con_ssh=con_ssh,
            fail_ok=fail_ok,
            auth_info=auth_info):
        return 2, "Host is not in unlocked state"

    if not system_helper.wait_for_host_values(
            host, timeout=timeout, fail_ok=fail_ok,
            check_interval=10, con_ssh=con_ssh, auth_info=auth_info,
            availability=[HostAvailState.AVAILABLE, HostAvailState.DEGRADED]):
        return 3, "Host state did not change to available or degraded within " \
                  "timeout"

    if not system_helper.wait_for_host_values(host,
                                              timeout=HostTimeout.TASK_CLEAR,
                                              fail_ok=fail_ok, con_ssh=con_ssh,
                                              auth_info=auth_info,
                                              task=''):
        return 5, "Task is not cleared within {} seconds after host goes " \
                  "available".format(HostTimeout.TASK_CLEAR)

    if check_hypervisor_up or check_webservice_up or check_subfunc:

        subfunc, personality = system_helper.get_host_values(
            host, fields=('subfunctions', 'personality'),
            con_ssh=con_ssh, auth_info=auth_info)
        string_total = subfunc + personality

        is_controller = 'controller' in string_total
        is_compute = bool(re.search('compute|worker', string_total))

        if check_hypervisor_up and is_compute:
            if container_helper.is_stx_openstack_deployed(con_ssh=con_ssh,
                                                          auth_info=auth_info):
                nova_auth = Tenant.get('admin', dc_region=auth_info.get(
                    'region') if auth_info else None)
                if not wait_for_hypervisors_up(
                        host, fail_ok=fail_ok, con_ssh=con_ssh,
                        auth_info=nova_auth,
                        timeout=HostTimeout.HYPERVISOR_UP)[0]:
                    return 6, "Host is not up in nova hypervisor-list"

            if not is_simplex:
                # wait_for_tasks_affined(host, con_ssh=con_ssh)
                # Do not fail the test due to task affining incomplete for
                # now to unblock test case.
                wait_for_tasks_affined(host, con_ssh=con_ssh, fail_ok=True)

        if check_webservice_up and is_controller:
            if not \
                wait_for_webservice_up(host, fail_ok=fail_ok, con_ssh=con_ssh,
                                       auth_info=auth_info, timeout=300)[0]:
                return 7, "Host web-services is not active in system " \
                          "servicegroup-list"

        if check_subfunc and is_controller and is_compute:
            # wait for subfunction states to be operational enabled and
            # available
            if not system_helper.wait_for_host_values(
                    host, timeout=90,
                    fail_ok=fail_ok,
                    con_ssh=con_ssh,
                    auth_info=auth_info,
                    subfunction_oper=HostOperState.ENABLED,
                    subfunction_avail=HostAvailState.AVAILABLE):
                err_msg = "Host subfunctions operational and availability " \
                          "did not change to enabled and available" \
                          " within timeout"
                LOG.warning(err_msg)
                return 9, err_msg

    if check_containers:
        from keywords import kube_helper, container_helper

        res_nodes = kube_helper.wait_for_nodes_ready(hosts=host, timeout=180,
                                                     con_ssh=con_ssh,
                                                     fail_ok=fail_ok)[0]
        res_app = True
        if check_stx:
            res_app = container_helper.wait_for_apps_status(
                apps='stx-openstack',
                status=AppStatus.APPLIED,
                auth_info=auth_info,
                con_ssh=con_ssh,
                check_interval=10,
                fail_ok=fail_ok)[0]

        res_pods = kube_helper.wait_for_pods_healthy(check_interval=10,
                                                     con_ssh=con_ssh,
                                                     fail_ok=fail_ok,
                                                     node=host,
                                                     name=prev_bad_pods,
                                                     exclude=True,
                                                     all_namespaces=True)

        if not (res_nodes and res_app and res_pods):
            err_msg = "Container check failed after unlock {}".format(host)
            return 10, err_msg

    if system_helper.get_host_values(host, 'availability', con_ssh=con_ssh,
                                     auth_info=auth_info)[0] == \
            HostAvailState.DEGRADED:
        if not available_only:
            LOG.warning("Host is in degraded state after unlocked.")
            return 4, "Host is in degraded state after unlocked."
        else:
            if not system_helper.wait_for_host_values(
                    host, timeout=timeout,
                    fail_ok=fail_ok,
                    check_interval=10,
                    con_ssh=con_ssh,
                    availability=HostAvailState.AVAILABLE,
                    auth_info=auth_info):
                err_msg = "Failed to wait for host to reach Available state " \
                          "after unlocked to Degraded state"
                LOG.warning(err_msg)
                return 8, err_msg

    LOG.info(
        "Host {} is successfully unlocked and in available state".format(host))
    return 0, "Host is unlocked and in available state."


def unlock_hosts(hosts, timeout=HostTimeout.CONTROLLER_UNLOCK, fail_ok=True,
                 con_ssh=None,
                 auth_info=Tenant.get('admin_platform'),
                 check_hypervisor_up=False, check_webservice_up=False,
                 check_nodes_ready=True, check_containers=False):
    """
    Unlock given hosts. Please use unlock_host() keyword if only one host
    needs to be unlocked.
    Args:
        hosts (list|str): Host(s) to unlock
        timeout (int): MAX seconds to wait for host to become available or
        degraded after unlocking
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        check_hypervisor_up (bool): Whether to check if host is up in nova
        hypervisor-list
        check_webservice_up (bool): Whether to check if host's web-service is
        active in system servicegroup-list
        check_nodes_ready (bool)
        check_containers (bool)


    Returns (dict): {host_0: res_0, host_1: res_1, ...}
        where res is a tuple as below, and scenario 1, 2, 3 only applicable
        if fail_ok=True
        (-1, "Host already unlocked. Do nothing")
        (0, "Host is unlocked and in available state.")
        (1, <stderr>)
        (2, "Host is not in unlocked state")
        (3, "Host is not in available or degraded state.")
        (4, "Host is in degraded state after unlocked.")
        (5, "Host is not up in nova hypervisor-list")   # Host with compute
        function only
        (6, "Host web-services is not active in system servicegroup-list") #
        controllers only
        (7, "Host platform tasks affining incomplete")
        (8, "Host status not ready in kubectl get nodes")

    """
    if not hosts:
        raise ValueError("No host(s) provided to unlock.")

    LOG.info("Unlocking {}...".format(hosts))

    if isinstance(hosts, str):
        hosts = [hosts]

    res = {}
    hosts_to_unlock = list(set(hosts))
    for host in hosts:
        if system_helper.get_host_values(host, 'administrative',
                                         con_ssh=con_ssh,
                                         auth_info=auth_info)[0] == \
                HostAdminState.UNLOCKED:
            message = "Host already unlocked. Do nothing"

            res[host] = -1, message
            hosts_to_unlock.remove(host)

    if not hosts_to_unlock:
        LOG.info("Host(s) already unlocked. Do nothing.")
        return res

    if len(hosts_to_unlock) != len(hosts):
        LOG.info("Some host(s) already unlocked. Unlocking the rest: {}".format(
            hosts_to_unlock))

    is_simplex = system_helper.is_aio_simplex(con_ssh=con_ssh,
                                              auth_info=auth_info)

    check_stx = prev_bad_pods = None
    if check_containers:
        from keywords import kube_helper, container_helper
        check_stx = container_helper.is_stx_openstack_deployed(
            applied_only=True, con_ssh=con_ssh, auth_info=auth_info)
        prev_bad_pods = kube_helper.get_unhealthy_pods(con_ssh=con_ssh,
                                                       all_namespaces=True)

    hosts_to_check = []
    for host in hosts_to_unlock:
        exitcode, output = cli.system('host-unlock', host, ssh_client=con_ssh,
                                      fail_ok=fail_ok,
                                      auth_info=auth_info, timeout=60)
        if exitcode == 1:
            res[host] = 1, output
        else:
            hosts_to_check.append(host)

    if not hosts_to_check:
        LOG.warning("Unlock host(s) rejected: {}".format(hosts_to_unlock))
        return res

    if is_simplex:
        _wait_for_simplex_reconnect(con_ssh=con_ssh,
                                    timeout=HostTimeout.CONTROLLER_UNLOCK,
                                    auth_info=auth_info)

    if not system_helper.wait_for_hosts_states(
            hosts_to_check, timeout=60,
            administrative=HostAdminState.UNLOCKED,
            con_ssh=con_ssh,
            auth_info=auth_info):
        LOG.warning("Some host(s) not in unlocked states after 60 seconds.")

    if not system_helper.wait_for_hosts_states(
            hosts_to_check, timeout=timeout, check_interval=10,
            con_ssh=con_ssh, auth_info=auth_info,
            availability=[HostAvailState.AVAILABLE, HostAvailState.DEGRADED]):
        LOG.warning(
            "Some host(s) state did not change to available or degraded "
            "within timeout")

    hosts_vals = system_helper.get_hosts(hostname=hosts_to_check,
                                         field=('hostname', 'availability'),
                                         administrative=HostAdminState.UNLOCKED,
                                         con_ssh=con_ssh, auth_info=auth_info)
    hosts_unlocked, hosts_avails_, = hosts_vals
    indices = range(len(hosts_unlocked))
    hosts_not_unlocked = list(set(hosts_to_check) - set(hosts_unlocked))
    hosts_avail = [hosts_unlocked[i] for i in indices if
                   hosts_avails_[i].lower() == HostAvailState.AVAILABLE]
    hosts_degrd = [hosts_unlocked[i] for i in indices if
                   hosts_avails_[i].lower() == HostAvailState.DEGRADED]
    hosts_other = list(
        set(hosts_unlocked) - set(hosts_avail) - set(hosts_degrd))

    for host in hosts_not_unlocked:
        res[host] = 2, "Host is not in unlocked state."
    for host in hosts_degrd:
        res[host] = 4, "Host is in degraded state after unlocked."
    for host in hosts_other:
        res[host] = 3, "Host is not in available or degraded state."

    if hosts_avail and (check_hypervisor_up or check_webservice_up):

        all_nodes = system_helper.get_hosts_per_personality(con_ssh=con_ssh,
                                                            auth_info=auth_info)
        computes = list(set(hosts_avail) & set(all_nodes['compute']))
        controllers = list(set(hosts_avail) & set(all_nodes['controller']))
        if system_helper.is_aio_system(con_ssh, auth_info=auth_info):
            computes += controllers

        if check_hypervisor_up and computes:
            nova_auth = Tenant.get('admin', dc_region=auth_info.get(
                'region') if auth_info else None)
            hosts_hypervisordown = \
                wait_for_hypervisors_up(computes, fail_ok=fail_ok,
                                        con_ssh=con_ssh,
                                        timeout=HostTimeout.HYPERVISOR_UP,
                                        auth_info=nova_auth)[1]
            for host in hosts_hypervisordown:
                res[host] = 5, "Host is not up in nova hypervisor-list"
                hosts_avail = list(set(hosts_avail) - set(hosts_hypervisordown))

        if check_webservice_up and controllers:
            hosts_webdown = wait_for_webservice_up(controllers, fail_ok=fail_ok,
                                                   con_ssh=con_ssh, timeout=180,
                                                   auth_info=auth_info)[1]
            for host in hosts_webdown:
                res[host] = 6, "Host web-services is not active in system " \
                               "servicegroup-list"
            hosts_avail = list(set(hosts_avail) - set(hosts_webdown))

        hosts_affine_incomplete = []
        for host in list(set(computes) & set(hosts_avail)):
            if not wait_for_tasks_affined(host, fail_ok=True,
                                          auth_info=auth_info):
                msg = "Host {} platform tasks affining incomplete".format(host)
                hosts_affine_incomplete.append(host)

                # Do not fail the test due to task affining incomplete for
                # now to unblock test case.
                LOG.error(msg)
                # res[host] = 7,
        # hosts_avail = list(set(hosts_avail) - set(hosts_affine_incomplete))

    if check_nodes_ready and (hosts_avail or hosts_degrd):
        from keywords import kube_helper, container_helper

        hosts_to_wait = list(hosts_avail)
        hosts_to_wait += hosts_degrd
        res_nodes, hosts_not_ready = kube_helper.wait_for_nodes_ready(
            hosts=hosts_to_wait, timeout=180, con_ssh=con_ssh,
            fail_ok=fail_ok)
        if hosts_not_ready:
            hosts_avail = list(set(hosts_avail) - set(hosts_not_ready))
            for host in hosts_not_ready:
                res[host] = 8, "Host status not ready in kubectl get nodes"

        if check_containers:
            res_app = True
            if check_stx:
                res_app = container_helper.wait_for_apps_status(
                    apps='stx-openstack',
                    status=AppStatus.APPLIED,
                    con_ssh=con_ssh,
                    check_interval=10,
                    fail_ok=fail_ok)[0]
            res_pods = kube_helper.wait_for_pods_healthy(check_interval=10,
                                                         con_ssh=con_ssh,
                                                         fail_ok=fail_ok,
                                                         name=prev_bad_pods,
                                                         exclude=True,
                                                         all_namespaces=True)
            if not (res_app and res_pods):
                err_msg = "Application status or pods status check failed " \
                          "after unlock {}".format(hosts)
                hosts_to_update = list(
                    (set(hosts_to_wait) - set(hosts_not_ready)))
                hosts_avail = []
                for host_ in hosts_to_update:
                    res[host_] = 9, err_msg

    for host in hosts_avail:
        res[host] = 0, "Host is unlocked and in available state."

    if not len(res) == len(hosts):
        raise exceptions.CommonError(
            "Something wrong with the keyword. Number of hosts in result is "
            "incorrect.")

    if not fail_ok:
        for host in res:
            if res[host][0] not in [-1, 0, 4]:
                raise exceptions.HostPostCheckFailed(
                    " Not all host(s) unlocked successfully. Detail: {}".format(
                        res))

    LOG.info("Results for unlocking hosts: {}".format(res))
    return res


def _wait_for_openstack_cli_enable(con_ssh=None, timeout=HostTimeout.SWACT,
                                   fail_ok=False, check_interval=10,
                                   reconnect=True, single_node=None,
                                   auth_info=Tenant.get('admin_platform')):
    """
    Wait for 'system show' cli to work on active controller. Also wait for
    host task to clear and subfunction ready.
    Args:
        con_ssh:
        timeout:
        fail_ok:
        check_interval:
        reconnect:
        auth_info

    Returns (bool):

    """
    from keywords import container_helper

    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    def check_sysinv_cli():

        cli.system('show', ssh_client=con_ssh, auth_info=auth_info,
                   timeout=10)
        time.sleep(10)
        active_con = system_helper.get_active_controller_name(
            con_ssh=con_ssh, auth_info=auth_info)

        if ((single_node or (
                single_node is None and system_helper.is_aio_simplex())) and
                system_helper.get_host_values(active_con,
                                              fields='administrative')[
                    0] == HostAdminState.LOCKED):
            LOG.info(
                "Simplex system in locked state. Wait for task to clear only")
            system_helper.wait_for_host_values(host=active_con,
                                               timeout=HostTimeout.LOCK,
                                               task='', con_ssh=con_ssh,
                                               auth_info=auth_info)
        else:
            wait_for_task_clear_and_subfunction_ready(hosts=active_con,
                                                      con_ssh=con_ssh,
                                                      auth_info=auth_info)
        is_openstack_applied = container_helper.is_stx_openstack_deployed(
            con_ssh=con_ssh, auth_info=auth_info)
        LOG.info("system cli and subfunction enabled")
        return is_openstack_applied

    def check_nova_cli():
        region = auth_info.get('region', None) if auth_info else None
        nova_auth = Tenant.get('admin', dc_region=region)
        cli.openstack('server list', ssh_client=con_ssh, auth_info=nova_auth,
                      timeout=10)
        LOG.info("nova cli enabled")

    cli_enable_end_time = time.time() + timeout
    LOG.info(
        "Waiting for system cli and subfunctions to be ready and nova cli (if "
        "stx-openstack applied) to be "
        "enabled on active controller")
    check_nova = None
    while time.time() < cli_enable_end_time:
        try:
            if check_nova is None:
                check_nova = check_sysinv_cli()
            if check_nova:
                check_nova_cli()
            return True
        except:
            if not con_ssh.is_connected():
                if reconnect:
                    LOG.info(
                        "con_ssh connection lost while waiting for system to "
                        "recover. Attempt to reconnect...")
                    con_ssh.connect(retry_timeout=timeout, retry=True)
                else:
                    LOG.error("system disconnected")
                    if fail_ok:
                        return False
                    raise

            time.sleep(check_interval)

    err_msg = "Timed out waiting for system to recover. Time waited: {}".format(
        timeout)
    if fail_ok:
        LOG.warning(err_msg)
        return False
    raise TimeoutError(err_msg)


def swact_host(hostname=None, swact_start_timeout=HostTimeout.SWACT,
               swact_complete_timeout=HostTimeout.SWACT,
               fail_ok=False, auth_info=Tenant.get('admin_platform'),
               con_ssh=None, wait_for_alarm=False):
    """
    Swact active controller from given hostname.

    Args:
        hostname (str|None): When None, active controller will be used for
            swact.
        swact_start_timeout (int): Max time to wait between cli executes and
            swact starts
        swact_complete_timeout (int): Max time to wait for swact to complete
            after swact started
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info
        wait_for_alarm (bool),: whether to wait for pre-swact alarms after swact

    Returns (tuple): (rtn_code(int), msg(str))      # 1, 3, 4 only returns
    when fail_ok=True
        (0, "Active controller is successfully swacted.")
        (1, <stderr>)   # swact host cli rejected
        (2, "<hostname> is not active controller host, thus swact request
            failed as expected.")
        (3, "Swact did not start within <swact_start_timeout>")
        (4, "Active controller did not change after swact within
            <swact_complete_timeou>")

    """
    active_host = system_helper.get_active_controller_name(con_ssh=con_ssh,
                                                           auth_info=auth_info)
    if hostname is None:
        hostname = active_host

    pre_alarms = None
    if wait_for_alarm:
        pre_alarms = system_helper.get_alarms(con_ssh=con_ssh,
                                              auth_info=auth_info)

    exitcode, msg = cli.system('host-swact', hostname, ssh_client=con_ssh,
                               fail_ok=fail_ok, auth_info=auth_info)
    if exitcode == 1:
        return 1, msg

    if hostname != active_host:
        system_helper.wait_for_host_values(hostname,
                                           timeout=swact_start_timeout,
                                           fail_ok=False, con_ssh=con_ssh,
                                           auth_info=auth_info, task='')
        return 2, "{} is not active controller host, thus swact request " \
                  "failed as expected.".format(hostname)
    else:
        rtn = wait_for_swact_complete(
            hostname, con_ssh, swact_start_timeout=swact_start_timeout,
            auth_info=auth_info, swact_complete_timeout=swact_complete_timeout,
            fail_ok=fail_ok)
    if rtn[0] == 0:
        nova_auth = Tenant.get('admin', dc_region=auth_info.get(
            'region') if auth_info else None)
        try:
            res = wait_for_webservice_up(
                system_helper.get_active_controller_name(),
                fail_ok=fail_ok,
                auth_info=auth_info, con_ssh=con_ssh)[0]
            if not res:
                return 5, "Web-services for new controller is not active"

            if system_helper.is_aio_duplex(con_ssh=con_ssh,
                                           auth_info=auth_info):
                hypervisor_up_res = wait_for_hypervisors_up(hostname,
                                                            fail_ok=fail_ok,
                                                            con_ssh=con_ssh,
                                                            auth_info=nova_auth)
                if not hypervisor_up_res:
                    return 6, "Hypervisor state is not up for {} after " \
                              "swacted".format(hostname)

                for host in ('controller-0', 'controller-1'):
                    task_aff_res = wait_for_tasks_affined(host, con_ssh=con_ssh,
                                                          fail_ok=True,
                                                          auth_info=auth_info,
                                                          timeout=300)
                    if not task_aff_res:
                        msg = "tasks affining incomplete on {} after swact " \
                              "from {}".format(host, hostname)
                        # Do not fail the test due to task affining
                        # incomplete for now to unblock test case.
                        LOG.error(msg=msg)
                        return 7, msg
        finally:
            # After swact, there is a delay for alarms to re-appear on new
            # active controller, thus the wait.
            if pre_alarms:
                post_alarms = system_helper.get_alarms(con_ssh=con_ssh,
                                                       auth_info=auth_info)
                for alarm in pre_alarms:
                    if alarm not in post_alarms:
                        alarm_id, entity_id = alarm.split('::::')
                        system_helper.wait_for_alarm(alarm_id=alarm_id,
                                                     entity_id=entity_id,
                                                     fail_ok=True, timeout=300,
                                                     check_interval=15,
                                                     auth_info=auth_info)

    return rtn


def wait_for_swact_complete(before_host, con_ssh=None,
                            swact_start_timeout=HostTimeout.SWACT,
                            swact_complete_timeout=HostTimeout.SWACT,
                            fail_ok=True,
                            auth_info=Tenant.get('admin_platform')):
    """
    Wait for swact to start and complete
    NOTE: This function assumes swact command was run from ssh session using
    floating ip!!

    Args:
        before_host (str): Active controller name before swact request
        con_ssh (SSHClient):
        swact_start_timeout (int): Max time to wait between cli executs and
        swact starts
        swact_complete_timeout (int): Max time to wait for swact to complete
        after swact started
        fail_ok
        auth_info

    Returns (tuple):
        (0, "Active controller is successfully swacted.")
        (3, "Swact did not start within <swact_start_timeout>")     # returns
        when fail_ok=True
        (4, "Active controller did not change after swact within
        <swact_complete_timeou>")  # returns when fail_ok=True
        (5, "400.001 alarm is not cleared within timeout after swact")
        (6, "tasks affining incomplete on <host>")

    """
    if con_ssh is None:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    fip_disconnected = con_ssh.wait_for_disconnect(fail_ok=fail_ok,
                                                   timeout=swact_start_timeout)
    if not fip_disconnected:
        return 3, "Swact did not start within {}".format(swact_start_timeout)

    LOG.info(
        "ssh to {} OAM floating IP disconnected, indicating swact "
        "initiated.".format(
            con_ssh.host))

    # permission denied is received when ssh right after swact initiated. Add
    # delay to avoid sanity failure
    time.sleep(30)
    con_ssh.connect(retry=True, retry_timeout=swact_complete_timeout - 30)

    # Give it sometime before openstack cmds enables on after host
    _wait_for_openstack_cli_enable(con_ssh=con_ssh, fail_ok=False,
                                   timeout=swact_complete_timeout,
                                   auth_info=auth_info)

    after_host = system_helper.get_active_controller_name(con_ssh=con_ssh,
                                                          auth_info=auth_info)
    LOG.info(
        "Host before swacting: {}, host after swacting: {}".format(before_host,
                                                                   after_host))

    if before_host == after_host:
        if fail_ok:
            return 4, "Active controller did not change after swact within " \
                      "{}".format(swact_complete_timeout)
        raise exceptions.HostPostCheckFailed(
            "Swact failed. Active controller host did not change")

    drbd_res = system_helper.wait_for_alarm_gone(
        alarm_id=EventLogID.CON_DRBD_SYNC, entity_id=after_host,
        strict=False, fail_ok=fail_ok, timeout=300, con_ssh=con_ssh,
        auth_info=auth_info)
    if not drbd_res:
        return 5, "400.001 alarm is not cleared within timeout after swact"

    return 0, "Active controller is successfully swacted."


def wait_for_hypervisors_up(hosts, timeout=HostTimeout.HYPERVISOR_UP,
                            check_interval=5, fail_ok=False,
                            con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Wait for given hypervisors to be up and enabled in nova hypervisor-list
    Args:
        hosts (list|str): names of the hypervisors, such as compute-0
        timeout (int):
        check_interval (int):
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info

    Returns (tuple): res_bool(bool), hosts_not_up(list)
        (True, [])      # all hypervisors given are up and enabled
        (False, [<hosts_not_up>]    # some hosts are not up and enabled

    """
    if isinstance(hosts, str):
        hosts = [hosts]

    hypervisors = get_hypervisors(con_ssh=con_ssh, auth_info=auth_info)

    if not set(hosts) <= set(hypervisors):
        msg = "Some host(s) not in nova hypervisor-list. Host(s) given: {}. " \
              "Hypervisors: {}".format(hosts, hypervisors)
        raise exceptions.HostPreCheckFailed(msg)

    hosts_to_check = list(hosts)
    LOG.info("Waiting for {} to be up in nova hypervisor-list...".format(hosts))
    end_time = time.time() + timeout
    while time.time() < end_time:
        up_hosts = get_hypervisors(state='up', con_ssh=con_ssh,
                                   auth_info=auth_info)
        for host in hosts_to_check:
            if host in up_hosts:
                hosts_to_check.remove(host)

        if not hosts_to_check:
            msg = "Host(s) {} are up and enabled in nova " \
                  "hypervisor-list".format(hosts)
            LOG.info(msg)
            return True, hosts_to_check

        time.sleep(check_interval)
    else:
        msg = "Host(s) {} are not up in hypervisor-list within timeout".format(
            hosts_to_check)
        if fail_ok:
            LOG.warning(msg)
            return False, hosts_to_check
        raise exceptions.HostTimeout(msg)


def wait_for_webservice_up(hosts, timeout=HostTimeout.WEB_SERVICE_UP,
                           check_interval=5, fail_ok=False, con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    if isinstance(hosts, str):
        hosts = [hosts]

    hosts_to_check = list(hosts)
    LOG.info(
        "Waiting for {} to be active for web-service in system "
        "servicegroup-list...".format(
            hosts_to_check))
    end_time = time.time() + timeout

    while time.time() < end_time:
        # need to check for strict True because 'go-active' state is not
        # 'active' state
        active_hosts = \
            system_helper.get_servicegroups(fields='hostname',
                                            service_group_name='web-services',
                                            strict=True,
                                            con_ssh=con_ssh,
                                            auth_info=auth_info)

        for host in hosts:
            if host in active_hosts and host in hosts_to_check:
                hosts_to_check.remove(host)

        if not hosts_to_check:
            msg = "Host(s) {} are active for web-service in system " \
                  "servicegroup-list".format(hosts)
            LOG.info(msg)
            return True, hosts_to_check

        time.sleep(check_interval)
    else:
        msg = "Host(s) {} are not active for web-service in system " \
              "servicegroup-list within timeout".format(hosts_to_check)
        if fail_ok:
            LOG.warning(msg)
            return False, hosts_to_check
        raise exceptions.HostTimeout(msg)


def get_hosts_in_storage_backing(storage_backing='local_image', up_only=True,
                                 hosts=None, con_ssh=None,
                                 auth_info=Tenant.get('admin')):
    """
    Return a list of hosts that supports the given storage backing.

    System: Regular, Small footprint

    Args:
        hosts (None|list|tuple): hosts to check
        storage_backing (str): 'local_image', or 'remote'
        up_only (bool): whether to return only up hypervisors
        con_ssh (SSHClient):
        auth_info

    Returns (tuple):
        such as ('compute-0', 'compute-2', 'compute-1', 'compute-3')
        or () if no host supports this storage backing

    """
    storage_backing = storage_backing.strip().lower()
    if 'image' in storage_backing:
        storage_backing = 'local_image'
    elif 'remote' in storage_backing:
        storage_backing = 'remote'
    else:
        raise ValueError("Invalid storage backing provided. "
                         "Please use one of these: 'local_image', 'remote'")

    hosts_per_backing = get_hosts_per_storage_backing(up_only=up_only,
                                                      con_ssh=con_ssh,
                                                      auth_info=auth_info,
                                                      hosts=hosts)
    return hosts_per_backing.get(storage_backing, [])


def get_up_hypervisors(con_ssh=None, auth_info=Tenant.get('admin')):
    return get_hypervisors(state='up', con_ssh=con_ssh, auth_info=auth_info)


def get_hypervisors(state=None, field='Hypervisor Hostname',
                    auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Return a list of hypervisors names in specified state and status. If None
    is set to state and status,
    all hypervisors will be returned.

    System: Regular

    Args:
        state (str): e.g., 'up', 'down'
        con_ssh (SSHClient):
        field (str|list|tuple): target header. e.g., ID, Hypervisor hostname
        auth_info

    Returns (list): a list of hypervisor names. Return () if no match found.
        Always return () for small footprint lab. i.e., do not work with
        small footprint lab
    """
    table_ = table_parser.table(
        cli.openstack('hypervisor list', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    kwargs = {'State': state} if state else {}
    return table_parser.get_multi_values(table_, field, **kwargs)


def _get_element_tree_virsh_xmldump(instance_name, host_ssh):
    code, output = host_ssh.exec_sudo_cmd(
        cmd='virsh dumpxml {}'.format(instance_name))
    if not 0 == code:
        raise exceptions.SSHExecCommandFailed(
            "virsh dumpxml failed to execute.")

    element_tree = ElementTree.fromstring(output)
    return element_tree


def get_values_virsh_xmldump(instance_name, host_ssh, tag_paths,
                             target_type='element'):
    """

    Args:
        instance_name (str): instance_name of a vm. Such as 'instance-00000002'
        host_ssh (SSHFromSSH): ssh of the host that hosting the given instance
        tag_paths (str|list|tuple): the tag path to reach to the target
        element. such as 'memoryBacking/hugepages/page'
        target_type (str): 'element', 'dict', 'text'

    Returns (list): list of Elements, dictionaries, or strings based on the
    target_type param.

    """
    target_type = target_type.lower().strip()
    root_element = _get_element_tree_virsh_xmldump(instance_name, host_ssh)

    is_str = False
    if isinstance(tag_paths, str):
        is_str = True
        tag_paths = [tag_paths]

    values_list = []
    for tag_path_ in tag_paths:
        elements = root_element.findall(tag_path_)

        if 'dict' in target_type:
            dics = []
            for element in elements:
                dics.append(element.attrib)
            values_list.append(dics)

        elif 'text' in target_type:
            texts = []
            for element in elements:
                text_list = list(element.itertext())
                if not text_list:
                    LOG.warning(
                        "No text found under tag: {}.".format(tag_path_))
                else:
                    texts.append(text_list[0])
                    if len(text_list) > 1:
                        LOG.warning((
                                        "More than one text found under tag: "
                                        "{}, returning the first one.".
                                        format(tag_path_)))

            values_list.append(texts)

        else:
            values_list.append(elements)

    if is_str:
        return values_list[0]
    else:
        return values_list


def _get_actual_mems(host):
    headers = ('mem_avail(MiB)', 'app_hp_total_1G', 'app_hp_pending_1G')
    displayed_mems = get_host_memories(host=host, headers=headers,
                                       wait_for_update=False)

    actual_mems = {}
    for proc in displayed_mems:
        mem_avail, total_1g, pending_1g = displayed_mems[proc]
        actual_1g = total_1g if pending_1g is None else pending_1g

        args = '-2M {} {} {}'.format(mem_avail, host, proc)
        code, output = cli.system('host-memory-modify', args, fail_ok=True)
        if code == 0:
            raise exceptions.SysinvError(
                'system host-memory-modify is not rejected when 2M pages '
                'exceeds mem_avail')

        # Processor 0:No available space for 2M huge page allocation, max 2M
        # VM pages: 27464
        actual_mem = int(re.findall(r'max 2M pages: (\d+)', output)[0]) * 2
        actual_mems[proc] = (actual_mem, actual_1g)

    return actual_mems


def wait_for_memory_update(host, proc_id=None, expt_1g=None, timeout=420,
                           auth_info=Tenant.get('admin_platform')):
    """
    Wait for host memory to be updated after modifying and unlocking host.
    Args:
        host:
        proc_id (int|list|None):
        expt_1g (int|list|None):
        timeout:
        auth_info

    Returns:

    """
    proc_id_type = type(proc_id)
    if not isinstance(expt_1g, proc_id_type):
        raise ValueError("proc_id and expt_1g have to be the same type")

    pending_2m = pending_1g = -1
    headers = ['app_hp_total_1G', 'app_hp_pending_1G', 'app_hp_pending_2M']
    current_time = time.time()
    end_time = current_time + timeout
    pending_end_time = current_time + 120
    while time.time() < end_time:
        host_mems = get_host_memories(host, headers, proc_id=proc_id,
                                      wait_for_update=False,
                                      auth_info=auth_info)
        for proc in host_mems:
            current_1g, pending_1g, pending_2m = host_mems[proc]
            if not (pending_2m is None and pending_1g is None):
                break
        else:
            if time.time() > pending_end_time:
                LOG.info("Pending memories are None for at least 120 seconds")
                break
        time.sleep(15)
    else:
        err = "Pending memory after {}s. Pending 2M: {}; Pending 1G: {}".format(
            timeout, pending_2m, pending_1g)
        assert 0, err

    if expt_1g:
        if isinstance(expt_1g, int):
            expt_1g = [expt_1g]
            proc_id = [proc_id]

        for i in range(len(proc_id)):
            actual_1g = host_mems[proc_id[i]][0]
            expt = expt_1g[i]
            assert expt == actual_1g, "{} proc{} 1G pages - actual: {}, " \
                                      "expected: {}". \
                format(host, proc_id[i], actual_1g, expt_1g)


def modify_host_memory(host, proc, gib_1g=None, gib_4k_range=None,
                       actual_mems=None, fail_ok=False,
                       con_ssh=None, auth_into=Tenant.get('admin_platform')):
    """

    Args:
        host (str):
        proc (int|str)
        gib_1g (None|int): 1g page to set
        gib_4k_range (None|tuple):
            None: no requirement on 4k page
            tuple: (min_val(None|int), max_val(None|int)) make sure 4k page
            total gib fall between the range (inclusive)
        actual_mems
        con_ssh
        auth_into
        fail_ok

    Returns (tuple):

    """
    args = ''
    if not actual_mems:
        actual_mems = _get_actual_mems(host=host)
    mib_avail, page_1g = actual_mems[proc]

    if gib_1g is not None:
        page_1g = gib_1g
        args += ' -1G {}'.format(gib_1g)
    mib_avail_2m = mib_avail - page_1g * 1024

    if gib_4k_range:
        min_4k, max_4k = gib_4k_range
        if not (min_4k is None and max_4k is None):
            if min_4k is None:
                gib_4k_final = max(0, max_4k - 2)
            elif max_4k is None:
                gib_4k_final = min_4k + 2
            else:
                gib_4k_final = (min_4k + max_4k) / 2
            mib_avail_2m = mib_avail_2m - gib_4k_final * 1024

    page_2m = int(mib_avail_2m / 2)
    args += ' -2M {} {} {}'.format(page_2m, host, proc)

    code, output = cli.system('host-memory-modify', args, ssh_client=con_ssh,
                              auth_info=auth_into, fail_ok=fail_ok)
    if code > 0:
        return 1, output

    LOG.info("{} memory modified successfully".format(host))
    return 0, page_2m


def modify_host_cpu(host, cpu_function, timeout=CMDTimeout.HOST_CPU_MODIFY,
                    fail_ok=False, con_ssh=None,
                    auth_info=Tenant.get('admin_platform'), **kwargs):
    """
    Modify host cpu to given key-value pairs. i.e., system host-cpu-modify -f
    <function> -p<id> <num of cores> <host>
    Notes: This assumes given host is already locked.

    Args:
        host (str): hostname of host to be modified
        cpu_function (str): cpu function to modify. e.g., 'vSwitch', 'platform'
        timeout (int): Timeout waiting for system host-cpu-modify cli to return
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        **kwargs: processor id and number of cores pair(s). e.g., p0=1, p1=1

    Returns (tuple): (rtn_code(int), message(str))
        (0, "Host cpu function modified successfully")
        (1, <stderr>)   # cli rejected
        (2, "Number of actual log_cores for <proc_id> is different than
        number set. Actual: <num>, expect: <num>")

    """
    LOG.info(
        "Modifying host {} CPU function {} to {}".format(host, cpu_function,
                                                         kwargs))

    if not kwargs:
        raise ValueError(
            "At least one key-value pair such as p0=1 has to be provided.")

    final_args = {}
    proc_args = ''
    for proc, cores in kwargs.items():
        if cores is not None:
            final_args[proc] = cores
            cores = str(cores)
            proc_args = ' '.join([proc_args, '-' + proc.lower().strip(), cores])

    if not final_args:
        raise ValueError("cores values cannot be all None")

    if not proc_args:
        raise ValueError(
            "At least one key-value pair should have non-None value. e.g., "
            "p1=2")

    subcmd = ' '.join(
        ['host-cpu-modify', '-f', cpu_function.lower().strip(), proc_args])
    code, output = cli.system(subcmd, host, ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info, timeout=timeout)

    if code == 1:
        return 1, output

    LOG.info("Post action check for host-cpu-modify...")
    table_ = table_parser.table(output)
    threads = len(set(table_parser.get_column(table_, 'thread')))

    table_ = table_parser.filter_table(table_, assigned_function=cpu_function)

    for proc, num in final_args.items():
        num = int(num)
        proc_id = re.findall(r'\d+', proc)[0]
        expt_cores = threads * num
        actual_cores = len(
            table_parser.get_values(table_, 'log_core', processor=proc_id))
        if expt_cores != actual_cores:
            msg = "Number of actual log_cores for {} is different than " \
                  "number set. Actual: {}, expect: {}". \
                format(proc, actual_cores, expt_cores)
            if fail_ok:
                LOG.warning(msg)
                return 2, msg
            raise exceptions.HostPostCheckFailed(msg)

    msg = "Host cpu function modified successfully"
    LOG.info(msg)
    return 0, msg


def add_host_interface(host, if_name, ports_or_ifs, if_type=None, pnet=None,
                       ae_mode=None, tx_hash_policy=None,
                       vlan_id=None, mtu=None, if_class=None, network=None,
                       ipv4_mode=None, ipv6_mode=None,
                       ipv4_pool=None, ipv6_pool=None, lock_unlock=True,
                       fail_ok=False, con_ssh=None,
                       auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        if_name:
        ports_or_ifs:
        if_type:
        pnet:
        ae_mode:
        tx_hash_policy:
        vlan_id:
        mtu:
        if_class:
        network:
        ipv4_mode:
        ipv6_mode:
        ipv4_pool:
        ipv6_pool:
        lock_unlock:
        fail_ok:
        con_ssh:
        auth_info:

    Returns:

    """
    if lock_unlock:
        lock_host(host=host, con_ssh=con_ssh, swact=True, fail_ok=False)

    if isinstance(ports_or_ifs, str):
        ports_or_ifs = [ports_or_ifs]
    args = '{} {}{}{} {}'.format(host, if_name,
                                 ' ' + if_type if if_type else '',
                                 ' ' + pnet if pnet else '',
                                 ' '.join(ports_or_ifs))
    opt_args_dict = {
        '--aemode': ae_mode,
        '--txhashpolicy': tx_hash_policy,
        '--vlan_id': vlan_id,
        '--imtu': mtu,
        '--ifclass': if_class,
        '--networks': network,
        '--ipv4-mode': ipv4_mode,
        '--ipv6-mode': ipv6_mode,
        '--ipv4-pool': ipv4_pool,
        '--ipv6-pool': ipv6_pool,
    }

    opt_args = ''
    for key, val in opt_args_dict.items():
        if val is not None:
            opt_args += '{} {} '.format(key, val)

    args = '{} {}'.format(args, opt_args).strip()
    code, out = cli.system('host-if-add', args, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, out

    if lock_unlock:
        unlock_host(host, con_ssh=con_ssh)

    msg = "Interface {} successfully added to {}".format(if_name, host)
    LOG.info(msg)

    return 0, msg


def modify_host_interface(host, interface, pnet=None, ae_mode=None,
                          tx_hash_policy=None,
                          mtu=None, if_class=None, network=None, ipv4_mode=None,
                          ipv6_mode=None,
                          ipv4_pool=None, ipv6_pool=None, sriov_vif_count=None,
                          new_if_name=None,
                          lock_unlock=True, fail_ok=False, con_ssh=None,
                          auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        interface:
        pnet:
        ae_mode:
        tx_hash_policy:
        mtu:
        if_class:
        network:
        ipv4_mode:
        ipv6_mode:
        ipv4_pool:
        ipv6_pool:
        sriov_vif_count:
        new_if_name:
        lock_unlock:
        fail_ok:
        con_ssh:
        auth_info:

    Returns:

    """
    if lock_unlock:
        lock_host(host=host, con_ssh=con_ssh, swact=True, fail_ok=False)

    args = '{} {}'.format(host, interface)
    opt_args_dict = {
        '--ifname': new_if_name,
        '--aemode': ae_mode,
        '--txhashpolicy': tx_hash_policy,
        '--imtu': mtu,
        '--ifclass': if_class,
        '--networks': network,
        '--ipv4-mode': ipv4_mode,
        '--ipv6-mode': ipv6_mode,
        '--ipv4-pool': ipv4_pool,
        '--ipv6-pool': ipv6_pool,
        '--num-vfs': sriov_vif_count,
        '--providernetworks': pnet,
    }

    opt_args = ''
    for key, val in opt_args_dict.items():
        if val is not None:
            opt_args += '{} {} '.format(key, val)

    args = '{} {}'.format(args, opt_args).strip()
    code, out = cli.system('host-if-modify', args, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, out

    if lock_unlock:
        unlock_host(host, con_ssh=con_ssh)

    msg = "{} interface {} is successfully modified".format(host, interface)
    LOG.info(msg)

    return 0, msg


def compare_host_to_cpuprofile(host, profile_uuid):
    """
    Compares the cpu function assignments of a host and a cpu profile.

    Args:
        host (str): name of host
        profile_uuid (str): name or uuid of the cpu profile

    Returns (tuple): (rtn_code(int), message(str))
        (0, "The host and cpu profile have the same information")
        (2, "The function of one of the cores has not been changed correctly:
        <core number>")

    """
    if not host or not profile_uuid:
        raise ValueError("There is either no host or no cpu profile given.")

    def check_range(core_group, core_num):
        group = []
        if isinstance(core_group, str):
            group.append(core_group)
        elif isinstance(core_group, list):
            for proc in core_group:
                group.append(proc)

        for processors in group:
            parts = processors.split(' ')
            cores = parts[len(parts) - 1]
            ranges = cores.split(',')
            for range_ in ranges:
                if range_ == '':
                    continue
                range_ = range_.split('-')
                if len(range_) == 2:
                    if int(range_[0]) <= int(core_num) <= int(range_[1]):
                        return True
                elif len(range_) == 1:
                    if int(range_[0]) == int(core_num):
                        return True
        LOG.warn("Could not match {} in {}".format(core_num, core_group))
        return False

    table_ = table_parser.table(cli.system('host-cpu-list', host)[1])
    functions = table_parser.get_column(table_=table_,
                                        header='assigned_function')

    table_ = table_parser.table(cli.system('cpuprofile-show', profile_uuid)[1])

    platform_cores = table_parser.get_value_two_col_table(table_,
                                                          field='platform '
                                                                'cores')
    vswitch_cores = table_parser.get_value_two_col_table(table_,
                                                         field='vswitch cores')
    shared_cores = table_parser.get_value_two_col_table(table_,
                                                        field='shared cores')
    vm_cores = table_parser.get_value_two_col_table(table_, field='vm cores')

    msg = "The function of one of the cores has not been changed correctly: "

    for i in range(0, len(functions)):
        if functions[i] == 'Platform':
            if not check_range(platform_cores, i):
                LOG.warning(msg + str(i))
                return 2, msg + str(i)
        elif functions[i] == 'vSwitch':
            if not check_range(vswitch_cores, i):
                LOG.warning(msg + str(i))
                return 2, msg + str(i)
        elif functions[i] == 'Shared':
            if not check_range(shared_cores, i):
                LOG.warning(msg + str(i))
                return 2, msg + str(i)
        elif functions[i] == 'Applications':
            if not check_range(vm_cores, i):
                LOG.warning(msg + str(i))
                return 2, msg + str(i)

    msg = "The host and cpu profile have the same information"
    return 0, msg


def apply_host_cpu_profile(host, profile_uuid,
                           timeout=CMDTimeout.CPU_PROFILE_APPLY, fail_ok=False,
                           con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    """
    Apply the given cpu profile to the host.
    Assumes the host is already locked.

    Args:
        host (str): name of host
        profile_uuid (str): name or uuid of the cpu profile
        timeout (int): timeout to wait for cli to return
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (rtn_code(int), message(str))
        (0, "cpu profile applied successfully")
        (1, <stderr>)   # cli rejected
        (2, "The function of one of the cores has not been changed correctly:
        <core number>")
    """
    if not host or not profile_uuid:
        raise ValueError("There is either no host or no cpu profile given.")

    LOG.info("Applying cpu profile: {} to host: {}".format(profile_uuid, host))

    code, output = cli.system('host-apply-cpuprofile',
                              '{} {}'.format(host, profile_uuid),
                              ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info,
                              timeout=timeout)

    if 1 == code:
        LOG.warning(output)
        return 1, output

    LOG.info("Post action host-apply-cpuprofile")
    res, out = compare_host_to_cpuprofile(host, profile_uuid)

    if res != 0:
        LOG.warning(output)
        return res, out

    success_msg = "cpu profile applied successfully"
    LOG.info(success_msg)
    return 0, success_msg


def get_host_cpu_cores_for_function(hostname, func='vSwitch',
                                    core_type='log_core', thread=0,
                                    con_ssh=None,
                                    auth_info=Tenant.get('admin_platform'),
                                    rtn_dict_per_proc=True):
    """
    Get processor/logical cpu cores/per processor on thread 0 for given
    function for host via system host-cpu-list

    Args:
        hostname (str): hostname to pass to system host-cpu-list
        func (str|tuple|list): such as 'Platform', 'vSwitch', or 'Applications'
        core_type (str): 'phy_core' or 'log_core'
        thread (int|None): thread number. 0 or 1
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict_per_proc (bool)

    Returns (dict|list): format: {<proc_id> (int): <log_cores> (list), ...}
        e.g., {0: [1, 2], 1: [21, 22]}

    """
    table_ = get_host_cpu_list_table(hostname, con_ssh=con_ssh,
                                     auth_info=auth_info)
    procs = list(set(table_parser.get_values(table_, 'processor',
                                             thread=thread))) if \
        rtn_dict_per_proc else [
        None]
    res = {}

    convert = False
    if isinstance(func, str):
        func = [func]
        convert = True

    for proc in procs:
        funcs_cores = []
        for func_ in func:
            if func_:
                func_ = 'Applications' if func_.lower() == 'vms' else func_
            cores = table_parser.get_values(table_, core_type, processor=proc,
                                            assigned_function=func_,
                                            thread=thread)
            funcs_cores.append(sorted([int(item) for item in cores]))

        if convert:
            funcs_cores = funcs_cores[0]

        if proc is not None:
            res[int(str(proc))] = funcs_cores
        else:
            res = funcs_cores
            break

    LOG.info("{} {} {}s: {}".format(hostname, func, core_type, res))
    return res


def get_logcores_counts(host, proc_ids=(0, 1), thread='0', functions=None,
                        con_ssh=None,
                        auth_info=Tenant.get('admin_platform')):
    """
    Get number of logical cores on given processor on thread 0.

    Args:
        host:
        proc_ids:
        thread (str|list): '0' or ['0', '1']
        con_ssh:
        functions (list|str)
        auth_info

    Returns (list):

    """
    table_ = get_host_cpu_list_table(host=host, con_ssh=con_ssh,
                                     auth_info=auth_info)
    table_ = table_parser.filter_table(table_, thread=thread)

    rtns = []
    kwargs = {}
    if functions:
        kwargs = {'assigned_function': functions}

    for i in proc_ids:
        cores_on_proc = table_parser.get_values(table_, 'log_core',
                                                processor=str(i), **kwargs)
        LOG.info("Cores on proc {}: {}".format(i, cores_on_proc))
        rtns.append(len(cores_on_proc))

    return rtns


def get_host_procs(hostname, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    table_ = get_host_cpu_list_table(host=hostname, con_ssh=con_ssh,
                                     auth_info=auth_info)
    procs = table_parser.get_column(table_, 'processor')
    return sorted(list(set(procs)))


def get_expected_vswitch_port_engine_map(host_ssh):
    """
    Get expected ports and vswitch cores mapping via vshell port-list and
    vshell engine-list

    Args:
        host_ssh (SSHClient): ssh of a nova host

    Returns (dict): format: {<proc_id> (str): <log_cores> (list), ...}
        e.g., {'0': ['1', '2'], '1': ['1', '2']}

    """
    ports_tab = table_parser.table(
        host_ssh.exec_cmd("vshell port-list", fail_ok=False)[1])
    ports_tab = table_parser.filter_table(ports_tab, type='physical')

    cores_tab = table_parser.table(
        host_ssh.exec_cmd("vshell engine-list", fail_ok=False)[1])

    header = 'socket' if 'socket' in ports_tab['headers'] else 'socket-id'
    sockets_for_ports = sorted(int(item) for item in list(
        set(table_parser.get_column(ports_tab, header))))
    sockets_for_cores = sorted(int(item) for item in list(
        set(table_parser.get_column(cores_tab, 'socket-id'))))
    expt_map = {}
    if sockets_for_ports == sockets_for_cores:
        for socket in sockets_for_ports:
            soc_ports = table_parser.get_values(ports_tab, 'id',
                                                **{header: str(socket)})
            soc_cores = sorted(int(item) for item in
                               table_parser.get_values(cores_tab, 'cpuid',
                                                       **{'socket-id': str(
                                                           socket)}))
            for port in soc_ports:
                expt_map[port] = soc_cores

    else:
        all_ports = table_parser.get_column(ports_tab, 'id')
        all_cores = sorted(
            int(item) for item in table_parser.get_column(cores_tab, 'cpuid'))
        for port in all_ports:
            expt_map[port] = all_cores

    return expt_map


def get_host_instance_backing(host, con_ssh=None, auth_info=Tenant.get('admin'),
                              fail_ok=False, refresh=False):
    """
    Get instance backing for host.

    Args:
        host (str):
        con_ssh:
        auth_info (dict)
        fail_ok:
        refresh (bool): if not refresh, it will try to get the value from
        existing global var if already exist

    Returns (str): remote, local_image, or '' (if unable to get host backing
    from nova conf)

    """
    instance_backings = ProjVar.get_var('INSTANCE_BACKING')
    if not refresh and instance_backings:
        for backing, hosts in instance_backings.items():
            if host in hosts:
                return backing

    config = kube_helper.get_openstack_configs(conf_file='/etc/nova/nova.conf',
                                               configs={
                                                   'libvirt': 'images_type'},
                                               node=host,
                                               label_app='nova',
                                               label_component='compute',
                                               con_ssh=con_ssh)
    images_type = list(config.values())[0].get('libvirt', 'images_type',
                                               fallback='')
    if not images_type:
        if fail_ok:
            return ''
        raise exceptions.NovaError(
            'images_type cannot be determined from {} nova-compute pod'.format(
                host))

    host_backing = 'remote' if images_type == 'rbd' else 'local_image'
    LOG.info("{} instance backing: {}".format(host, host_backing))
    if host_backing not in instance_backings:
        instance_backings[host_backing] = []

    for backing, hosts_with_backing in instance_backings.items():
        if host_backing == backing and host not in hosts_with_backing:
            instance_backings[backing].append(host)
        elif host_backing != backing and host in hosts_with_backing:
            instance_backings[backing].remove(host)

    ProjVar.set_var(INSTANCE_BACKING=instance_backings)

    return host_backing


def assign_host_labels(host, labels, default_value='enabled', check_first=True,
                       lock=True, unlock=True, fail_ok=False,
                       con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Assign given labels to host
    Args:
        host:
        labels (dict|list): when list of label names instead dict,
        use default_value for each label
        default_value (str):
        check_first:
        lock:
        unlock:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):
        (-1, "Host already have expected labels: <labels>. Do nothing.")
        (0, <labels>(dict))
        (1, <std_err>)

    """
    if isinstance(labels, (list, tuple)):
        labels = {label: default_value for label in labels}

    if check_first:
        existing_labels = get_host_labels_info(host, con_ssh=con_ssh,
                                               auth_info=auth_info)
        for label, expt_val in labels.items():
            if expt_val != existing_labels.get(label, 'disabled'):
                LOG.debug(
                    "{} label needs to assigned to {}".format(label, host))
                break
        else:
            msg = "{} already have expected labels: {}. Do nothing.".format(
                host, labels)
            LOG.info(msg)
            return -1, msg

    if lock:
        lock_host(host, con_ssh=con_ssh, swact=True, auth_info=auth_info)

    args = '{} {}'.format(host, ' '.join(
        ['{}={}'.format(key, val) for key, val in labels.items()]))
    code, output = cli.system('host-label-assign', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    LOG.info("{} label(s) assigned: {}".format(host, labels))
    if unlock:
        unlock_host(host, con_ssh=con_ssh, auth_info=auth_info)

    post_labels = get_host_labels_info(host, con_ssh=con_ssh,
                                       auth_info=auth_info)
    for label_, expt_val in labels.items():
        if expt_val != post_labels.get(label_, 'disabled'):
            raise exceptions.SysinvError(
                'Unexpected value for {} label {}'.format(host, label_))

    LOG.info("{} label(s) removed: {}".format(host, labels))

    return 0, labels


def get_host_labels_info(host, con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Get host labels
    Args:
        host (str):
        con_ssh:
        auth_info:

    Returns (dict): key/value pairs of host labels

    """
    output = cli.system('host-label-list --nowrap', host, ssh_client=con_ssh,
                        auth_info=auth_info)[1]
    table_ = table_parser.table(output)
    label_keys = table_parser.get_column(table_, 'label key')
    label_values = table_parser.get_column(table_, 'label value')

    labels_info = {label_keys[i]: label_values[i] for i in
                   range(len(label_keys))}
    return labels_info


def remove_host_labels(host, labels, check_first=True, lock=True, unlock=True,
                       fail_ok=False, con_ssh=None,
                       auth_info=Tenant.get('admin_platform')):
    """
    Remove given labels from host
    Args:
        host:
        labels (tuple|list): labels to remove
        check_first:
        lock:
        unlock:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):
        (-1, "Host already have expected labels: <labels>. Do nothing.")
        (0, <labels>(list))
        (1, <std_err>)

    """
    if isinstance(labels, str):
        labels = [labels]

    labels_to_remove = labels
    if check_first:
        existing_labels = get_host_labels_info(host, con_ssh=con_ssh,
                                               auth_info=auth_info)
        labels_to_remove = list(set(labels) & set(existing_labels))
        if not labels_to_remove:
            msg = "{} does not have any of these labels to remove: {}. Do " \
                  "nothing.".format(host, labels)
            LOG.info(msg)
            return -1, msg

    if lock:
        lock_host(host, con_ssh=con_ssh, swact=True, auth_info=auth_info)

    args = '{} {}'.format(host, ' '.join(labels_to_remove))
    code, output = cli.system('host-label-remove', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    if unlock:
        unlock_host(host, con_ssh=con_ssh, auth_info=auth_info)

    post_labels = get_host_labels_info(host, con_ssh=con_ssh,
                                       auth_info=auth_info)
    unremoved_labels = list(set(labels) & set(post_labels))
    if unremoved_labels:
        raise exceptions.SysinvError(
            "{} labels still exist after removal: {}".format(host,
                                                             unremoved_labels))

    LOG.info("{} label(s) removed: {}".format(host, labels))

    return 0, labels


def set_host_storage_backing(host, inst_backing, lock=True, unlock=True,
                             wait_for_configured=True, check_first=True,
                             fail_ok=False,
                             auth_info=Tenant.get('admin_platform'),
                             con_ssh=None):
    """

    Args:
        host (str): host to modify lvg for
        inst_backing (str): image, or remote
        wait_for_configured (bool): Whether or not wait for host instance
        backing change via system host-lvg-show
        lock (bool): whether or not to lock host before modify
        unlock (bool): whether or not to unlock host and verify config after
            modify
        check_first
        fail_ok (bool): whether or not raise exception if host-label-assign
            fails
        auth_info (dict):
        con_ssh (SSHClient):

    Returns:

    """
    if wait_for_configured and not unlock:
        raise ValueError("'wait_for_configured=True' requires 'unlock=True'")

    label = {
        'remote-storage': 'enabled' if inst_backing == 'remote' else 'disabled'}
    code, output = assign_host_labels(host, labels=label, lock=lock,
                                      unlock=unlock, fail_ok=fail_ok,
                                      check_first=check_first,
                                      auth_info=auth_info, con_ssh=con_ssh)
    if code > 0:
        return 1, 'Failed to assign label to {}: {}'.format(host, output)

    if wait_for_configured:
        nova_auth = Tenant.get('admin', dc_region=auth_info.get(
            'region') if auth_info else None)
        res = wait_for_host_in_instance_backing(host=host,
                                                storage_backing=inst_backing,
                                                fail_ok=fail_ok,
                                                auth_info=nova_auth)
        if not res:
            err = "Host {} is not in {} lvg within timeout".format(
                host, inst_backing)
            return 2, err

    return 0, "{} storage backing is successfully set to {}".format(
        host, inst_backing)


def wait_for_host_in_instance_backing(host, storage_backing, timeout=120,
                                      check_interval=3, fail_ok=False,
                                      con_ssh=None,
                                      auth_info=Tenant.get('admin')):
    """
    Wait for host instance backing to be given value via system host-lvg-show
    Args:
        host (str):
        storage_backing: local_image or remote
        timeout:
        check_interval:
        fail_ok:
        con_ssh:
        auth_info

    Returns:

    """
    storage_backing = 'local_image' if 'image' in storage_backing else \
        storage_backing
    end_time = time.time() + timeout
    while time.time() < end_time:
        host_backing = get_host_instance_backing(host=host, con_ssh=con_ssh,
                                                 refresh=True,
                                                 auth_info=auth_info)
        if host_backing in storage_backing:
            LOG.info("{} is configured with {} backing".format(
                host, storage_backing))
            time.sleep(30)
            return True

        time.sleep(check_interval)

    err_msg = "Timed out waiting for {} to appear in {} host-aggregate".format(
        host, storage_backing)
    if fail_ok:
        LOG.warning(err_msg)
        return False
    else:
        raise exceptions.HostError(err_msg)


def __parse_total_cpus(output):
    last_line = output.splitlines()[-1]
    print(last_line)
    # Final resource view: name=controller-0 phys_ram=44518MB used_ram=0MB
    # phys_disk=141GB used_disk=1GB
    # free_disk=133GB total_vcpus=31 used_vcpus=0.0 pci_stats=[PciDevicePool(
    # count=1,numa_node=0,product_id='0522',
    # tags={class_id='030000',configured='1',dev_type='type-PCI'},
    # vendor_id='102b')]
    total = round(float(re.findall(r'used_vcpus=([\d|.]*) ', last_line)[0]), 4)
    return total


def get_vcpus_per_proc(hosts=None, thread=None, con_ssh=None,
                       auth_info=Tenant.get('admin_platform')):
    if not hosts:
        hosts = get_up_hypervisors(con_ssh=con_ssh)
    elif isinstance(hosts, str):
        hosts = [hosts]

    vcpus_per_proc = {}
    for host in hosts:
        vcpus_per_proc[host] = {}
        cpus_per_proc = get_host_cpu_cores_for_function(host,
                                                        func='Applications',
                                                        thread=thread,
                                                        auth_info=auth_info,
                                                        con_ssh=con_ssh)
        with ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
            cmd = """ps-sched.sh|grep qemu|grep " CPU" |awk '{{print $10;}}'"""
            cores = host_ssh.exec_cmd(cmd)[1]
            cores = [int(core.strip()) for core in cores.splitlines()]

        for proc, total_vcpus_per_proc in cpus_per_proc.items():
            used_cores = list(set(total_vcpus_per_proc) & set(cores))
            vcpus_per_proc[host][proc] = (used_cores, total_vcpus_per_proc)

    return vcpus_per_proc


def get_vcpus_for_computes(hosts=None, field='vcpus_used', con_ssh=None):
    """
    Get vcpus info for given computes via openstack hypervisor show
    Args:
        hosts:
        field (str): valid values: vcpus_used, vcpus, vcpus_avail
        con_ssh:

    Returns (dict): host(str),cpu_val(float with 4 digits after decimal
    point) pairs as dictionary

    """
    if hosts is None:
        hosts = get_up_hypervisors(con_ssh=con_ssh)
    elif isinstance(hosts, str):
        hosts = [hosts]

    if field == 'used_now':
        field = 'vcpus_used'

    if 'avail' not in field:
        hosts_cpus = get_hypervisor_info(hosts=hosts, field=field,
                                         con_ssh=con_ssh)
    else:
        cpus_info = get_hypervisor_info(hosts=hosts,
                                        field=('vcpus', 'vcpus_used'),
                                        con_ssh=con_ssh)
        hosts_cpus = {}
        for host in hosts:
            total_cpu, used_cpu = cpus_info[host]
            hosts_cpus[host] = float(total_cpu) - float(used_cpu)

    return hosts_cpus


def get_hypervisor_info(hosts, field='status', con_ssh=None,
                        auth_info=Tenant.get('admin')):
    """
    Get info from openstack hypervisor show for specified field
    Args:
        hosts (str|list): hostname(s)
        field (str|list|tuple): field(s) in hypervisor show table
        con_ssh:
        auth_info:

    Returns (dict): {<host>(str): val(str|list), ...}
    """
    if isinstance(hosts, str):
        hosts = [hosts]

    convert_to_str = False
    if isinstance(field, str):
        field = [field]
        convert_to_str = True

    hosts_vals = {}
    for host in hosts:
        table_ = table_parser.table(
            cli.openstack('hypervisor show --fit-width', host,
                          ssh_client=con_ssh,
                          auth_info=auth_info)[1], combine_multiline_entry=True)
        vals = []
        for field_ in field:
            val = table_parser.get_value_two_col_table(table_, field=field_,
                                                       strict=True,
                                                       merge_lines=True)
            try:
                val = eval(val)
            except (NameError, SyntaxError):
                pass
            vals.append(val)
        if convert_to_str:
            vals = vals[0]
        hosts_vals[host] = vals

    LOG.info("Hosts_info: {}".format(hosts_vals))
    return hosts_vals


def _get_host_logcores_per_thread(host, con_ssh=None,
                                  auth_info=Tenant.get('admin_platform')):
    table_ = get_host_cpu_list_table(host=host, con_ssh=con_ssh,
                                     auth_info=auth_info)
    threads = list(set(table_parser.get_column(table_, 'thread')))
    cores_per_thread = {}
    for thread in threads:
        table_thread = table_parser.filter_table(table_, strict=True,
                                                 regex=False, thread=thread)
        cores_str = table_parser.get_column(table_thread, 'log_core')
        cores_per_thread[int(thread)] = [int(core) for core in cores_str]

    return cores_per_thread


def get_thread_num_for_cores(log_cores, host, con_ssh=None):
    cores_per_thread = _get_host_logcores_per_thread(host=host, con_ssh=con_ssh)

    core_thread_dict = {}
    for thread, cores_for_thread in cores_per_thread.items():
        for core in log_cores:
            if int(core) in cores_for_thread:
                core_thread_dict[core] = thread

        if len(core_thread_dict) == len(log_cores):
            return core_thread_dict
    else:
        raise exceptions.HostError(
            "Cannot find thread num for all cores provided. Cores provided: "
            "{}. Threads found: {}".format(log_cores, core_thread_dict))


def get_logcore_siblings(host, con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Get cpu pairs for given host.
    Args:
        host (str): such as compute-1
        con_ssh (SSHClient):
        auth_info (dict)

    Returns (list): list of log_core_siblings(tuple). Output examples:
        - HT enabled: [[0, 20], [1, 21], ..., [19, 39]]
        - HT disabled: [[0], [1], ..., [19]]
    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    table_ = get_host_cpu_list_table(host=host, con_ssh=con_ssh,
                                     auth_info=auth_info)
    phy_cores = sorted(
        [int(i) for i in set(table_parser.get_column(table_, 'phy_core'))])

    sibling_pairs = []
    for phy_core in phy_cores:
        log_cores = table_parser.get_values(table_, 'log_core',
                                            **{'phy_core': str(phy_core)})
        sibling_pairs.append(log_cores)

    LOG.info("Sibling cores for {}: {}".format(host, sibling_pairs))
    return sibling_pairs


def get_vcpu_pins_for_instance_via_virsh(host_ssh, instance_name):
    vcpu_pins = get_values_virsh_xmldump(instance_name=instance_name,
                                         host_ssh=host_ssh,
                                         tag_paths='cputune/vcpupin',
                                         target_type='dict')
    return vcpu_pins


def get_hosts_per_storage_backing(up_only=True, con_ssh=None,
                                  auth_info=Tenant.get('admin'), hosts=None,
                                  refresh=False):
    """
    Get hosts for each possible storage backing
    Args:
        up_only (bool): whether to return up hypervisor only
        auth_info
        con_ssh:
        hosts (None|list|tuple): hosts to check
        refresh (bool)

    Returns (dict): {'local_image': <cow hosts list>,
                    'remote': <remote hosts list>
                    }
    """
    instance_backings = ProjVar.get_var('INSTANCE_BACKING')
    if instance_backings and not refresh and not up_only:
        return instance_backings

    if not hosts:
        host_func = get_up_hypervisors if up_only else get_hypervisors
        hosts = host_func(con_ssh=con_ssh, auth_info=auth_info)
    elif isinstance(hosts, str):
        hosts = (hosts,)

    for host in hosts:
        backing = get_host_instance_backing(host=host, con_ssh=con_ssh,
                                            fail_ok=True, refresh=refresh)
        if not backing:
            LOG.warning('{} instance backing cannot be determined'.format(host))

    post_instance_backings = ProjVar.get_var('INSTANCE_BACKING')
    LOG.info("Hosts per storage backing: {}".format(post_instance_backings))
    if not ProjVar.get_var(
            'DEFAULT_INSTANCE_BACKING') or post_instance_backings != \
            instance_backings:
        # Host backing changed. As a result,
        # if system has more than 1 instance backings across nova
        # hypervisors, nova aggregates need to be created
        # in order to restrict openstack vms onto host(s) with specific
        # instance backing
        configured_backings = [backing for backing in post_instance_backings if
                               post_instance_backings.get(backing)]
        default_local_storage = 'remote'
        if 'local_image' in configured_backings:
            default_local_storage = 'local_image'
            if len(post_instance_backings.get('remote', [])) > len(
                    post_instance_backings['local_image']):
                default_local_storage = 'remote'

        ProjVar.set_var(DEFAULT_INSTANCE_BACKING=default_local_storage)
        if len(configured_backings) > 1:
            # More than 1 instance backings across nova hosts
            # Need to configure host aggregates
            aggregates = nova_helper.get_aggregates(con_ssh=con_ssh,
                                                    auth_info=auth_info)
            for inst_backing in configured_backings:
                expt_hosts = sorted(post_instance_backings[inst_backing])
                aggregate_name = STORAGE_AGGREGATE[inst_backing]
                if aggregate_name not in aggregates:
                    nova_helper.create_aggregate(name=aggregate_name,
                                                 avail_zone='nova',
                                                 check_first=False,
                                                 con_ssh=con_ssh,
                                                 auth_info=auth_info)
                    properties = {}
                    hosts_in_aggregate = []
                else:
                    properties, hosts_in_aggregate = \
                        nova_helper.get_aggregate_values(
                            aggregate_name,
                            fields=('properties', 'hosts'),
                            con_ssh=con_ssh, auth_info=auth_info)

                property_key = FlavorSpec.STORAGE_BACKING.split(':')[-1].strip()
                if property_key not in properties:
                    nova_helper.set_aggregate(
                        aggregate_name,
                        properties={property_key: inst_backing},
                        con_ssh=con_ssh, auth_info=auth_info)

                if expt_hosts != sorted(hosts_in_aggregate):
                    hosts_to_remove = list(
                        set(hosts_in_aggregate) - set(expt_hosts))
                    hosts_to_add = list(
                        set(expt_hosts) - set(hosts_in_aggregate))
                    if hosts_to_add:
                        nova_helper.add_hosts_to_aggregate(
                            aggregate=aggregate_name, hosts=hosts_to_add,
                            check_first=False, con_ssh=con_ssh,
                            auth_info=auth_info)
                    if hosts_to_remove:
                        nova_helper.remove_hosts_from_aggregate(
                            aggregate=aggregate_name, hosts=hosts_to_remove,
                            check_first=False, con_ssh=con_ssh,
                            auth_info=auth_info)

    return {backing: hosts_ for backing, hosts_ in
            post_instance_backings.items() if set(hosts_) & set(hosts)}


def get_coredumps_and_crashreports(move=True):
    """
    Get core dumps and crash reports from every host
    Args:
        move: whether to move coredumps and crashreports to local automation dir

    Returns (dict):

    """
    LOG.info(
        "Getting existing system crash reports from /var/crash/ and coredumps "
        "from /var/lib/systemd/coredump/")
    hosts_to_check = system_helper.get_hosts(
        availability=(HostAvailState.FAILED, HostAvailState.OFFLINE),
        exclude=True)

    core_dumps_and_reports = {}
    active_con = system_helper.get_active_controller_name()
    con_ssh = ControllerClient.get_active_controller()
    con_dir = '{}/coredumps_and_crashreports/'.format(HostLinuxUser.get_home())
    con_ssh.exec_cmd('mkdir -p {}'.format(con_dir))
    scp_to_local = False
    ls_cmd = 'ls -l --time-style=+%Y-%m-%d_%H-%M-%S {} | grep --color=never ' \
             '-v total'
    core_dump_dir = '/var/lib/systemd/coredump/'
    crash_report_dir = '/var/crash/'
    for host in hosts_to_check:
        with ssh_to_host(hostname=host) as host_ssh:
            core_dumps_and_reports[host] = []

            for failure_dir in (core_dump_dir, crash_report_dir):
                failures = host_ssh.exec_cmd(ls_cmd.format(failure_dir),
                                             fail_ok=True)[1].splitlines()
                core_dumps_and_reports[host].append(failures)

            if move and failures:
                for line in failures:
                    timestamp, name = line.split(sep=' ')[-2:]
                    new_name = '_'.join((host, timestamp, name))
                    host_ssh.exec_sudo_cmd(
                        'mv {}/{} {}/{}'.format(failure_dir, name, failure_dir,
                                                new_name),
                        fail_ok=False)

                scp_to_local = True
                if host_ssh.get_hostname() != active_con:
                    host_ssh.scp_on_source(
                        source_path='{}/*'.format(failure_dir),
                        dest_user=HostLinuxUser.get_user(),
                        dest_ip=active_con, dest_path=con_dir,
                        dest_password=HostLinuxUser.get_password())
                else:
                    host_ssh.exec_sudo_cmd(
                        'cp -r {}/* {}'.format(failure_dir, con_dir),
                        fail_ok=False)
                host_ssh.exec_sudo_cmd('rm -rf {}/*'.format(failure_dir))

    if scp_to_local:
        con_ssh.exec_sudo_cmd('chmod -R 755 {}'.format(con_dir))

        log_dir = ProjVar.get_var('LOG_DIR')
        coredump_and_crashreport_dir = os.path.join(
            log_dir, 'coredumps_and_crashreports')
        os.makedirs(coredump_and_crashreport_dir, exist_ok=True)
        source_path = '{}/*'.format(con_dir)
        common.scp_from_active_controller_to_localhost(
            source_path=source_path, dest_path=coredump_and_crashreport_dir)
        con_ssh.exec_cmd('rm -rf {}/*'.format(con_dir))

    LOG.info("core dumps and crash reports per host: {}".format(
        core_dumps_and_reports))
    return core_dumps_and_reports


def modify_mtu_on_interface(host, interface, mtu_val, network_type='data',
                            lock_unlock=True, fail_ok=False, con_ssh=None):
    mtu_val = int(mtu_val)

    LOG.info("Modify MTU for IF {} of NET-TYPE {} to: {} on {}".format(
        interface, network_type, mtu_val, host))

    args = "-m {} {} {}".format(mtu_val, host, interface)

    code, output = cli.system('host-if-modify', args, ssh_client=con_ssh,
                              fail_ok=fail_ok)

    if code != 0:
        msg = "Attempt to change MTU failed on host:{} for IF:{} to " \
              "MTU:{}".format(host, interface, mtu_val)
        if fail_ok:
            return 2, msg
        raise exceptions.HostPostCheckFailed(msg)

    if lock_unlock:
        unlock_host(host)

    return code, output


def modify_mtu_on_interfaces(hosts, mtu_val, network_type, lock_unlock=True,
                             fail_ok=False, con_ssh=None):
    if not hosts:
        raise exceptions.HostError("No hostname provided.")

    mtu_val = int(mtu_val)

    if isinstance(hosts, str):
        hosts = [hosts]

    res = {}
    rtn_code = 0

    if_class = network_type
    network = ''
    if network_type in PLATFORM_NET_TYPES:
        if_class = 'platform'
        network = network_type

    for host in hosts:
        table_ = table_parser.table(
            cli.system('host-if-list', '{} --nowrap'.format(host),
                       ssh_client=con_ssh)[1])
        table_ = table_parser.filter_table(table_, **{'class': if_class})
        # exclude unmatched platform interfaces from the table.
        if 'platform' == if_class:
            platform_ifs = table_parser.get_values(table_, target_header='name',
                                                   **{'class': 'platform'})
            for pform_if in platform_ifs:
                if_nets = \
                    get_host_interface_values(host=host, interface=pform_if,
                                              fields='networks',
                                              con_ssh=con_ssh)[0]
                if_nets = [if_net.strip() for if_net in if_nets.split(sep=',')]
                if network not in if_nets:
                    table_ = table_parser.filter_table(table_, strict=True,
                                                       exclude=True,
                                                       name=pform_if)

        uses_if_names = table_parser.get_values(table_, 'name', exclude=True,
                                                **{'uses i/f': '[]'})
        non_uses_if_names = table_parser.get_values(table_, 'name',
                                                    exclude=False,
                                                    **{'uses i/f': '[]'})
        uses_if_first = False
        if uses_if_names:
            current_mtu = int(
                get_host_interface_values(host, interface=uses_if_names[0],
                                          fields=['imtu'],
                                          con_ssh=con_ssh)[0])
            if current_mtu <= mtu_val:
                uses_if_first = True

        if uses_if_first:
            if_names = uses_if_names + non_uses_if_names
        else:
            if_names = non_uses_if_names + uses_if_names

        if lock_unlock:
            lock_host(host, swact=True)

        LOG.info("Modify MTU for {} {} interfaces to: {}".format(
            host, network_type, mtu_val))

        res_for_ifs = {}
        for if_name in if_names:
            args = "-m {} {} {}".format(mtu_val, host, if_name)
            # system host-if-modify controller-1 <port_uuid>--imtu <mtu_value>
            code, output = cli.system('host-if-modify', args,
                                      ssh_client=con_ssh, fail_ok=fail_ok)
            res_for_ifs[if_name] = code, output

            if code != 0:
                rtn_code = 1

        res[host] = res_for_ifs

    if lock_unlock:
        unlock_hosts(hosts, check_hypervisor_up=True, check_webservice_up=True)

    check_failures = []
    for host in hosts:
        host_res = res[host]
        for if_name in host_res:
            mod_res = host_res[if_name]

            # Check mtu modified correctly
            if mod_res[0] == 0:
                actual_mtu = int(
                    get_host_interface_values(host, interface=if_name,
                                              fields=['imtu'],
                                              con_ssh=con_ssh)[0])
                if not actual_mtu == mtu_val:
                    check_failures.append((host, if_name, actual_mtu))

    if check_failures:
        msg = "Actual MTU value after modify is not as expected. " \
              "Expected MTU value: {}. Actual [Host, Interface, " \
              "MTU value]: {}".format(mtu_val, check_failures)
        if fail_ok:
            return 2, msg
        raise exceptions.HostPostCheckFailed(msg)

    return rtn_code, res


def get_hosts_and_pnets_with_pci_devs(pci_type='pci-sriov', up_hosts_only=True,
                                      con_ssh=None,
                                      auth_info=Tenant.get('admin')):
    """

    Args:
        pci_type (str|list|tuple): pci-sriov, pci-passthrough
        up_hosts_only:
        con_ssh:
        auth_info:

    Returns (dict): hosts and pnets with ALL specified pci devs

    """
    state = 'up' if up_hosts_only else None
    hosts = get_hypervisors(state=state, auth_info=auth_info)
    sysinv_auth = Tenant.get('admin_platform', dc_region=auth_info.get(
        'region') if auth_info else None)

    hosts_pnets_with_pci = {}
    if isinstance(pci_type, str):
        pci_type = [pci_type]

    for host_ in hosts:
        pnets_list_for_host = []
        for pci_type_ in pci_type:

            pnets_list = get_host_interfaces(host_, field='data networks',
                                             net_type=pci_type_,
                                             con_ssh=con_ssh,
                                             auth_info=sysinv_auth)
            pnets_for_type = []
            for pnets_ in pnets_list:
                pnets_for_type += pnets_

            if not pnets_for_type:
                LOG.info("{} {} interface data network not found".format(
                    host_, pci_type_))
                pnets_list_for_host = []
                break
            pnets_list_for_host.append(list(set(pnets_for_type)))

        if pnets_list_for_host:
            pnets_final = pnets_list_for_host[0]
            for pnets_ in pnets_list_for_host[1:]:
                pnets_final = list(set(pnets_final) & set(pnets_))

            if pnets_final:
                hosts_pnets_with_pci[host_] = pnets_final

    if not hosts_pnets_with_pci:
        LOG.info("No {} interface found from any of following hosts: "
                 "{}".format(pci_type, hosts))
    else:
        LOG.info("Hosts and provider networks with {} devices: {}".format(
                pci_type, hosts_pnets_with_pci))

    return hosts_pnets_with_pci


def get_sm_dump_table(controller, con_ssh=None):
    """

    Args:
        controller (str|SSHClient): controller name/ssh client to get sm-dump
        con_ssh (SSHClient): ssh client for active controller

    Returns ():
    table_ (dict): Dictionary of a table parsed by tempest.
            Example: table =
            {
                'headers': ["Field", "Value"];
                'values': [['name', 'internal-subnet0'], ['id', '36864844783']]}

    """
    if isinstance(controller, str):
        with ssh_to_host(controller, con_ssh=con_ssh) as host_ssh:
            return table_parser.sm_dump_table(
                host_ssh.exec_sudo_cmd('sm-dump', fail_ok=False)[1])

    host_ssh = controller
    return table_parser.sm_dump_table(
        host_ssh.exec_sudo_cmd('sm-dump', fail_ok=False)[1])


def get_sm_dump_items(controller, item_names=None, con_ssh=None):
    """
    get sm dump dict for specified items
    Args:
        controller (str|SSHClient): hostname or ssh client for a controller
        such as controller-0, controller-1
        item_names (list|str|None): such as 'oam-services', or ['oam-ip',
        'oam-services']
        con_ssh (SSHClient):

    Returns (dict): such as {'oam-services': {'desired-state': 'active',
    'actual-state': 'active'},
                             'oam-ip': {...}
                            }

    """
    sm_dump_tab = get_sm_dump_table(controller=controller, con_ssh=con_ssh)
    if item_names:
        if isinstance(item_names, str):
            item_names = [item_names]

        sm_dump_tab = table_parser.filter_table(sm_dump_tab, name=item_names)

    sm_dump_items = table_parser.row_dict_table(sm_dump_tab, key_header='name',
                                                unique_key=True)
    return sm_dump_items


def get_sm_dump_item_states(controller, item_name, con_ssh=None):
    """
    get desired and actual states of given item

    Args:
        controller (str|SSHClient): hostname or host_ssh for a controller
        such as controller-0, controller-1
        item_name (str): such as 'oam-services'
        con_ssh (SSHClient):

    Returns (tuple): (<desired-state>, <actual-state>) such as ('active',
    'active')

    """
    item_value_dict = \
        get_sm_dump_items(controller=controller, item_names=item_name,
                          con_ssh=con_ssh)[item_name]

    return item_value_dict['desired-state'], item_value_dict['actual-state']


def wait_for_sm_dump_desired_states(controller, item_names=None, timeout=60,
                                    strict=True, fail_ok=False, con_ssh=None):
    """
    Wait for sm_dump item(s) to reach desired state(s)

    Args:
        controller (str): controller name
        item_names (str|list|None): item(s) name(s) to wait for desired
            state(s). Wait for desired states for all items
            when set to None.
        timeout (int): max seconds to wait
        strict (bool): whether to find strict match for given item_names.
        e.g., item_names='drbd-', strict=False will
            check all items whose name contain 'drbd-'
        fail_ok (bool): whether or not to raise exception if any item did not
        reach desired state before timed out
        con_ssh (SSHClient):

    Returns (bool): True if all of given items reach desired state

    """

    LOG.info("Waiting for {} {} in sm-dump to reach desired state".format(
        controller, item_names))
    if item_names is None:
        item_names = get_sm_dump_items(controller=controller,
                                       item_names=item_names, con_ssh=con_ssh)

    elif not strict:
        table_ = get_sm_dump_table(controller=controller, con_ssh=con_ssh)
        item_names = table_parser.get_values(table_, 'name', strict=False,
                                             name=item_names)

    if isinstance(item_names, str):
        item_names = [item_names]

    items_to_check = {}
    for item in item_names:
        items_to_check[item] = {}
        items_to_check[item]['prev-state'] = items_to_check[item][
            'actual-state'] = \
            items_to_check[item]['desired-state'] = ''

    def __wait_for_desired_state(ssh_client):
        end_time = time.time() + timeout

        while time.time() < end_time:
            items_names_to_check = list(items_to_check.keys())
            items_states = get_sm_dump_items(ssh_client,
                                             item_names=items_names_to_check,
                                             con_ssh=con_ssh)

            for item_ in items_states:
                items_to_check[item_].update(**items_states[item_])

                prev_state = items_to_check[item_]['prev-state']
                desired_state = items_states[item_]['desired-state']
                actual_state = items_states[item_]['actual-state']

                if desired_state == actual_state:
                    LOG.info(
                        "{} in sm-dump has reached desired state: {}".format(
                            item_, desired_state))
                    items_to_check.pop(item_)
                    continue

                elif prev_state and actual_state != prev_state:
                    LOG.info(
                        "{} actual state changed from {} to {} while desired "
                        "state is: {}".
                        format(item_, prev_state, actual_state, desired_state))

                items_to_check[item_].update(prev_state=actual_state)

            if not items_to_check:
                return True

            time.sleep(3)

        err_msg = "Timed out waiting for sm-dump item(s) to reach desired " \
                  "state(s): {}".format(items_to_check)
        if fail_ok:
            LOG.warning(err_msg)
            return False
        else:
            raise exceptions.TimeoutException(err_msg)

    if isinstance(controller, str):
        with ssh_to_host(controller, con_ssh=con_ssh) as host_ssh:
            return __wait_for_desired_state(host_ssh)
    else:
        return __wait_for_desired_state(controller)


# This is a copy from installer_helper due to blocking issues in
# installer_helper on importing non-exist modules


@contextmanager
def ssh_to_test_server(test_srv=TestFileServer.SERVER, user=TestFileServer.USER,
                       password=TestFileServer.PASSWORD, prompt=None):
    """
    ssh to test server.
    Usage: Use with context_manager. i.e.,
        with ssh_to_build_server(bld_srv=cgts-yow3-lx) as bld_srv_ssh:
            # do something
        # ssh session will be closed automatically

    Args:
        test_srv (str): test server ip
        user (str): svc-cgcsauto if unspecified
        password (str): password for svc-cgcsauto user if unspecified
        prompt (str|None): expected prompt. such as:
        svc-cgcsauto@yow-cgts4-lx.wrs.com$

    Yields (SSHClient): ssh client for given build server and user

    """
    # Get build_server dict from bld_srv param.

    prompt = prompt if prompt else Prompt.TEST_SERVER_PROMPT_BASE.format(user)
    test_server_conn = SSHClient(test_srv, user=user, password=password,
                                 initial_prompt=prompt)
    test_server_conn.connect()

    try:
        yield test_server_conn
    finally:
        test_server_conn.close()


def get_host_co_processor_pci_list(hostname):
    host_pci_info = []
    with ssh_to_host(hostname) as host_ssh:
        LOG.info(
            "Getting the Co-processor pci list for host {}".format(hostname))
        cmd = r"lspci -nnm | grep Co-processor | grep --color=never -v -A 1 " \
              r"-E 'Device \[0000\]|Virtual'"
        rc, output = host_ssh.exec_cmd(cmd)
        if rc != 0:
            return host_pci_info

        # sample output:
        # wcp7-12:
        # 09:00.0 "Co-processor [0b40]" "Intel Corporation [8086]" "DH895XCC
        # Series QAT [0435]" "Intel Corporation [8086]" "Device [35c5]"
        # 09:01.0 "Co-processor [0b40]" "Intel Corporation [8086]" "DH895XCC
        # Series QAT Virtual Function [0443]" "Intel Corporation [8086]"
        # "Device [0000]"

        # wolfpass-13_14:
        # 3f:00.0 "Co-processor [0b40]" "Intel Corporation [8086]" "Device [
        # 37c8]" -r04 "Intel Corporation [8086]" "Device [35cf]"
        # 3f:01.0 "Co-processor [0b40]" "Intel Corporation [8086]" "Device [
        # 37c9]" -r04 "Intel Corporation [8086]" "Device [0000]"
        # --
        # da:00.0 "Co-processor [0b40]" "Intel Corporation [8086]" "Device [
        # 37c8]" -r04 "Intel Corporation [8086]" "Device [35cf]"
        # da:01.0 "Co-processor [0b40]" "Intel Corporation [8086]" "Device [
        # 37c9]" -r04 "Intel Corporation [8086]" "Device [0000]"
        dev_sets = output.split('--\n')
        for dev_set in dev_sets:
            pdev_line, vdev_line = dev_set.strip().splitlines()
            class_id, vendor_id, device_id = re.findall(r'\[([0-9a-fA-F]{4})\]',
                                                        pdev_line)[0:3]
            vf_class_id, vf_vendor_id, vf_device_id = re.findall(
                r'\[([0-9a-fA-F]{4})\]', vdev_line)[0:3]
            assert vf_class_id == class_id
            assert vf_vendor_id == vendor_id
            assert device_id != vf_device_id

            vendor_name = \
                re.findall(r'\"([^\"]+) \[{}\]'.format(vendor_id), pdev_line)[0]
            pci_alias = \
                re.findall(r'\"([^\"]+) \[{}\]'.format(device_id), pdev_line)[0]
            if pci_alias == 'Device':
                pci_alias = None
            else:
                pci_alias = 'qat-{}-vf'.format(pci_alias.lower())
            pci_address = (
                "0000:{}".format(pdev_line.split(sep=' "', maxsplit=1)[0]))
            pci_name = "pci_{}".format(
                pci_address.replace('.', '_').replace(':', '_').strip())
            # Ensure class id is at least 6 digits as displayed in nova
            # device-list and system host-device-list
            class_id = (class_id + '000000')[0:6]

            LOG.info("pci_name={} device_id={}".format(pci_name, device_id))
            pci_info = {'pci_address': pci_address,
                        'pci_name': pci_name,
                        'vendor_name': vendor_name,
                        'vendor_id': vendor_id,
                        'device_id': device_id,
                        'class_id': class_id,
                        'pci-alias': pci_alias,
                        'vf_device_id': vf_device_id,
                        }

            host_pci_info.append(pci_info)

        LOG.info("The Co-processor pci list for host {}: {}".format(
            hostname, host_pci_info))

    return host_pci_info


def get_mellanox_ports(host):
    """
    Get Mellanox data ports for given host

    Args:
        host (str): hostname

    Returns (list):

    """
    data_ports = get_host_ports_for_net_type(host, net_type='data',
                                             ports_only=True)
    mt_ports = get_host_ports(host, 'uuid', if_name=data_ports, strict=False,
                              regex=True, **{'device type': MELLANOX_DEVICE})
    LOG.info("Mellanox ports: {}".format(mt_ports))
    return mt_ports


def is_host_locked(host, con_ssh=None):
    admin_state = system_helper.get_host_values(host, 'administrative',
                                                con_ssh=con_ssh)[0]
    return admin_state.lower() == HostAdminState.LOCKED.lower()


def get_host_network_interface_dev_names(host, con_ssh=None):
    dev_names = []
    with ssh_to_host(host, con_ssh=con_ssh) as host_ssh:

        cmd = "ifconfig -a | sed 's/[ \t].*//;/^$/d;/^lo/d'"
        rc, output = host_ssh.exec_sudo_cmd(cmd)
        if rc == 0:
            output = output.splitlines()
            for dev in output:
                if dev.endswith(':'):
                    dev = dev[:-1]
                dev_names.append(dev)
            LOG.info(
                "Host {} interface device names: {}".format(host, dev_names))
        else:
            LOG.warning(
                "Failed to get interface device names for host {}".format(host))

    return dev_names


def get_host_interfaces_for_net_type(host, net_type='infra', if_type=None,
                                     exclude_iftype=False, con_ssh=None):
    """
    Get interface names for given net_type that is expected to be listed in
    ifconfig on host
    Args:
        host (str):
        net_type (str): 'infra', 'mgmt' or 'oam', (data is handled in AVS
        thus not shown in ifconfig on host)
        if_type (str|None): When None, interfaces with all eth types will return
        exclude_iftype(bool): whether or not to exclude the if type specified.
        con_ssh (SSHClient):

    Returns (dict): {
        'ethernet': [<dev1>, <dev2>, etc],
        'vlan': [<dev1.vlan1>, <dev2.vlan2>, etc],
        'ae': [(<if1_name>, [<dev1_names>]), (<if2_name>, [<dev2_names>]), ...]
        }

    """
    LOG.info("Getting expected eth names for {} network on {}".format(net_type,
                                                                      host))
    table_origin = get_host_interfaces_table(host=host, con_ssh=con_ssh)

    if if_type:
        table_ = table_parser.filter_table(table_origin, exclude=exclude_iftype,
                                           **{'type': if_type})
    else:
        table_ = copy.deepcopy(table_origin)

    network = ''
    if_class = net_type
    if net_type in PLATFORM_NET_TYPES:
        if_class = 'platform'
        network = net_type

    table_ = table_parser.filter_table(table_, **{'class': if_class})
    # exclude unmatched platform interfaces from the table.
    if 'platform' == if_class:
        platform_ifs = table_parser.get_values(table_, target_header='name',
                                               **{'class': 'platform'})
        for pform_if in platform_ifs:
            if_nets = get_host_interface_values(host=host, interface=pform_if,
                                                fields='networks')[0]
            if_nets = [if_net.strip() for if_net in if_nets.split(sep=',')]
            if network not in if_nets:
                table_ = table_parser.filter_table(table_, strict=True,
                                                   exclude=True, name=pform_if)

    interfaces = {}
    table_eth = table_parser.filter_table(table_, **{'type': 'ethernet'})
    eth_ifs = table_parser.get_values(table_eth, 'ports')
    interfaces['ethernet'] = eth_ifs
    # such as ["[u'enp134s0f1']", "[u'enp131s0f1']"]

    table_ae = table_parser.filter_table(table_, **{'type': 'ae'})
    ae_names = table_parser.get_values(table_ae, 'name')
    ae_ifs = table_parser.get_values(table_ae, 'uses i/f')

    ae_list = []
    for i in range(len(ae_names)):
        ae_list.append((ae_names[i], ae_ifs[i]))
    interfaces['ae'] = ae_list

    table_vlan = table_parser.filter_table(table_,
                                           **{'type': ['vlan', 'vxlan']})
    vlan_ifs_ = table_parser.get_values(table_vlan, 'uses i/f')
    vlan_ids = table_parser.get_values(table_vlan, 'vlan id')
    vlan_list = []
    for i in range(len(vlan_ifs_)):
        # assuming only 1 item in 'uses i/f' list
        vlan_useif = eval(vlan_ifs_[i])[0]
        vlan_useif_ports = eval(
            table_parser.get_values(table_origin, 'ports', name=vlan_useif)[0])
        if vlan_useif_ports:
            vlan_useif = vlan_useif_ports[0]
        vlan_list.append("{}.{}".format(vlan_useif, vlan_ids[i]))

    LOG.info(
        "Expected eth names for {} network on {}: {}".format(net_type, host,
                                                             interfaces))
    return interfaces


def get_host_cpu_model(host, con_ssh=None,
                       auth_info=Tenant.get('admin_platform')):
    """
    Get cpu model for a given host. e.g., Intel(R) Xeon(R) CPU E5-2680 v2 @
    2.80GHz
    Args:
        host (str): e.g., compute-0
        con_ssh (SSHClient):
        auth_info

    Returns (str):
    """
    table_ = get_host_cpu_list_table(host=host, con_ssh=con_ssh,
                                     auth_info=auth_info)
    cpu_model = table_parser.get_column(table_, 'processor_model')[0]

    LOG.info("CPU Model for {}: {}".format(host, cpu_model))
    return cpu_model


def get_max_vms_supported(host, con_ssh=None):
    max_count = 10
    cpu_model = get_host_cpu_model(host=host, con_ssh=con_ssh)
    if ProjVar.get_var('IS_VBOX'):
        max_count = MaxVmsSupported.VBOX
    elif re.search(r'Xeon.* CPU D-[\d]+', cpu_model):
        max_count = MaxVmsSupported.XEON_D

    LOG.info("Max number vms supported on {}: {}".format(host, max_count))
    return max_count


def get_hypersvisors_with_config(hosts=None, up_only=True, hyperthreaded=None,
                                 storage_backing=None, con_ssh=None):
    """
    Get hypervisors with specified configurations
    Args:
        hosts (None|list):
        up_only (bool):
        hyperthreaded
        storage_backing (None|str):
        con_ssh (SSHClient):

    Returns (list): list of hosts meeting the requirements

    """
    if up_only:
        hypervisors = get_up_hypervisors(con_ssh=con_ssh)
    else:
        hypervisors = get_hypervisors(con_ssh=con_ssh)

    if hosts:
        candidate_hosts = list(set(hypervisors) & set(hosts))
    else:
        candidate_hosts = hypervisors

    if candidate_hosts and storage_backing:
        candidate_hosts = get_hosts_in_storage_backing(
            storage_backing=storage_backing, con_ssh=con_ssh,
            hosts=candidate_hosts)

    if hyperthreaded is not None and candidate_hosts:
        ht_hosts = []
        non_ht = []
        for host in candidate_hosts:
            if is_host_hyperthreaded(host, con_ssh=con_ssh):
                ht_hosts.append(host)
            else:
                non_ht.append(host)
        candidate_hosts = ht_hosts if hyperthreaded else non_ht

    return candidate_hosts


def lock_unlock_controllers(host_recover='function', alarm_ok=False,
                            no_standby_ok=False):
    """
    lock/unlock both controller to get rid of the config out of date situations

    Args:
        host_recover (None|str): try to recover host if lock/unlock fails
        alarm_ok (bool)
        no_standby_ok (bool)

    Returns (tuple): return code and msg

    """
    active, standby = system_helper.get_active_standby_controllers()
    if standby:
        LOG.info("Locking unlocking controllers to complete action")
        from testfixtures.recover_hosts import HostsToRecover
        if host_recover:
            HostsToRecover.add(hostnames=standby, scope=host_recover)
        lock_host(standby)
        unlock_host(standby)
        if host_recover:
            HostsToRecover.remove(hostnames=standby, scope=host_recover)
        drbd_res = system_helper.wait_for_alarm_gone(
            alarm_id=EventLogID.CON_DRBD_SYNC, entity_id=standby,
            strict=False, fail_ok=alarm_ok, timeout=300, check_interval=20)
        if not drbd_res:
            return 1, "400.001 alarm is not cleared within timeout after " \
                      "unlock standby"

        lock_host(active, swact=True)
        unlock_host(active)
        drbd_res = system_helper.wait_for_alarm_gone(
            alarm_id=EventLogID.CON_DRBD_SYNC, entity_id=active,
            strict=False, fail_ok=alarm_ok, timeout=300)
        if not drbd_res:
            return 1, "400.001 alarm is not cleared within timeout after " \
                      "unlock standby"

    elif system_helper.is_aio_simplex():
        LOG.info("Simplex system - lock/unlock only controller")
        lock_host('controller-0', swact=False)
        unlock_host('controller-0')

    else:
        LOG.warning(
            "Standby controller unavailable. Unable to lock active controller.")
        if no_standby_ok:
            return 2, 'No standby available, thus unable to lock/unlock ' \
                      'controllers'
        else:
            raise exceptions.HostError(
                "Unable to lock/unlock controllers due to no standby "
                "controller")

    return 0, "Locking unlocking controller(s) completed"


def lock_unlock_hosts(hosts, force_lock=False, con_ssh=None,
                      auth_info=Tenant.get('admin_platform'),
                      recover_scope='function'):
    """
    Lock/unlock hosts simultaneously when possible.
    Args:
        hosts (str|list):
        force_lock (bool): lock without migrating vms out
        con_ssh:
        auth_info
        recover_scope (None|str):

    Returns:

    """
    if isinstance(hosts, str):
        hosts = [hosts]

    last_compute = last_storage = None
    from testfixtures.recover_hosts import HostsToRecover
    controllers, computes, storages = system_helper.get_hosts_per_personality(
        con_ssh=con_ssh, auth_info=auth_info,
        rtn_tuple=True)
    controllers = list(set(controllers) & set(hosts))
    computes_to_lock = list(set(computes) & set(hosts))
    storages = list(set(storages) & set(hosts))

    hosts_to_lock = list(computes_to_lock)
    from keywords import container_helper, vm_helper
    nova_auth = Tenant.get('admin',
                           auth_info.get('region') if auth_info else None)
    if computes and not force_lock and \
            len(computes) == len(computes_to_lock) and \
            container_helper.is_stx_openstack_deployed() and \
            vm_helper.get_vms(auth_info=nova_auth):
        # leave a compute if there are vms on system and force lock=False
        last_compute = hosts_to_lock.pop()

    active, standby = system_helper.get_active_standby_controllers(
        con_ssh=con_ssh, auth_info=auth_info)

    if standby and standby in controllers:
        hosts_to_lock.append(standby)

        if storages and 'storage-0' in storages:
            # storage-0 cannot be locked with any controller
            last_storage = 'storage-0'
            storages.remove(last_storage)
    if storages:
        hosts_to_lock += storages

    LOG.info("Lock/unlock: {}".format(hosts_to_lock))
    hosts_locked = []
    try:
        for host in hosts_to_lock:
            HostsToRecover.add(hostnames=host, scope=recover_scope)
            lock_host(host, con_ssh=con_ssh, force=force_lock,
                      auth_info=auth_info)
            hosts_locked.append(host)

    finally:
        if hosts_locked:
            unlock_hosts(hosts=hosts_locked, con_ssh=con_ssh,
                         auth_info=auth_info)
            wait_for_hosts_ready(hosts=hosts_locked, con_ssh=con_ssh,
                                 auth_info=auth_info)
            HostsToRecover.remove(hosts_locked, scope=recover_scope)

        LOG.info("Lock/unlock last compute {} and storage {} if any".format(
            last_compute, last_storage))
        hosts_locked_next = []
        try:
            for host in (last_compute, last_storage):
                if host:
                    HostsToRecover.add(host, scope=recover_scope)
                    lock_host(host=host, con_ssh=con_ssh, auth_info=auth_info)
                    hosts_locked_next.append(host)

        finally:
            if hosts_locked_next:
                unlock_hosts(hosts_locked_next, con_ssh=con_ssh,
                             auth_info=auth_info)
                wait_for_hosts_ready(hosts_locked_next, con_ssh=con_ssh,
                                     auth_info=auth_info)
                HostsToRecover.remove(hosts_locked_next, scope=recover_scope)

            if active in controllers:
                if active and system_helper.is_aio_duplex(con_ssh=con_ssh,
                                                          auth_info=auth_info):
                    system_helper.wait_for_alarm_gone(
                        alarm_id=EventLogID.CPU_USAGE_HIGH, check_interval=30,
                        timeout=300, con_ssh=con_ssh, entity_id=active,
                        auth_info=auth_info)
                LOG.info("Lock/unlock {}".format(active))
                HostsToRecover.add(active, scope=recover_scope)
                lock_host(active, swact=True, con_ssh=con_ssh, force=force_lock,
                          auth_info=auth_info)
                unlock_hosts(active, con_ssh=con_ssh, auth_info=auth_info)
                wait_for_hosts_ready(active, con_ssh=con_ssh,
                                     auth_info=auth_info)
                HostsToRecover.remove(active, scope=recover_scope)

    LOG.info("Hosts lock/unlock completed: {}".format(hosts))


def get_traffic_control_rates(dev, con_ssh=None):
    """
    Check the traffic control profile on given device name

    Returns (dict): return traffic control rates in Mbit.
        e.g., {'root': [10000, 10000], 'drbd': [8000, 10000], ... }

    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()
    output = con_ssh.exec_cmd('tc class show dev {}'.format(dev),
                              expect_timeout=10)[1]

    traffic_classes = {}
    for line in output.splitlines():
        match = re.findall(TrafficControl.RATE_PATTERN, line)
        if match:
            ratio, rate, rate_unit, ceil_rate, ceil_rate_unit = match[0]
            class_name = TrafficControl.CLASSES[ratio]
        else:
            root_match = re.findall(TrafficControl.RATE_PATTERN_ROOT, line)
            if not root_match:
                raise NotImplementedError(
                    'Unrecognized traffic class line: {}'.format(line))
            rate, rate_unit, ceil_rate, ceil_rate_unit = root_match[0]
            class_name = 'root'

        rate = int(rate)
        ceil_rate = int(ceil_rate)

        rates = []
        for rate_info in ((rate, rate_unit), (ceil_rate, ceil_rate_unit)):
            rate_, unit_ = rate_info
            rate_ = int(rate_)
            if unit_ == 'G':
                rate_ = int(rate_ * 1000)
            elif unit_ == 'K':
                rate_ = int(rate_ / 1000)

            rates.append(rate_)

        traffic_classes[class_name] = rates

    LOG.info("Traffic classes for {}: ".format(dev, traffic_classes))
    return traffic_classes


def get_nic_speed(interface, con_ssh=None):
    """
    Check the speed on given interface name
    Args:
        interface (str|list)
        con_ssh

    Returns (list): return speed

    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    if isinstance(interface, str):
        interface = [interface]

    speeds = []
    for if_ in interface:
        if_speed = con_ssh.exec_cmd('cat /sys/class/net/{}/speed'.format(if_),
                                    expect_timeout=10, fail_ok=False)[1]
        speeds.append(int(if_speed))

    return speeds


def get_host_cmdline_options(host, con_ssh=None):
    with ssh_to_host(hostname=host, con_ssh=con_ssh) as host_ssh:
        output = host_ssh.exec_cmd('cat /proc/cmdline')[1]

    return output


def get_host_memories(host, headers=('app_hp_avail_2M',), proc_id=None,
                      wait_for_update=True, con_ssh=None,
                      auth_info=Tenant.get('admin_platform'), rtn_dict=True):
    """
    Get host memory values
    Args:
        host (str): hostname
        headers (str|list|tuple):
        proc_id (int|str|None|tuple|list): such as 0, '1'
        wait_for_update (bool): wait for app_hp_pending_2M and
            app_hp_pending_1G to be None
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict

    Returns (dict|list):  {<proc>(int): <mems>(list), ... } or [<proc0_mems>(
    list), <proc1_mems>(list), ...]
        e.g., {0: [62018, 1]}

    """

    cmd = 'host-memory-list --nowrap'
    table_ = table_parser.table(
        cli.system(cmd, host, ssh_client=con_ssh, auth_info=auth_info)[1])

    if proc_id is None:
        proc_id = table_parser.get_column(table_, 'processor')
    elif isinstance(proc_id, (str, int)):
        proc_id = [int(proc_id)]

    procs = sorted([int(proc) for proc in proc_id])

    if wait_for_update:
        end_time = time.time() + 330
        while time.time() < end_time:
            pending_2m, pending_1g = table_parser.get_multi_values(
                table_, evaluate=True,
                fields=('app_hp_pending_2M', 'app_hp_pending_1G'))
            for i in range(len(pending_2m)):
                if (pending_2m[i] is not None) or (pending_1g[i] is not None):
                    break
            else:
                LOG.debug("No pending 2M or 1G mem pages")
                break

            LOG.info("Pending 2M or 1G pages, wait for mem page to update")
            time.sleep(30)
            table_ = table_parser.table(cli.system(cmd, host,
                                                   ssh_client=con_ssh,
                                                   auth_info=auth_info)[1])
        else:
            raise exceptions.SysinvError(
                "Pending 2M or 1G pages after 5 minutes")

    values_all_procs = []
    for proc in procs:
        vals = table_parser.get_multi_values(table_, headers, evaluate=True,
                                             convert_single_field=False,
                                             **{'processor': str(proc)})
        # Since proc is set, there will be only 1 row filtered out.
        vals = [val[0] for val in vals]
        values_all_procs.append(vals)

    if rtn_dict:
        values_all_procs = {procs[i]: values_all_procs[i] for i in
                            range(len(procs))}

    return values_all_procs


def get_host_used_mem_values(host, proc_id=0,
                             auth_info=Tenant.get('admin_platform'),
                             con_ssh=None):
    """
    Return number of MiB used by a specific host
    Args:
        host:
        proc_id:
        auth_info:
        con_ssh:

    Returns (int):

    """
    mem_vals = get_host_memories(
        host, ['mem_total(MiB)', 'mem_avail(MiB)', 'avs_hp_size(MiB)',
               'avs_hp_total'],
        proc_id=proc_id, con_ssh=con_ssh, auth_info=auth_info)[int(proc_id)]

    mem_total, mem_avail, avs_hp_size, avs_hp_total = [int(val) for val in
                                                       mem_vals]

    used_mem = mem_total - mem_avail - avs_hp_size * avs_hp_total

    return used_mem


def is_host_hyperthreaded(host, con_ssh=None,
                          auth_info=Tenant.get('admin_platform')):
    table_ = table_parser.table(
        cli.system('host-cpu-list', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return len(set(table_parser.get_column(table_, 'thread'))) > 1


def get_host_cpu_list_table(host, con_ssh=None,
                            auth_info=Tenant.get('admin_platform')):
    """
    Get the parsed version of the output from system host-cpu-list <host>
    Args:
        host (str): host's name
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (dict): output of system host-cpu-list <host> parsed by table_parser

    """
    output = cli.system('host-cpu-list --nowrap', host, ssh_client=con_ssh,
                        auth_info=auth_info)[1]
    table_ = table_parser.table(output)
    return table_


def get_host_ports(host, field='name', if_name=None, pci_addr=None, proc=None,
                   dev_type=None, strict=True,
                   regex=False, rtn_dict=False, con_ssh=None,
                   auth_info=Tenant.get('admin_platform'), **kwargs):
    """
    Get
    Args:
        host:
        field (str|list):
        if_name:
        pci_addr:
        proc:
        dev_type:
        strict:
        regex:
        con_ssh:
        auth_info:
        rtn_dict
        **kwargs:

    Returns (list|dict): list if header is string, dict if header is list.

    """
    table_ = table_parser.table(
        cli.system('host-port-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    args_tmp = {
        'name': if_name,
        'pci address': pci_addr,
        'processor': proc,
        'device_type': dev_type
    }

    kwargs.update({k: v for k, v in args_tmp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, rtn_dict=rtn_dict,
                                         strict=strict, regex=regex, **kwargs)


def get_host_interfaces_table(host, show_all=False, con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    """
    Get system host-if-list <host> table
    Args:
        host (str):
        show_all (bool):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (dict):

    """
    args = ''
    args += ' --a' if show_all else ''
    args += ' ' + host

    table_ = table_parser.table(
        cli.system('host-if-list --nowrap', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_


def get_host_interfaces(host, field='name', net_type=None, if_type=None,
                        uses_ifs=None, used_by_ifs=None,
                        show_all=False, strict=True, regex=False, con_ssh=None,
                        auth_info=Tenant.get('admin_platform'),
                        exclude=False, **kwargs):
    """
    Get specified interfaces info for given host via system host-if-list

    Args:
        host (str):
        field (str|tuple): header for return info
        net_type (str|list|tuple): valid values: 'oam', 'data', 'infra',
        'mgmt', 'None'(string instead of None type)
        if_type (str): possible values: 'ethernet', 'ae', 'vlan'
        uses_ifs (str):
        used_by_ifs (str):
        show_all (bool): whether or not to show unused interfaces
        exclude (bool): whether or not to exclude the interfaces filtered
        strict (bool):
        regex (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        **kwargs: extraheader=value pairs to further filter out info. such as
        attributes='MTU=1500'.

    Returns (list):

    """
    table_ = get_host_interfaces_table(host=host, show_all=show_all,
                                       con_ssh=con_ssh, auth_info=auth_info)

    if isinstance(net_type, str):
        net_type = [net_type]
    networks = if_classes = None
    if net_type is not None:
        networks = []
        if_classes = []
        for net in net_type:
            network = ''
            if_class = net
            if net in PLATFORM_NET_TYPES:
                if_class = 'platform'
                network = net
            networks.append(network)
            if_classes.append(if_class)

    args_tmp = {
        'class': if_classes,
        'type': if_type,
        'uses i/f': uses_ifs,
        'used by i/f': used_by_ifs
    }

    for key, value in args_tmp.items():
        if value is not None:
            kwargs[key] = value

    table_ = table_parser.filter_table(table_, strict=strict, regex=regex,
                                       exclude=exclude, **kwargs)

    # exclude the platform interface that does not have desired net_type
    if if_classes is not None and 'platform' in if_classes:
        platform_ifs = table_parser.get_values(table_, target_header='name',
                                               **{'class': 'platform'})
        for pform_if in platform_ifs:
            if_nets = get_host_interface_values(host=host, interface=pform_if,
                                                fields='networks',
                                                con_ssh=con_ssh)[0]
            if_nets = [if_net.strip() for if_net in if_nets.split(sep=',')]
            if not (set(if_nets) & set(networks)):
                table_ = table_parser.filter_table(table_, strict=True,
                                                   exclude=(not exclude),
                                                   name=pform_if)

    vals = table_parser.get_multi_values(table_, fields=field, evaluate=True)
    if not isinstance(field, str) and len(vals) > 1:
        vals = list(zip(*vals))

    return vals


def get_host_ports_for_net_type(host, net_type='data', ports_only=True,
                                con_ssh=None,
                                auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        net_type:
        ports_only: whether to include dev_name as well
        con_ssh:
        auth_info:

    Returns (list):

    """
    table_ = get_host_interfaces_table(host=host, con_ssh=con_ssh,
                                       auth_info=auth_info)
    table_origin = copy.deepcopy(table_)
    if net_type:
        if_class = net_type
        network = ''
        if net_type in PLATFORM_NET_TYPES:
            if_class = 'platform'
            network = net_type

        table_ = table_parser.filter_table(table_, **{'class': if_class})
        # exclude unmatched platform interfaces from the table.
        if 'platform' == if_class:
            platform_ifs = table_parser.get_values(table_, target_header='name',
                                                   **{'class': 'platform'})
            for pform_if in platform_ifs:
                if_nets = \
                    get_host_interface_values(host=host, interface=pform_if,
                                              fields='networks',
                                              con_ssh=con_ssh)[0]
                if_nets = [if_net.strip() for if_net in if_nets.split(sep=',')]
                if network not in if_nets:
                    table_ = table_parser.filter_table(table_, strict=True,
                                                       exclude=True,
                                                       name=pform_if)

    net_ifs_names = table_parser.get_column(table_, 'name')
    total_ports = []
    for if_name in net_ifs_names:
        if_type = table_parser.get_values(table_, 'type', name=if_name)[0]
        if if_type == 'ethernet':
            ports = ast.literal_eval(
                table_parser.get_values(table_, 'ports', name=if_name)[0])
            dev_name = ports[0] if len(ports) == 1 else if_name
        else:
            dev_name = if_name
            ports = []
            uses_ifs = ast.literal_eval(
                table_parser.get_values(table_, 'uses i/f', name=if_name)[0])
            for use_if in uses_ifs:
                use_if_type = \
                    table_parser.get_values(table_origin, 'type',
                                            name=use_if)[0]
                if use_if_type == 'ethernet':
                    useif_ports = ast.literal_eval(
                        table_parser.get_values(table_origin, 'ports',
                                                name=use_if)[0])
                else:
                    # uses if is ae
                    useif_ports = ast.literal_eval(
                        table_parser.get_values(table_origin, 'uses i/f',
                                                name=use_if)[0])
                ports += useif_ports

            if if_type == 'vlan':
                vlan_id = \
                    table_parser.get_values(table_, 'vlan id', name=if_name)[0]
                if ports:
                    dev_name = ports[0] if len(ports) == 1 else uses_ifs[0]
                dev_name = '{}.{}'.format(dev_name, vlan_id)

        if ports_only:
            total_ports += ports
        else:
            total_ports.append((dev_name, sorted(ports)))

    LOG.info("{} {} network ports are: {}".format(host, net_type, total_ports))
    if ports_only:
        total_ports = list(set(total_ports))

    return total_ports


def get_host_port_pci_address(host, interface, con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        interface:
        con_ssh:
        auth_info:

    Returns (str): pci address of interface

    """
    table_ = table_parser.table(
        cli.system('host-port-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    pci_addresses = table_parser.get_values(table_, 'pci address',
                                            name=interface)

    pci_address = pci_addresses.pop()
    LOG.info("pci address of interface {} for host is: {}".format(interface,
                                                                  pci_address))

    return pci_address


def get_host_port_pci_address_for_net_type(host, net_type='mgmt', rtn_list=True,
                                           con_ssh=None,
                                           auth_info=Tenant.get(
                                               'admin_platform')):
    """

    Args:
        host:
        net_type:
        rtn_list:
        con_ssh:
        auth_info:

    Returns (list):

    """
    ports = get_host_ports_for_net_type(host, net_type=net_type,
                                        ports_only=rtn_list, con_ssh=con_ssh,
                                        auth_info=auth_info)
    pci_addresses = []
    for port in ports:
        pci_address = get_host_port_pci_address(host, port, con_ssh=con_ssh,
                                                auth_info=auth_info)
        pci_addresses.append(pci_address)

    return pci_addresses


def get_host_mgmt_pci_address(host, con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        con_ssh:
        auth_info:

    Returns:

    """
    mgmt_ip = \
        system_helper.get_host_values(host=host, fields='mgmt_ip',
                                      con_ssh=con_ssh,
                                      auth_info=auth_info)[0]
    mgmt_ports = get_host_ifnames_by_address(host, address=mgmt_ip)
    pci_addresses = []
    for port in mgmt_ports:
        pci_address = get_host_port_pci_address(host, port, con_ssh=con_ssh,
                                                auth_info=auth_info)
        pci_addresses.append(pci_address)

    return pci_addresses


def get_host_interface_values(host, interface, fields, con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    args = "{} {}".format(host, interface)
    table_ = table_parser.table(
        cli.system('host-if-show', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields)


def get_hosts_interfaces_info(hosts, fields, con_ssh=None,
                              auth_info=Tenant.get('admin_platform'),
                              strict=True,
                              **interface_filters):
    if isinstance(hosts, str):
        hosts = [hosts]

    res = {}
    for host in hosts:
        interfaces = get_host_interfaces(host, field='name', strict=strict,
                                         **interface_filters)
        host_res = {}
        for interface in interfaces:
            values = get_host_interface_values(host, interface, fields=fields,
                                               con_ssh=con_ssh,
                                               auth_info=auth_info)
            host_res[interface] = values

        res[host] = host_res

    return res


def get_host_ethernet_port_table(host, con_ssh=None,
                                 auth_info=Tenant.get('admin_platform')):
    """
    Get system host-if-list <host> table
    Args:
        host (str):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (dict):

    """
    args = ''
    args += ' ' + host

    table_ = table_parser.table(
        cli.system('host-ethernet-port-list --nowrap', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_


def get_host_ifnames_by_address(host, field='ifname', address=None, id_=None,
                                fail_ok=False, con_ssh=None,
                                auth_info=Tenant.get('admin_platform')):
    """
    Get the host ifname by address.
    Args:
        host
        con_ssh (SSHClient):
        address:
        id_:
        field:
        auth_info (dict):
        fail_ok: whether return False or raise exception when some services
            fail to reach enabled-active state

    Returns (list):

    """

    table_ = table_parser.table(
        cli.system('host-addr-list', host, ssh_client=con_ssh, fail_ok=fail_ok,
                   auth_info=auth_info)[1])
    args_dict = {
        'uuid': id_,
        'address': address,
    }
    kwargs = ({k: v for k, v in args_dict.items() if v is not None})
    ifnames = table_parser.get_multi_values(table_, field, strict=True,
                                            regex=True, merge_lines=True,
                                            **kwargs)
    return ifnames


def get_host_addresses(host, field='address', ifname=None, id_=None,
                       auth_info=Tenant.get('admin_platform'),
                       fail_ok=False, con_ssh=None):
    """
    Disable Murano Services
    Args:
        host
        con_ssh (SSHClient):
        ifname:
        id_:
        field:
        auth_info (dict):
        fail_ok: whether return False or raise exception when some services
            fail to reach enabled-active state

    Returns:

    """

    table_ = table_parser.table(
        cli.system('host-addr-list --nowrap', host, ssh_client=con_ssh,
                   fail_ok=fail_ok,
                   auth_info=auth_info)[1])
    args_dict = {
        'id': id_,
        'ifname': ifname,
    }
    kwargs = ({k: v for k, v in args_dict.items() if v is not None})
    address = table_parser.get_multi_values(table_, field, strict=True,
                                            regex=True, merge_lines=True,
                                            **kwargs)
    return address


def get_host_lldp_agents(host, field='uuid', uuid=None, local_port=None,
                         status=None, chassis_id=None,
                         port_id=None, system_name=None,
                         system_description=None,
                         auth_info=Tenant.get('admin_platform'), con_ssh=None,
                         strict=True, regex=None, **kwargs):
    """
    Get lldp agent table via system host-lldp-agent-list <host>
    Args:
        host: (mandatory)
        field: 'uuid' (default)
        uuid:
        local_port:
        status:
        chassis_id:
        port_id:
        system_name:
        system_description:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('host-lldp-agent-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    args_temp = {
        'uuid': uuid,
        'local_port': local_port,
        'status': status,
        'chassis_id': chassis_id,
        'system_name': system_name,
        'system_description': system_description,
        'port_id': port_id,
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_host_lldp_neighbors(host, field='uuid', uuid=None, local_port=None,
                            remote_port=None, chassis_id=None,
                            management_address=None, system_name=None,
                            system_description=None,
                            auth_info=Tenant.get('admin_platform'),
                            con_ssh=None, strict=True,
                            regex=None, **kwargs):
    """
    Get lldp neighbour table via system host-lldp-neighbor-list <host>
    Args:
        host (str)
        field (str|list|tuple): 'uuid' (default value)
        uuid:
        local_port:
        remote_port:
        chassis_id:
        management_address:
        system_name:
        system_description:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('host-lldp-neighbor-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'uuid': uuid,
        'local_port': local_port,
        'remote_port': remote_port,
        'chassis_id': chassis_id,
        'system_name': system_name,
        'system_description': system_description,
        'management_address': management_address
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_host_device_values(host, device, fields, con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    """
    Get host device values for given fields via system host-device-show
    Args:
        host:
        device:
        fields (str|list|tuple):
        con_ssh:
        auth_info:

    Returns (list):

    """
    args = "{} {}".format(host, device)
    table_ = table_parser.table(
        cli.system('host-device-show', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    return table_parser.get_value_two_col_table(table_, fields)


def get_host_devices(host, field='name', list_all=False, con_ssh=None,
                     auth_info=Tenant.get('admin_platform'), strict=True,
                     regex=False, **kwargs):
    """
    Get the parsed version of the output from system host-device-list <host>
    Args:
        host (str): host's name
        field (str): field name to return value for
        list_all (bool): whether to list all devices including the disabled ones
        con_ssh (SSHClient):
        auth_info (dict):
        strict (bool): whether to perform strict search on filter
        regex (bool): whether to use regular expression to search the value in
            kwargs
        kwargs: key-value pairs to filter the table

    Returns (list): output of system host-device-list <host> parsed by
        table_parser

    """
    param = '--nowrap'
    param += ' --all' if list_all else ''
    table_ = table_parser.table(
        cli.system('host-device-list {}'.format(param), host,
                   ssh_client=con_ssh, auth_info=auth_info)[1])

    values = table_parser.get_multi_values(table_, field, strict=strict,
                                           evaluate=True, regex=regex, **kwargs)

    return values


def modify_host_device(host, device, new_name=None, new_state=None,
                       check_first=True, lock_unlock=False, fail_ok=False,
                       con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Modify host device to given name or state.
    Args:
        host: host to modify
        device: device name or pci address
        new_name (str): new name to modify to
        new_state (bool): new state to modify to
        lock_unlock (bool): whether to lock unlock host before and after modify
        con_ssh (SSHClient):
        fail_ok (bool):
        check_first (bool):
        auth_info (dict):

    Returns (tuple):

    """
    args = ''
    fields = []
    expt_vals = []
    if new_name:
        fields.append('name')
        expt_vals.append(new_name)
        args += ' --name {}'.format(new_name)
    if new_state is not None:
        fields.append('enabled')
        expt_vals.append(new_state)
        args += ' --enabled {}'.format(new_state)

    if check_first and fields:
        vals = get_host_device_values(host, device, fields=fields,
                                      con_ssh=con_ssh, auth_info=auth_info)
        if vals == expt_vals:
            return -1, "{} device {} already set to given name and/or " \
                       "state".format(host, device)

    try:
        if lock_unlock:
            LOG.info("Lock host before modify host device")
            lock_host(host=host, con_ssh=con_ssh, auth_info=auth_info)

        LOG.info("Modify {} device {} with args: {}".format(host, device, args))
        args = "{} {} {}".format(host, device, args.strip())
        res, out = cli.system('host-device-modify', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)

        if res == 1:
            return 1, out

        LOG.info("Verifying the host device new pci name")
        post_vals = get_host_device_values(host, device, fields=fields,
                                           con_ssh=con_ssh, auth_info=auth_info)
        assert expt_vals == post_vals, "{} device {} is not modified to " \
                                       "given values. Expt: {}, actual: {}". \
            format(host, device, expt_vals, post_vals)

        msg = "{} device {} is successfully modified to given values".format(
            host, device)
        LOG.info(msg)
        return 0, msg
    finally:
        if lock_unlock:
            LOG.info("Unlock host after host device modify")
            unlock_host(host=host, con_ssh=con_ssh, auth_info=auth_info)


def enable_disable_hosts_devices(hosts, devices, enable=True, con_ssh=None,
                                 auth_info=Tenant.get('admin_platform')):
    """
    Enable/Disable given devices on specified hosts. (lock/unlock required
    unless devices already in state)
    Args:
        hosts (str|list|tuple): hostname(s)
        devices (str|list|tuple): device(s) name or address via
            system host-device-list
        enable (bool): whether to enable or disable devices
        con_ssh
        auth_info

    Returns:

    """
    if isinstance(hosts, str):
        hosts = [hosts]

    if isinstance(devices, str):
        devices = [devices]

    key = 'name' if 'pci_' in devices[0] else 'address'

    for host_ in hosts:
        states = get_host_devices(host=host_, field='enabled', list_all=True,
                                  con_ssh=con_ssh,
                                  auth_info=auth_info, **{key: devices})
        if (not enable) in states:
            try:
                lock_host(host=host_, swact=True, con_ssh=con_ssh,
                          auth_info=auth_info)
                for i in range(len(states)):
                    if states[i] is not enable:
                        device = devices[i]
                        modify_host_device(host=host_, device=device,
                                           new_state=enable, check_first=False,
                                           con_ssh=con_ssh, auth_info=auth_info)
            finally:
                unlock_host(host=host_, con_ssh=con_ssh, auth_info=auth_info)

        post_states = get_host_devices(host=host_, field='enabled',
                                       list_all=True, con_ssh=con_ssh,
                                       auth_info=auth_info, **{key: devices})
        assert not ((not enable) in post_states), \
            "Some devices enabled!={} after unlock".format(enable)

    LOG.info("enabled={} set successfully for following devices on hosts "
             "{}: {}".format(enable, hosts, devices))


def wait_for_tasks_affined(host, timeout=180, fail_ok=False, con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    if system_helper.is_aio_simplex(con_ssh=con_ssh, auth_info=auth_info):
        return True

    LOG.info(
        "Check {} non-existent on {}".format(PLATFORM_AFFINE_INCOMPLETE, host))
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    with ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        end_time = time.time() + timeout
        while time.time() < end_time:
            if not host_ssh.file_exists(PLATFORM_AFFINE_INCOMPLETE):
                LOG.info(
                    "{} platform tasks re-affined successfully".format(host))
                return True
            time.sleep(5)

    err = "{} did not clear on {}".format(PLATFORM_AFFINE_INCOMPLETE, host)
    if fail_ok:
        LOG.warning(err)
        return False
    raise exceptions.HostError(err)


def get_storage_backing_with_max_hosts(rtn_down_hosts=False, con_ssh=None):
    """
    Get storage backing that has the most hypervisors
    Args:
        rtn_down_hosts (bool): whether to return down hosts if no up
            hosts available
        con_ssh (SSHClient):

    Returns (tuple): (<storage_backing>(str), <hosts>(list))
        Examples:
            Regular/Storage system: ('local_image',['compute-1', 'compute-3'])
            AIO: ('local_image', ['controller-0', 'controller-1'])

    """
    hosts_per_backing = get_hosts_per_storage_backing(
        up_only=not rtn_down_hosts, con_ssh=con_ssh)
    default_backing = ProjVar.get_var('DEFAULT_INSTANCE_BACKING')
    return default_backing, hosts_per_backing.get(default_backing, [])
