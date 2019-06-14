#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import configparser
import datetime
import os.path
import re
import time
from io import StringIO

import pexpect

from consts.auth import Tenant
from consts.timeout import MTCTimeout
from keywords import system_helper, host_helper
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG

KILL_CMD = 'kill -9'
PROCESS_TYPES = ['sm', 'pmon', 'other']
KILL_PROC_EVENT_FORMAT = {
    # documented
    # 401.001	Service group <group> state change from <state> to <state> on
    # host <host_name>
    #
    # actual in 2017-02-20_22-01-22
    # clear | 400.001      | Service group cloud-services degraded;
    # cinder-api(disabled, failed) |\
    # service_domain=controller.service_group=cloud-services.host=controller-1
    # log   | 401.001      | Service group cloud-services state change from
    # active-degraded to active on host
    # set   | 400.001      | Service group cloud-services degraded;
    # cinder-api(disabled, failed) |\
    # service_domain=controller.service_group=cloud-services.host=controller-1

    # 'sm': ('401.001',
    # actual in 2017-02-20_22-01-22
    # clear	400.001	Service group cloud-services warning; nova-novnc(disabled,
    # failed)
    # service_domain=controller.service_group=cloud-services.host=controller-0

    # 'sm': ('400.001',
    #        r'Service group ([^\s]+) ([^\s]+);\s*(.*)',
    #        r'service_domain=controller\.service_group=([^\.]+)\.host=(.*)'),
    'sm': {
        'event_id': '400.001',
        'critical': (
            r'Service group ([^\s]+) ([^\s]+);\s*(.*)',
            r'service_domain=controller\.service_group=([^\.]+)\.host=(.*)'
        ),
        'major': (
            r'Service group ([^\s]+) ([^\s]+);\s*(.*)',
            r'service_domain=controller\.service_group=([^\.]+)\.host=(.*)'
        ),
        'minor': (
            r'Service group ([^\s]+) ([^\s]+);\s*(.*)',
            r'service_domain=controller\.service_group=([^\.]+)\.host=(.*)'
        ),
    },

    # set 200.006 controller-1 'acpid' process has failed.
    # Auto recovery in progress. host=controller-1.process=acpid	minor
    'pmon': {
        'event_id': '200.006',
        # controller-1 critical 'sm' process has failed and could not be
        # auto-recovered gracefully.
        # Auto- recovery progression by host reboot is required and in
        # progress. host=controller-1.process=sm
        'critical': (
            r'([^\s]+) ([^\s]+) \'([^\']+)\' process has ([^\s]+) and could '
            r'not be auto-recovered gracefully. '
            r'Auto.recovery progression by host reboot is required and in '
            r'progress.',
            r'host=([^\.]+)\.process=([^\s]+)'
        ),
        # compute-2 is degraded due to the failure of its 'fsmond' process.
        # Auto recovery of this major
        # | host=compute-2.process= | major | process is in progress.
        'major': (
            r'([^\s]+) is ([^\s]+) due to the failure of its \'([^\']+)\' '
            r'process. Auto recovery of this ([^\s]+) '
            r'process is in progress.',
            r'host=([^\.]+)\.process=([^\s]+)'
        ),
        # clear 	200.006 	compute-2 'mtclogd' process has failed. Auto
        # recovery in progress.
        # host=compute-2.process=mtclogd 	minor
        # "compute-2 'mtclogd' process has failed. Auto recovery in progress."
        # set compute-1 'ntpd' process has failed. Manual recovery is required.
        'minor': (
            r"([^\s]+) '([^\']+)' process has ([^\s]+)\. [^\s]+ recovery.*",
            r'host=([^\.]+)\.process=([^\s]+)'
        ),
    },
}
AVAILABILITY_MAPPINGS = {'active': 'enabled', 'enabled': 'active'}
PMON_PROC_CONF_DIR = '/etc/pmon.d'


def get_pmon_process_info(name, host, conf_file=None, con_ssh=None):
    """
    Get process info from its PMON config file
    Args:
        name (str):     name of the PMON process
        host (str):     host on which the PROM process running
        con_ssh:        connection to the active controller
        conf_file (str):    configuration file for the PMON process

    Returns (dict):     settings of the process

    """
    LOG.info('Get PMON process information for {}'.format(name))

    if not conf_file:
        file_name = '{}.conf'.format(name)
    else:
        file_name = conf_file

    cmd = 'cat {}'.format(os.path.join(PMON_PROC_CONF_DIR, file_name))

    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as con0_ssh:
        code, output = con0_ssh.exec_sudo_cmd(cmd)

    if 0 != code or not output.strip():
        LOG.error(
            'Failed to read config file:{}/{} for PMON process:{} on host:{}, '
            'code:{}, message:{}'.format(
                PMON_PROC_CONF_DIR, file_name, name, host, code, output))
        return {}

    conf_parser = configparser.ConfigParser()
    conf_parser.read_file(StringIO(output))

    settings = {}

    if 'process' in conf_parser.sections():
        settings = {k.strip(): v.split(';')[0].strip() for k, v in
                    conf_parser.items('process')}

    settings['interval'] = int(settings.get('interval', 5))
    settings['debounce'] = int(settings.get('debounce', 20))
    LOG.debug('process settings:{}'.format(settings))
    return settings


def get_ancestor_process(name, host, cmd='', fail_ok=False, retries=5,
                         retry_interval=3, con_ssh=None):
    """
    Get the ancestor of the processes with the given name and command-line if
    any.

    Args:
        name:       name of the process
        host:       host on which to find the process
        cmd:        executable name
        fail_ok:    do not throw exception when errors
        retries:        times to try before return
        retry_interval: wait before next re-try
        con_ssh:        ssh connection/client to the active controller

    Returns:
        pid (int),          process id, -1 if there is any error
        ppid (int),         parent process id, -1 if there is any error
        cmdline (str)       command line of the process
    """
    retries = retries if retries > 1 else 3
    retry_interval = retry_interval if retry_interval > 0 else 1

    if cmd:
        ps_cmd = r'ps -e -oppid,pid,cmd | /usr/bin/grep "{}\|{}" | ' \
                 r'/usr/bin/grep -v grep | /usr/bin/grep {}'.\
            format(name, os.path.basename(cmd), cmd)
    else:
        ps_cmd = 'ps -e -oppid,pid,cmd | /usr/bin/grep "{}" | /usr/bin/grep ' \
                 '-v grep'.format(name)

    code, output = -1, ''
    if fail_ok:
        for count in range(retries):
            with host_helper.ssh_to_host(host, con_ssh=con_ssh) as con0_ssh:
                code, output = con0_ssh.exec_cmd(ps_cmd, fail_ok=True)
                if 0 == code and output.strip():
                    break
                LOG.warn('Failed to run cli:{} on controller at retry:{:02d}, '
                         'wait:{} seconds and try again'.format(cmd, count,
                                                                retry_interval))
                time.sleep(retry_interval)
    else:
        with host_helper.ssh_to_host(host, con_ssh=con_ssh) as con0_ssh:
            code, output = con0_ssh.exec_cmd(ps_cmd, fail_ok=False)

    if not (0 == code and output.strip()):
        LOG.error(
            'Failed to find process with name:{} and cmd:{}'.format(name, cmd))
        return -1, -1, ''

    procs = []
    ppids = []
    for line in output.strip().splitlines():
        proc_attr = line.strip().split()
        if not proc_attr:
            continue
        try:
            ppid = int(proc_attr[0].strip())
            pid = int(proc_attr[1].strip())
            cmdline = ' '.join(proc_attr[2:])
            LOG.info('ppid={}, pid={}\ncmdline={}'.format(ppid, pid, cmdline))
        except IndexError:
            LOG.warn(
                'Failed to execute ps -p ?! cmd={}, line={}, output={}'.format(
                    cmd, line, output.strip()))
            continue

        if cmd and cmd not in cmdline:
            continue
        procs.append((pid, ppid, cmdline))
        ppids.append(ppid)

    if len(procs) <= 0:
        LOG.error(
            'Could not find process with name:{} and cmd:{}'.format(name, cmd))
        return -1, -1, ''

    pids = [v[1] for v in procs]

    if len(pids) == 1:
        LOG.info('porcs[0]:{}'.format(procs[0]))
        return procs[0]

    LOG.warn(
        'Multiple ({}) parent processes?, ppids:{}'.format(len(ppids), ppids))

    if '1' not in ppids:
        LOG.warn(
            'Init is not the grand parent process?, ppids:{}'.format(ppids))

    for ppid, pid, cmdline in procs:
        if pid in ppids and ppid not in pids and 1 != pid:
            LOG.info('pid={}, ppid={}, cmdline={}'.format(pid, ppid, cmdline))
            return pid, ppid, cmdline

    LOG.error(
        'Could not find process, procs:{}, ppids:{}, pids:{}'.format(procs,
                                                                     ppids,
                                                                     pids))
    return -1, -1, ''


def verify_process_with_pid_file(pid, pid_file, con_ssh=None):
    """
    Check if the given PID matching the PID in the specified pid_file

    Args:
        pid:        process id
        pid_file:   the file containing the process id
        con_ssh:    ssh connnection/client to the host on which the process
            resides

    Returns:

    """
    con_ssh = con_ssh or ControllerClient.get_active_controller()

    code, output = con_ssh.exec_sudo_cmd('cat {} | head -n1'.format(pid_file),
                                         fail_ok=False)
    LOG.info('code={}, output={}'.format(code, output))

    output = output.strip()
    if not output or int(output) != pid:
        LOG.info('Mismatched PID, expected:<{}>, from pid_file:<{}>, '
                 'pid_file={}'.format(pid, output, pid_file))
        return False
    else:
        LOG.info(
            'OK PID:{} matches with that from pid_file:{}, pid_file={}'.format(
                pid, output.strip(), pid_file))
        return True


def get_process_from_sm(name, con_ssh=None, pid_file='',
                        expecting_status='enabled-active'):
    """
    Get the information for the process from SM, including PID, Name, Current
    Status and Pid-File

    Args:
        name:               name of the process
        con_ssh:            ssh connection/client to the active-controller
        pid_file:           known pid-file path/name to compare with
        expecting_status:   expected status of the process

    Returns:
        pid (int):          process id
        proc_name (str):    process name
        actual_status (str):    actual/current status of the process
        sm_pid_file (str):      pid-file in records of SM
    """
    con_ssh = con_ssh or ControllerClient.get_active_controller()

    cmd = "true; NM={}; sudo sm-dump --impact --pid --pid_file | awk -v " \
          "pname=$NM '{{ if ($1 == pname) print }}'; " \
          "echo".format(name)

    code, output = con_ssh.exec_sudo_cmd(cmd, fail_ok=True)

    pid, proc_name, impact, sm_pid_file, actual_status = -1, '', '', '', ''

    if 0 != code or not output:
        LOG.warn(
            'Cannot find the process:{} in SM with error code:\n{}\n'
            'output:{}'.format(name, code, output))
        return pid, proc_name, impact, sm_pid_file, actual_status

    for line in output.splitlines():
        if not line.strip():
            continue
        pid, proc_name, impact, sm_pid_file, actual_status = -1, '', '', '', ''

        results_array = line.strip().split()
        LOG.info('results_array={}'.format(results_array))

        if len(results_array) != 6:
            LOG.debug(
                'Invalid format from output of sm-dump?! line={}\n'
                'cmd={}'.format(line, cmd))
            continue

        proc_name = results_array[0]
        if proc_name != name:
            continue

        expect_status = results_array[1]
        actual_status = results_array[2]

        if expect_status != actual_status:
            LOG.warn(
                'service:{} is not in expected status yet. expected:{}, '
                'actual:{}. Retry'.format(
                    proc_name, expect_status, actual_status))
            continue

        if actual_status != expecting_status:
            LOG.warn(
                'service:{} is not in expected status yet. expected:{}, '
                'actual:{}. Retry'.format(
                    proc_name, expecting_status, actual_status))
            break

        impact = results_array[3]

        pid = int(results_array[4].strip())
        if results_array[5] != sm_pid_file:
            LOG.warn(
                'pid_file not matching with that from SM-dump, pid_file={}, '
                'sm-dump-pid_file={}'.format(
                    sm_pid_file, results_array[5]))
        sm_pid_file = results_array[5]

        if pid_file and sm_pid_file != pid_file:
            LOG.warn(
                'pid_file differs from input pid_file, pid_file={}, '
                'sm-dump-pid_file={}'.format(
                    pid_file, sm_pid_file))

        if sm_pid_file:
            if not verify_process_with_pid_file(pid, sm_pid_file,
                                                con_ssh=con_ssh):
                LOG.warn(
                    'pid of service mismatch that from pid-file, pid:{}, '
                    'pid-file:{}, proc-name:{}'.format(
                        pid, sm_pid_file, proc_name))
        # found
        break

    if -1 != pid:
        host = system_helper.get_active_controller_name()
        running, msg = is_process_running(pid, host)
        if not running:
            LOG.warn(
                'Process not existing, name={}, pid={}, msg={}'.format(name,
                                                                       pid,
                                                                       msg))
            return -1, '', '', '', ''
        else:
            LOG.info(
                'OK, Process is running: name={}, pid={}, output={}'.format(
                    name, pid, msg))

    return pid, proc_name, impact, actual_status, sm_pid_file


def is_controller_swacted(
        prev_active, prev_standby,
        swact_start_timeout=MTCTimeout.KILL_PROCESS_SWACT_NOT_START,
        swact_complete_timeout=MTCTimeout.KILL_PROCESS_SWACT_COMPLETE,
        con_ssh=None):
    """
    Wait and check if the active-controller on the system was 'swacted' with
    give time period

    Args:
        prev_active:            previous active controller
        prev_standby:           previous standby controller
        swact_start_timeout:    check within this time frame if the swacting
            started
        swact_complete_timeout: check if the swacting (if any) completed in
            this time period
        con_ssh:                ssh connection/client to the current
        active-controller

    Returns:

    """
    LOG.info(
        'Check if the controllers started to swact within:{}, and completing '
        'swacting within:{}'.format(
            swact_start_timeout, swact_complete_timeout))

    code = -1
    host = prev_active
    for retry in range(1, 5):
        LOG.info(
            'retry{:02d}: checking if swacting triggered, '
            'prev-active-controller={}'.format(
                retry, prev_active))
        code = 0
        try:
            code, msg = host_helper.wait_for_swact_complete(
                host, con_ssh=con_ssh, fail_ok=True,
                swact_start_timeout=swact_start_timeout,
                swact_complete_timeout=swact_complete_timeout)

            if 0 == code:
                LOG.info(
                    'OK, host-swacted, prev-active:{}, pre-standby:{}, '
                    'code:{}, message:{}'.format(
                        prev_active, prev_active, code, msg))
                return True

            active, standby = system_helper.get_active_standby_controllers()
            if active == prev_standby and standby == prev_active:
                LOG.info(
                    'swacted?! prev-active:{} prev-standby:{}, cur active:{}, '
                    'cur standby:{}'.format(
                        prev_active, prev_standby, active, standby))
                return True
            break

        except Exception as e:
            LOG.warn(
                'erred, indicating system is in unstable state, meaning '
                'probably swacting is in process. '
                'previous active-controller:{}, previous standby-controller:{}'
                '\nerror message:{}'.format(prev_active, prev_standby, e))

            if retry >= 4:
                LOG.error(
                    'Fail the test after retry {} times, system remains in '
                    'unstable state, '
                    'meaning probably swacting is in process. previous '
                    'active-controller:{}, '
                    'previous standby-controller:{}\nerror message:{}'.
                    format(retry, prev_active, prev_standby, e))
                raise

        time.sleep(10)

    return 0 == code


def wait_for_sm_process_events(service, host, target_status, expecting=True,
                               severity='major',
                               last_events=None, process_type='sm', timeout=60,
                               interval=3, con_ssh=None):
    if process_type not in KILL_PROC_EVENT_FORMAT:
        LOG.error('unknown type of process:{}'.format(process_type))

    event_log_id = KILL_PROC_EVENT_FORMAT[process_type]['event_id']
    reason_pattern, entity_id_pattern = KILL_PROC_EVENT_FORMAT[process_type][
                                            severity][0:2]

    if last_events is not None:
        last_event = last_events['values'][0]
        start_time = \
            last_event[1].replace('-', '').replace('T', ' ').split('.')[0]
    else:
        start_time = ''

    search_keys = {
        'Event Log ID': event_log_id,
        'Reason Text': reason_pattern,
        'Entity Instance ID': entity_id_pattern,
    }

    expected_availability = target_status.get('availability', None)

    matched_events = []
    stop_time = time.time() + timeout
    if expecting and (service == 'nova-novnc' or service == 'vim-webserver'):
        stop_time = time.time() + timeout + 300
        interval = 60
    retry = 0
    while time.time() < stop_time:
        retry += 1
        matched_events[:] = []
        events_table = system_helper.get_events_table(
            event_log_id=event_log_id, show_uuid=True,
            start=start_time, limit=10, con_ssh=con_ssh, regex=True,
            **search_keys)

        if not events_table or not events_table['values']:
            LOG.warn(
                'run{:02d} for process:{}: Empty event table?!\n'
                'evens_table:{}\nevent_id={}, '
                'start={}\nkeys={}, severify={}'.
                format(retry, service, events_table, event_log_id, start_time,
                       search_keys, severity))
            continue

        for event in events_table['values']:
            try:
                actual_event_id = event[3].strip()
                if actual_event_id != event_log_id:
                    LOG.warn('Irrelevant event? event-list quering broken?!'
                             ' looking-for-event-id={}, actual-event-id={}, '
                             'event={}'.
                             format(event_log_id, actual_event_id, event))
                    continue

                actual_state = event[2]
                if actual_state not in ('set', 'clear'):
                    LOG.info(
                        'State not matching, expected-state="log", '
                        'actual-state={}", event={}'.format(
                            actual_state, event))
                    continue

                actual_reason = event[4].strip()
                # ('cloud-services', 'active', 'active-degraded',
                # 'controller-0;', ' glance-api(disabled, failed)')
                m = re.match(reason_pattern, actual_reason)
                if not m:
                    LOG.info(
                        'Not matched event:{},\nevent_id={}, start={}, '
                        'reason_text={}'.format(
                            event, event_log_id, start_time, reason_pattern))
                    continue

                actual_group_status = m.group(2)
                if actual_group_status not in ('active', expected_availability):
                    LOG.info(
                        'Group status not matching!, expected-status={}, '
                        'actual-status={}\nevent={}'.format(
                            expected_availability, actual_group_status, event))
                    continue

                if 'host={}'.format(host) not in event[5]:
                    LOG.info(
                        'Host not matching, expected-host={}, acutal-host={}, '
                        'event={}'.format(
                            host, event[5], event))
                    continue

                actual_service_name, status = m.group(3).split('(')
                service_operational, service_availability = status.split(',')
                matched_events.append(dict(
                    uuid=event[0],
                    event=event[1:-1],
                    service=actual_service_name,
                    serice_operational=service_operational,
                    service_availability=service_availability.strip().strip(
                        ')'),
                    group_name=m.group(1),
                    group_prev_status=m.group(2),
                    group_status=m.group(3)
                ))

                if not expecting:
                    LOG.error(
                        'Found set/clear event while it should NOT\nevent:'
                        '{}'.format(event))
                    return -1, tuple(matched_events)

                matched_events = list(reversed(matched_events))
                if len(matched_events) > 1:
                    if matched_events[-1]['event'][1] == 'clear' and \
                            matched_events[-2]['event'][1] == 'set':
                        LOG.info('OK, found matched events:{}'.format(
                            matched_events))
                        return 0, tuple(matched_events)

            except IndexError:
                LOG.error(
                    'CLI fm event-list changed its output format?\nsearching '
                    'keys={}'.format(
                        search_keys))
                raise

        LOG.warn(
            'No matched event found at try:{}, will sleep {} seconds and retry'
            '\nmatched events:\n{}, host={}'.format(retry, interval,
                                                    matched_events, host))

        time.sleep(interval)
        continue

    LOG.info('No matched events:\n{}'.format(matched_events))

    return -1, tuple()


def _check_status_after_killing_process(service, host, target_status,
                                        expecting=True, process_type='sm',
                                        last_events=None, con_ssh=None,
                                        auth_info=Tenant.get('admin_platform')):
    LOG.info(
        'check for process:{} on host:{} expecting status:{}, process_type:'
        '{}'.format(service, host, target_status, process_type))

    try:
        operational, availability = target_status.split('-')
    except ValueError as e:
        LOG.error('unknown host status:{}, error:{}'.format(target_status, e))
        raise

    expected = {'operational': operational, 'availability': availability}

    if availability == 'warning':
        LOG.info('impact:{} meaning: operational={}, availabiltiy={}'.format(
            target_status, operational, availability))
        code, _ = wait_for_sm_process_events(
            service,
            host,
            expected,
            expecting=expecting,
            last_events=last_events,
            process_type=process_type,
            con_ssh=con_ssh)

        return (0 == code) == expecting

    total_wait = 120 if expecting else 30
    time.sleep(1)

    found = system_helper.wait_for_host_values(host, timeout=total_wait / 2,
                                               con_ssh=con_ssh, fail_ok=True,
                                               auth_info=auth_info, **expected)

    if expecting and found:
        LOG.debug('OK, process:{} in status:{} as expected.'.format(
            service, target_status))

        LOG.debug('Next, wait and verify the sytstem recovers')
        expected = {'operational': 'enabled', 'availability': 'available'}
        return system_helper.wait_for_host_values(
            host, timeout=total_wait / 2, con_ssh=con_ssh, auth_info=auth_info,
            fail_ok=True, **expected)
        # return True

    elif not expecting and found:
        LOG.error('Unexpected status for process:{}, expected status:{}'.format(
            service, expected))
        return False

    elif not expecting and not found:
        LOG.info(
            'OK, IMPACT did not happen which is correct. '
            'target_status={}'.format(target_status))
        return True

    elif expecting and not found:
        LOG.warn(
            'host is not in expected status:{} for service:{}'.format(expected,
                                                                      service))

        code = wait_for_sm_process_events(
            service, host, expected, expecting=expecting,
            last_events=last_events,
            process_type=process_type, con_ssh=con_ssh)[0]

        return 0 == code

    else:
        # should never reach here
        pass


def check_impact(impact, service_name, host='', last_events=None,
                 expecting_impact=False, process_type='sm', con_ssh=None,
                 timeout=80, **kwargs):
    """
    Check if the expected IMPACT happens (or NOT) on the specified host

    Args:
        impact (str):   system behavior to check, including:
                            swact   ---  the active controller swacting
                            enabled-degraded    ---     the host changed to
                            'enalbed-degraded' status
                            disabled-failed     ---     the host changed to
                            'disabled-failed' status
                            ...
        service_name (str): name of the service/process
        host (str):         the host to check
        last_events (dict)  the last events before action
        expecting_impact (bool): if the IMPACT should happen timeout
        process_type (str): type of the process: sm, pm, other
        con_ssh: ssh connection/client to the active controller
        timeout
        **kwargs:

    Returns:
        boolean -   whether the IMPACT happens as expected

    """
    LOG.info(
        'Checking impact:{} on host:{} after killing process:{}, '
        'process_type={}'.format(
            impact, host, service_name, process_type))

    prev_active = kwargs.get('active_controller', 'controller-0')
    prev_standby = kwargs.get('standby_controller', 'controller-1')
    severity = kwargs.get('severity', 'major')

    if impact == 'swact':
        if expecting_impact:
            return is_controller_swacted(prev_active, prev_standby,
                                         con_ssh=con_ssh,
                                         swact_start_timeout=max(timeout / 2,
                                                                 20),
                                         swact_complete_timeout=timeout)
        else:
            return not is_controller_swacted(prev_active, prev_standby,
                                             con_ssh=con_ssh,
                                             swact_start_timeout=timeout / 4)

    elif impact in ('enabled-degraded', 'enabled-warning'):
        return _check_status_after_killing_process(
            service_name, host, target_status=impact,
            expecting=expecting_impact,
            process_type=process_type, last_events=last_events, con_ssh=con_ssh)

    elif impact == 'disabled-failed':

        if host == prev_active:
            LOG.info(
                'Killing PMON process:{} on active host:{} will trigger '
                'swact. impact:{}, '
                'severity:{}'.format(service_name, host, impact, severity))
            swacted = is_controller_swacted(prev_active, prev_standby,
                                            con_ssh=con_ssh,
                                            swact_start_timeout=20,
                                            swact_complete_timeout=timeout)
            assert swacted, 'Active-controller must be swacted before been ' \
                            'taken into disabled-failed status'

        operational, available = impact.split('-')
        expected = {'operational': operational, 'available': available}

        reached = system_helper.wait_for_host_values(host, timeout=timeout,
                                                     con_ssh=con_ssh,
                                                     fail_ok=True, **expected)
        if reached and expecting_impact:
            LOG.info(
                'host {} reached status {} as expected after killing process '
                '{}'.format(
                    host, expected, service_name))
            return True

        elif not reached and not expecting_impact:
            LOG.info(
                'host {} DID NOT reach status {} (as expected) after killing '
                'process {}'.format(
                    host, expected, service_name))
            return True

        else:
            LOG.error(
                'Host:{} did not get into status:{} in {} seconds, seaching '
                'for related events'.format(
                    host, expected, timeout))

            # todo: it's better to do this in parallel with process-monitoring
            expected = {'operational': 'enabled',
                        'available': ['available', 'degraded']}
            reached = system_helper.wait_for_host_values(host, timeout=timeout,
                                                         con_ssh=con_ssh,
                                                         fail_ok=True,
                                                         **expected)

            if reached:
                LOG.info(
                    'Host:{} did not recover into status:{} in {} '
                    'seconds'.format(
                        host, expected, timeout))
                return True

            LOG.error(
                'Host:{} did not get into status:{} in {} seconds, and there '
                'is no related events'.format(
                    host, expected, timeout))

            return False
    else:
        LOG.warn(
            'impact-checker for impact:{} not implemented yet, '
            'kwargs:{}'.format(impact, kwargs))
        return False


def get_pmon_process_id(pid_file, host, con_ssh=None):
    cmd = 'cat {} 2>/dev/null | head -n1 && echo 2>/dev/null'.format(pid_file)

    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as con:
        code, output = con.exec_cmd(cmd)

    if output.strip():
        return int(output.strip())

    return -1


def get_process_info(name, cmd='', pid_file='', host='', process_type='sm',
                     con_ssh=None,
                     auth_info=Tenant.get('admin_platform')):
    """
    Get the information of the process with the specified name

    Args:
        name (str):     name of the process
        cmd (str):      path of the executable
        pid_file (str): path of the file containing the process id
        host (str):     host on which the process resides
        process_type (str):  type of service/process, must be one of 'sm',
        'pm', 'other'
        con_ssh:        ssh connection/client to the active controller
        auth_info

    Returns:

    """
    LOG.info('name:{} cmd={} pid_file={} host={} process_type={}'.format(
        name, cmd, pid_file, host, process_type))

    active_controller = system_helper.get_active_controller_name(
        con_ssh=con_ssh, auth_info=auth_info)
    if not host:
        host = active_controller

    if process_type == 'sm':
        LOG.debug(
            'to get_process_info for SM process:{} on host:{}'.format(name,
                                                                      host))

        if host != active_controller:
            LOG.warn(
                'Already swacted? host:{} is not  the active controller now. '
                'Active controller is {}'.format(
                    host, active_controller))
        pid, name, impact, status, pid_file = get_process_from_sm(
            name, con_ssh=con_ssh, pid_file=pid_file)
        if status != 'enabled-active':
            LOG.warn('SM process is in status:{}, not "enabled-active"'.format(
                status))
            if 'disabl' in status:
                LOG.warn(
                    'Wrong controller? Or controller already swacted, '
                    'wait and try on the other controller')
                time.sleep(10)
                return get_process_from_sm(name, pid_file=pid_file)

            return -1, name, impact, status, pid_file
        else:
            return pid, name, impact, status, pid_file

    elif process_type == 'pmon':
        pid = get_pmon_process_id(pid_file, host, con_ssh=con_ssh)
        LOG.info('Found: PID={} for PMON process:{}'.format(pid, name))
        return pid, name

    else:
        LOG.info('Try to find the process:{} using "ps"'.format(name))

        pid = get_ancestor_process(name, host, cmd=cmd, con_ssh=con_ssh)[0]
        if -1 == pid:
            return -1, ''

        return pid, name


def is_process_running(pid, host, con_ssh=None, retries=3, interval=3):
    """
    Check if the process with the PID is existing

    Args:
        pid (int):      process id
        host (str):     host the process resides
        con_ssh:        ssh connection/client to the host
        retries (int):  times to re-try if no process found before return
            failure
        interval (int): time to wait before next re-try

    Returns:
        boolean     - true if the process existing, false otherwise
        msg (str)   - the details of the process or error messages
    """
    cmd = 'ps -p {}'.format(pid)
    for _ in range(retries):
        with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
            code, output = host_ssh.exec_cmd(cmd, fail_ok=True)
            if 0 != code:
                LOG.warn(
                    'Process:{} DOES NOT exist, error:{}'.format(pid, output))
            else:
                return True, output
            time.sleep(interval)

    return False, ''


def _get_last_events_timestamps(limit=1, event_log_id=None, con_ssh=None,
                                auth_info=Tenant.get('admin_platform')):
    latest_events = system_helper.get_events_table(limit=limit,
                                                   event_log_id=event_log_id,
                                                   show_uuid=True,
                                                   con_ssh=con_ssh,
                                                   auth_info=auth_info)

    return latest_events


def kill_sm_process_and_verify_impact(name, cmd='', pid_file='', retries=2,
                                      impact='swact', host='controller-0',
                                      interval=20, action_timeout=90,
                                      total_retries=3, process_type='sm',
                                      on_active_controller=True, con_ssh=None,
                                      auth_info=Tenant.get('admin_platform')):
    """
    Kill the process with the specified name and verify the system behaviors
    as expected

    Args:
        name (str):             name of the process
        cmd (str):              executable of the process
        pid_file (str):         file containing process id
        retries (int):          times of killing actions upon which the
        IMPACT will be triggered
        impact (str):           system behavior including:
                                    swact   -- active controller is swacted
                                    enabled-degraded    -- the status of the
                                    service will change to
                                    disabled-failed     -- the status of the
                                    service will change to
                                    ...
        host (str):             host to test on
        interval (int):         least time to wait between kills
        action_timeout (int):   kills and impact should happen within this
        time frame
        total_retries (int):    total number of retries for whole kill and
        wait actions
        process_type (str):     valid types are: sm, pmon, other
        on_active_controller (boolean):
        con_ssh:                ssh connection/client to the active controller
        auth_info

    Returns: (pid, host)
        pid:
            >0  suceess, the final PID of the process
            -1  fail because of impact NOT happening after killing the
            process up to threshold times
            -2  fail because of impact happening before killing threshold times
            -3  fail after try total_retries times
        host:
            the host tested on
    """
    active_controller, standby_controller = \
        system_helper.get_active_standby_controllers(con_ssh=con_ssh,
                                                     auth_info=auth_info)

    if on_active_controller:
        LOG.info(
            'on active controller: {}, host:{}'.format(active_controller, host))

        host = active_controller
        con_ssh = con_ssh or ControllerClient.get_active_controller()

    LOG.info('on host: {}'.format(host))

    if total_retries < 1 or retries < 1:
        LOG.error(
            'retries/total-retries < 1? retires:{}, total retries:{}'.format(
                retries, total_retries))
        return None
    count = 0
    for i in range(1, total_retries + 1):
        LOG.info(
            'retry:{:02d} kill the process:{} and verify impact:{}'.format(
                i, name, impact))

        exec_times = []
        killed_pids = []

        timeout = time.time() + action_timeout * (
            retries / 2 if retries > 2 else 1)

        while time.time() < timeout:
            count += 1

            LOG.debug(
                'retry{:02d}-{:02d}: Failed to get process id for {} on '
                'host:{}, swacted unexpectedly?'.format(
                    i, count, name, host))

            try:
                pid, proc_name = get_process_info(name, cmd=cmd, host=host,
                                                  process_type=process_type,
                                                  pid_file=pid_file,
                                                  con_ssh=con_ssh)[0:2]

            except pexpect.exceptions.EOF:
                LOG.warn(
                    'retry{:02d}-{:02d}: Failed to get process id for {} on '
                    'host:{}, swacted unexpectedly?'.format(
                        i, count, name, host))
                time.sleep(interval / 3.0)
                continue

            if -1 == pid:
                LOG.error(
                    'retry{:02d}-{:02d}: Failed to get PID for process with '
                    'name:{}, cmd:{}, '
                    'wait and retries'.format(i, count, name, cmd))
                time.sleep(interval / 3.0)
                continue

            if killed_pids and pid in killed_pids:
                LOG.warn(
                    'retry{:02d}-{:02d}: No new process re-created, '
                    'prev-pid={}, cur-pid={}'.format(
                        i, count, killed_pids[-1], pid))
                time.sleep(interval / 3.0)
                continue

            last_killed_pid = killed_pids[-1] if killed_pids else None
            killed_pids.append(pid)
            last_kill_time = exec_times[-1] if exec_times else None
            exec_times.append(datetime.datetime.utcnow())

            latest_events = _get_last_events_timestamps(
                event_log_id=KILL_PROC_EVENT_FORMAT[process_type]['event_id'],
                limit=10)

            LOG.info(
                'retry{:02d}-{:02d}: before kill CLI, proc_name={}, pid={}, '
                'last_killed_pid={}, last_kill_time={}'.format(
                    i, count, proc_name, pid, last_killed_pid, last_kill_time))

            LOG.info('\tactive-controller={}, standby-controller={}'.format(
                active_controller, standby_controller))

            kill_cmd = '{} {}'.format(KILL_CMD, pid)

            with host_helper.ssh_to_host(host, con_ssh=con_ssh) as con:
                code, output = con.exec_sudo_cmd(kill_cmd, fail_ok=True)
                if 0 != code:
                    # it happens occasionaly
                    LOG.error('Failed to kill pid:{}, cmd={}, output=<{}>, '
                              'at run:{}, already terminated?'.format(
                               pid, kill_cmd, output, count))

            if count < retries:
                # IMPACT should not happen yet
                if not check_impact(impact, proc_name,
                                    last_events=latest_events,
                                    active_controller=active_controller,
                                    standby_controller=standby_controller,
                                    expecting_impact=False,
                                    process_type=process_type, host=host,
                                    con_ssh=con_ssh):
                    LOG.error(
                        'Impact:{} observed unexpectedly, it should happen '
                        'only after killing {} times, '
                        'actual killed times:{}'.format(impact, retries, count))
                    return -2, host

                LOG.info(
                    'retry{:02d}-{:02d}: OK, NO impact as expected, impact={}, '
                    'will kill it another time'.format(i, count, impact))

                time.sleep(max(interval * 1 / 2.0, 5))

            else:
                no_standby_controller = standby_controller is None
                expecting_impact = True if not no_standby_controller else False
                if not check_impact(
                        impact, proc_name, last_events=latest_events,
                        active_controller=active_controller,
                        standby_controller=standby_controller,
                        expecting_impact=expecting_impact,
                        process_type=process_type, host=host, con_ssh=con_ssh):
                    LOG.error(
                        'No impact after killing process {} {} times, while '
                        '{}'.format(proc_name, count,
                                    ('expecting impact' if expecting_impact
                                     else 'not expecting impact')))

                    return -1, host

                LOG.info(
                    'OK, final retry{:02d}-{:02d}: OK, IMPACT happened '
                    '(if applicable) as expected, '
                    'impact={}'.format(i, count, impact))

                active_controller, standby_controller = \
                    system_helper.get_active_standby_controllers(
                        con_ssh=con_ssh)

                LOG.info(
                    'OK, after impact:{} (tried:{} times), '
                    'now active-controller={}, standby-controller={}'.format(
                     impact, count, active_controller, standby_controller))

                pid, proc_name = get_process_info(name, cmd=cmd, host=host,
                                                  pid_file=pid_file,
                                                  process_type=process_type,
                                                  con_ssh=con_ssh)[0:2]

                return pid, active_controller

    return -3, host


def wait_for_sm_dump_services_active(timeout=60, fail_ok=False, con_ssh=None,
                                     auth_info=Tenant.get('admin_platform')):
    """
    Wait for all services
    Args:
        timeout:
        fail_ok:
        con_ssh:
        auth_info

    Returns:

    """
    active_controller = system_helper.get_active_controller_name(
        con_ssh=con_ssh, auth_info=auth_info)
    return host_helper.wait_for_sm_dump_desired_states(
        controller=active_controller, timeout=timeout, fail_ok=fail_ok)
