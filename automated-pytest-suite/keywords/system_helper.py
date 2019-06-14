#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import ipaddress
import re
import os
import time

from pytest import skip

from consts.auth import Tenant, HostLinuxUser
from consts.stx import UUID, Prompt, SysType, EventLogID, HostAvailState
from consts.proj_vars import ProjVar
from consts.timeout import SysInvTimeout, MiscTimeout, HostTimeout
from utils import cli, table_parser, exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG
from testfixtures.fixture_resources import ResourceCleanup
from keywords import common


def get_sys_type(con_ssh=None):
    """
    Please do NOT call this function in testcase/keyword. This is used to set
    global variable SYS_TYPE in ProjVar.
    Use ProjVar.get_var('SYS_TYPE') in testcase/keyword instead.
    Args:
        con_ssh:

    Returns:

    """
    auth_info = Tenant.get('admin_platform')
    is_aio = is_aio_system(controller_ssh=con_ssh, auth_info=auth_info)
    if is_aio:
        sys_type = SysType.AIO_DX
        if len(get_controllers(con_ssh=con_ssh, auth_info=auth_info)) == 1:
            sys_type = SysType.AIO_SX
    elif get_storage_nodes(con_ssh=con_ssh):
        sys_type = SysType.STORAGE
    else:
        sys_type = SysType.REGULAR

    LOG.info("============= System type: {} ==============".format(sys_type))
    return sys_type


def is_storage_system(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    sys_type = ProjVar.get_var('SYS_TYPE')
    if sys_type:
        if not (ProjVar.get_var('IS_DC') and auth_info and
                ProjVar.get_var('PRIMARY_SUBCLOUD') != auth_info.get('region')):
            return SysType.STORAGE == sys_type
    else:
        return bool(get_storage_nodes(con_ssh=con_ssh, auth_info=auth_info))


def is_aio_duplex(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Whether it is two node CPE system
    Args:
        con_ssh:
        auth_info

    Returns (bool):

    """

    sys_type = ProjVar.get_var('SYS_TYPE')
    if sys_type:
        if not (ProjVar.get_var('IS_DC') and auth_info and
                ProjVar.get_var('PRIMARY_SUBCLOUD') != auth_info.get('region',
                                                                     None)):
            return SysType.AIO_DX == sys_type
    else:
        return is_aio_system(controller_ssh=con_ssh) \
               and len(get_controllers(con_ssh=con_ssh)) == 2


def is_aio_simplex(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    sys_type = ProjVar.get_var('SYS_TYPE')
    if sys_type:
        if not (ProjVar.get_var('IS_DC') and auth_info and
                ProjVar.get_var('PRIMARY_SUBCLOUD') != auth_info.get('region',
                                                                     None)):
            return SysType.AIO_SX == sys_type
    else:
        return is_aio_system(controller_ssh=con_ssh,
                             auth_info=auth_info) and \
               len(get_controllers(con_ssh=con_ssh,
                                   auth_info=auth_info)) == 1


def is_aio_system(controller_ssh=None, controller='controller-0',
                  auth_info=Tenant.get('admin_platform')):
    """
    Whether it is AIO-Duplex or AIO-Simplex system where controller has both
    controller and compute functions
    Args:
        controller_ssh (SSHClient):
        controller (str): controller to check
        auth_info

    Returns (bool): True if CPE or Simplex, else False

    """
    sys_type = ProjVar.get_var('SYS_TYPE')
    if sys_type:
        if not (ProjVar.get_var('IS_DC') and auth_info and
                ProjVar.get_var('PRIMARY_SUBCLOUD') != auth_info.get('region',
                                                                     None)):
            return 'aio' in sys_type.lower()

    subfunc = get_host_values(host=controller, fields='subfunctions',
                              con_ssh=controller_ssh, auth_info=auth_info)[0]
    combined = 'controller' in subfunc and re.search('compute|worker', subfunc)

    str_ = 'not ' if not combined else ''

    LOG.info("This is {}small footprint system.".format(str_))
    return combined


def get_storage_nodes(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Get hostnames with 'storage' personality from system host-list
    Args:
        con_ssh (SSHClient):
        auth_info

    Returns (list): list of hostnames. Empty list [] returns when no storage
    nodes.

    """
    return get_hosts(personality='storage', con_ssh=con_ssh,
                     auth_info=auth_info)


def get_controllers(administrative=None, operational=None, availability=None,
                    con_ssh=None,
                    auth_info=Tenant.get('admin_platform')):
    """
    Get hostnames with 'controller' personality from system host-list
    Args:
        administrative
        operational
        availability
        con_ssh (SSHClient):
        auth_info

    Returns (list): list of hostnames

    """
    return get_hosts(personality='controller', administrative=administrative,
                     operational=operational,
                     availability=availability, con_ssh=con_ssh,
                     auth_info=auth_info)


def get_computes(administrative=None, operational=None, availability=None,
                 con_ssh=None,
                 auth_info=Tenant.get('admin_platform')):
    """
    Get hostnames with 'compute' personality from system host-list
    Args:
        administrative
        operational
        availability
        con_ssh (SSHClient):
        auth_info

    Returns (list): list of hostnames. Empty list [] returns when no compute
    nodes.

    """
    return get_hosts(personality='compute', administrative=administrative,
                     operational=operational,
                     availability=availability, con_ssh=con_ssh,
                     auth_info=auth_info)


def get_hosts(personality=None, administrative=None, operational=None,
              availability=None, hostname=None, strict=True,
              exclude=False, con_ssh=None,
              auth_info=Tenant.get('admin_platform'),
              field='hostname', rtn_dict=False):
    """
    Get hostnames with given criteria
    Args:
        personality (None|str|tuple|list):
        administrative (None|str|list|tuple):
        operational (None|str|list|tuple):
        availability (None|str|list|tuple):
        hostname (None|tuple|list|str): filter out these hosts only
        strict (bool):
        exclude (bool):
        con_ssh (SSHClient|None):
        auth_info
        field (str|list|tuple)
        rtn_dict (bool): Whether to return dict where each field is a key,
        and value is a list

    Returns (list): hosts

    """
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    table_ = table_parser.table(
        cli.system('host-list', ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    table_ = table_parser.filter_table(table_, exclude=True, hostname='None')
    if hostname:
        table_ = table_parser.filter_table(table_, hostname=hostname)

    if personality:
        compute_personality = 'compute|worker'
        if personality == 'compute':
            personality = compute_personality
        elif not isinstance(personality, str):
            personality = list(personality)
            if 'compute' in personality:
                compute_index = personality.index('compute')
                personality[compute_index] = compute_personality

    filters = {'personality': personality,
               'administrative': administrative,
               'operational': operational,
               'availability': availability}
    filters = {k: v for k, v in filters.items() if v is not None}
    if filters:
        table_ = table_parser.filter_table(table_, strict=strict,
                                           exclude=exclude, regex=True,
                                           **filters)

    hostnames = table_parser.get_multi_values(table_, field, rtn_dict=rtn_dict)
    LOG.debug("Filtered hosts: {}".format(hostnames))

    return hostnames


def get_hosts_per_personality(availability=None, administrative=None,
                              operational=None, con_ssh=None,
                              auth_info=Tenant.get('admin_platform'),
                              source_rc=False,
                              rtn_tuple=False):
    """
    Args:
        availability
        administrative
        operational
        con_ssh:
        auth_info
        source_rc
        rtn_tuple (bool): whether to return tuple instead of dict. i.e.,
        <controllers>, <computes>, <storages>

    Returns (dict|tuple):
    e.g., {'controller': ['controller-0', 'controller-1'], 'compute': [
    'compute-0', 'compute-1], 'storage': []}

    """
    table_ = table_parser.table(
        cli.system('host-list', ssh_client=con_ssh, auth_info=auth_info,
                   source_openrc=source_rc)[1])
    personalities = ('controller', 'compute', 'storage')
    res = {}
    for personality in personalities:
        personality_tmp = 'compute|worker' if personality == 'compute' else \
            personality
        hosts = table_parser.get_values(table_, 'hostname',
                                        personality=personality_tmp,
                                        availability=availability,
                                        administrative=administrative,
                                        operational=operational, regex=True)
        hosts = [host for host in hosts if host.lower() != 'none']
        res[personality] = hosts

    if rtn_tuple:
        res = res['controller'], res['compute'], res['storage']

    return res


def get_active_controller_name(con_ssh=None,
                               auth_info=Tenant.get('admin_platform')):
    """
    This assumes system has 1 active controller
    Args:
        con_ssh:
        auth_info

    Returns: hostname of the active controller
        Further info such as ip, uuid can be obtained via System.CONTROLLERS[
        hostname]['uuid']
    """
    return get_active_standby_controllers(con_ssh=con_ssh, auth_info=auth_info)[
        0]


def get_standby_controller_name(con_ssh=None,
                                auth_info=Tenant.get('admin_platform')):
    """
    This assumes system has 1 standby controller
    Args:
        con_ssh:
        auth_info

    Returns (str): hostname of the active controller
        Further info such as ip, uuid can be obtained via System.CONTROLLERS[
        hostname]['uuid']
    """
    active, standby = get_active_standby_controllers(con_ssh=con_ssh,
                                                     auth_info=auth_info)
    return standby if standby else ''


def get_active_standby_controllers(con_ssh=None,
                                   auth_info=Tenant.get('admin_platform')):
    """
    Get active controller name and standby controller name (if any)
    Args:
        con_ssh (SSHClient):
        auth_info

    Returns (tuple): such as ('controller-0', 'controller-1'),
        when non-active controller is in bad state or degraded
        state, or any scenarios where standby controller does not exist,
        this function will return
        (<active_con_name>, None)

    """
    table_ = table_parser.table(
        cli.system('servicegroup-list', ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    table_ = table_parser.filter_table(table_,
                                       service_group_name='controller-services')
    active_con = table_parser.get_values(table_, 'hostname', state='active',
                                         strict=False)[0]
    standby_con = table_parser.get_values(table_, 'hostname', state='standby',
                                          strict=False)

    standby_con = standby_con[0] if standby_con else None
    return active_con, standby_con


def get_alarms_table(uuid=True, show_suppress=False, query_key=None,
                     query_value=None, query_type=None, con_ssh=None,
                     mgmt_affecting=None,
                     auth_info=Tenant.get('admin_platform'),
                     retry=0):
    """
    Get active alarms_and_events dictionary with given criteria
    Args:
        uuid (bool): whether to show uuid
        show_suppress (bool): whether to show suppressed alarms_and_events
        query_key (str): one of these: 'event_log_id', 'entity_instance_id',
            'uuid', 'severity',
        query_value (str): expected value for given key
        query_type (str): data type of value. one of these: 'string',
            'integer', 'float', 'boolean'
        mgmt_affecting (bool)
        con_ssh (SSHClient):
        auth_info (dict):
        retry (None|int): number of times to retry if the alarm-list cli got
            rejected

    Returns:
        dict: events table in format: {'headers': <headers list>, 'values':
        <list of table rows>}
    """
    args = '--nowrap'
    args = __process_query_args(args, query_key, query_value, query_type)
    if uuid:
        args += ' --uuid'
    if show_suppress:
        args += ' --include_suppress'
    if mgmt_affecting:
        args += ' --mgmt_affecting'

    fail_ok = True
    if not retry:
        fail_ok = False
        retry = 0

    output = None
    for i in range(retry + 1):
        code, output = cli.fm('alarm-list', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
        if code == 0:
            table_ = table_parser.table(output, combine_multiline_entry=True)
            return table_

        if i < retry:
            time.sleep(5)
    else:
        raise exceptions.CLIRejected(
            'fm alarm-list cli got rejected after {} retries: {}'.format(
                retry, output))


def get_alarms(fields=('Alarm ID', 'Entity ID'), alarm_id=None,
               reason_text=None, entity_id=None,
               severity=None, time_stamp=None, strict=False,
               show_suppress=False, query_key=None, query_value=None,
               query_type=None, mgmt_affecting=None, con_ssh=None,
               auth_info=Tenant.get('admin_platform'),
               combine_entries=True):
    """
    Get a list of alarms with values for specified fields.
    Args:
        fields (tuple): fields to get values for
        alarm_id (str): filter out the table using given alarm id (
        strict=True). if None, table will not be filtered.
        reason_text (str): reason text to filter out the table (strict
            defined in param)
        entity_id (str): entity instance id to filter out the table (strict
            defined in param)
        severity (str): severity such as 'critical', 'major'
        time_stamp (str):
        strict (bool): whether to perform strict filter on reason text,
            entity_id, severity, or time_stamp
        show_suppress (bool): whether to show suppressed alarms. Default to
            False.
        query_key (str): key in --query <key>=<value> passed to fm alarm-list
        query_value (str): value in --query <key>=<value> passed to fm
            alarm-list
        query_type (str): 'string', 'integer', 'float', or 'boolean'
        mgmt_affecting (bool)
        con_ssh (SSHClient):
        auth_info (dict):
        combine_entries (bool): return list of strings when set to True,
            else return a list of tuples.
            e.g., when True, returns ["800.003::::cluster=829851fa",
            "250.001::::host=controller-0"]
                  when False, returns [("800.003", "cluster=829851fa"),
                  ("250.001", "host=controller-0")]

    Returns (list): list of alarms with values of specified fields

    """

    table_ = get_alarms_table(show_suppress=show_suppress, query_key=query_key,
                              query_value=query_value,
                              query_type=query_type, con_ssh=con_ssh,
                              auth_info=auth_info,
                              mgmt_affecting=mgmt_affecting)

    if alarm_id:
        table_ = table_parser.filter_table(table_, **{'Alarm ID': alarm_id})

    kwargs_dict = {
        'Reason Text': reason_text,
        'Entity ID': entity_id,
        'Severity': severity,
        'Time Stamp': time_stamp
    }

    kwargs = {}
    for key, value in kwargs_dict.items():
        if value is not None:
            kwargs[key] = value

    if kwargs:
        table_ = table_parser.filter_table(table_, strict=strict, **kwargs)

    rtn_vals_list = []
    for field in fields:
        vals = table_parser.get_column(table_, field)
        rtn_vals_list.append(vals)

    rtn_vals_list = zip(*rtn_vals_list)
    if combine_entries:
        rtn_vals_list = ['::::'.join(vals) for vals in rtn_vals_list]
    else:
        rtn_vals_list = list(rtn_vals_list)

    return rtn_vals_list


def get_suppressed_alarms(uuid=False, con_ssh=None,
                          auth_info=Tenant.get('admin_platform')):
    """
    Get suppressed alarms_and_events as dictionary
    Args:
        uuid (bool): whether to show uuid
        con_ssh (SSHClient):
        auth_info (dict):

    Returns:
        dict: events table in format: {'headers': <headers list>, 'values':
        <list of table rows>}
    """
    args = ''
    if uuid:
        args += ' --uuid'
    args += ' --nowrap --nopaging'
    table_ = table_parser.table(
        cli.fm('event-suppress-list', args, ssh_client=con_ssh,
               auth_info=auth_info)[1])
    return table_


def unsuppress_all_events(ssh_con=None, fail_ok=False,
                          auth_info=Tenant.get('admin_platform')):
    """

    Args:
        ssh_con:
        fail_ok:
        auth_info:

    Returns (tuple): (<code>(int), <msg>(str))

    """
    LOG.info("Un-suppress all events")
    args = '--nowrap --nopaging'
    code, output = cli.fm('event-unsuppress-all', positional_args=args,
                          ssh_client=ssh_con, fail_ok=fail_ok,
                          auth_info=auth_info)

    if code == 1:
        return 1, output

    if not output:
        msg = "No suppressed events to un-suppress"
        LOG.warning(msg)
        return -1, msg

    table_ = table_parser.table(output)
    if not table_['values']:
        suppressed_list = []
    else:
        suppressed_list = table_parser.get_values(table_,
                                                  target_header="Suppressed "
                                                                "Alarm ID's",
                                                  **{'Status': 'suppressed'})

    if suppressed_list:
        msg = "Unsuppress-all failed. Suppressed Alarm IDs: {}".format(
            suppressed_list)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.NeutronError(msg)

    succ_msg = "All events unsuppressed successfully."
    LOG.info(succ_msg)
    return 0, succ_msg


def get_events(fields=('Event Log ID', 'Entity Instance ID'), limit=10,
               event_id=None, entity_id=None,
               severity=None, show_suppress=False, start=None, end=None,
               state=None, show_uuid=True,
               strict=False, time_stamp=None, reason_text=None, uuid=None,
               con_ssh=None, auth_info=Tenant.get('admin_platform'),
               combine_entries=True):
    """
    Get a list of alarms with values for specified fields.
    Args:
        fields (tuple|list|str): fields to get values for
        limit (int)
        event_id (str): filter event using event log id
        reason_text (str): reason text to filter out the table (strict
            defined in param)
        entity_id (str): entity instance id to filter out the table (strict
            defined in param)
        severity (str): severity such as 'critical', 'major'
        show_suppress (bool): whether to show suppressed events. Default to
            False.
        show_uuid (bool): Whether to show uuid in event table
        start (str): display events after this time stamp
        end (str): display events prior to this time stamp
        state (str): filter with events state
        time_stamp (str): exact timestamp for the event, filter after events
            displayed
        uuid (str)
        strict (bool): whether to perform strict filter on reason text,
            or time_stamp
        con_ssh (SSHClient):
        auth_info (dict):
        combine_entries (bool): return list of strings when set to True,
            else return a list of tuples.
            e.g., when True, returns ["800.003::::cluster=829851fa",
            "250.001::::host=controller-0"]
                  when False, returns [("800.003", "cluster=829851fa"),
                  ("250.001", "host=controller-0")]

    Returns (list): list of events with values of specified fields

    """

    table_ = get_events_table(show_uuid=show_uuid, limit=limit,
                              event_log_id=event_id,
                              entity_instance_id=entity_id,
                              show_suppress=show_suppress, con_ssh=con_ssh,
                              auth_info=auth_info,
                              start=start, end=end, severity=severity)

    kwargs_dict = {
        'Reason Text': reason_text,
        'Time Stamp': time_stamp,
        'UUID': uuid,
        'State': state,
    }

    kwargs = {}
    for key, value in kwargs_dict.items():
        if value is not None:
            kwargs[key] = value

    if kwargs:
        table_ = table_parser.filter_table(table_, strict=strict, **kwargs)

    rtn_vals_list = []
    if isinstance(fields, str):
        fields = (fields,)
    for header in fields:
        vals = table_parser.get_column(table_, header)
        if not vals:
            vals = []
        rtn_vals_list.append(vals)

    LOG.warning('{}'.format(rtn_vals_list))
    rtn_vals_list = list(zip(*rtn_vals_list))
    if combine_entries:
        rtn_vals_list = ['::::'.join(vals) for vals in rtn_vals_list]

    return rtn_vals_list


def get_events_table(limit=5, show_uuid=False, show_only=None,
                     show_suppress=False, event_log_id=None,
                     entity_type_id=None, entity_instance_id=None,
                     severity=None, start=None, end=None,
                     con_ssh=None, auth_info=Tenant.get('admin_platform'),
                     regex=False, **kwargs):
    """
    Get a list of events with given criteria as dictionary
    Args:
        limit (int): max number of event logs to return
        show_uuid (bool): whether to show uuid
        show_only (str): 'alarms_and_events' or 'logs' to return only
        alarms_and_events or logs
        show_suppress (bool): whether or not to show suppressed
            alarms_and_events
        event_log_id (str|None): event log id passed to system eventlog -q
        event_log_id=<event_log_id>
        entity_type_id (str|None): entity_type_id passed to system eventlog
            -q entity_type_id=<entity_type_id>
        entity_instance_id (str|None): entity_instance_id passed to
            system eventlog -q entity_instance_id=<entity_instance_id>
        severity (str|None):
        start (str|None): start date/time passed to '--query' in format
            "20170410"/"20170410 01:23:34"
        end (str|None): end date/time passed to '--query' in format
            "20170410"/"20170410 01:23:34"
        con_ssh (SSHClient):
        auth_info (dict):
        regex (bool):
        **kwargs: filter table after table returned

    Returns:
        dict: events table in format: {'headers': <headers list>, 'values':
        <list of table rows>}
    """

    args = '-l {}'.format(limit)

    # args = __process_query_args(args, query_key, query_value, query_type)
    query_dict = {
        'event_log_id': event_log_id,
        'entity_type_id': entity_type_id,
        'entity_instance_id': entity_instance_id,
        'severity': severity,
        'start': '{}'.format(start) if start else None,
        'end': '{}'.format(end) if end else None
    }

    queries = []
    for q_key, q_val in query_dict.items():
        if q_val is not None:
            queries.append('{}={}'.format(q_key, str(q_val)))

    query_string = ';'.join(queries)
    if query_string:
        args += " -q '{}'".format(query_string)

    args += ' --nowrap --nopaging'
    if show_uuid:
        args += ' --uuid'
    if show_only:
        args += ' --{}'.format(show_only.lower())
    if show_suppress:
        args += ' --include_suppress'

    table_ = table_parser.table(
        cli.fm('event-list ', args, ssh_client=con_ssh, auth_info=auth_info)[1])

    if kwargs:
        table_ = table_parser.filter_table(table_, regex=regex, **kwargs)

    return table_


def _compose_events_table(output, uuid=False):
    if not output['headers']:
        headers = ['UUID', 'Time Stamp', 'State', 'Event Log ID', 'Reason Text',
                   'Entity Instance ID', 'Severity']
        if not uuid:
            headers.remove('UUID')
        values = []
        output['headers'] = headers
        output['values'] = values

    return output


def __process_query_args(args, query_key, query_value, query_type):
    if query_key:
        if not query_value:
            raise ValueError(
                "Query value is not supplied for key - {}".format(query_key))
        data_type_arg = '' if not query_type else "{}::".format(
            query_type.lower())
        args += ' -q {}={}"{}"'.format(query_key.lower(), data_type_arg,
                                       query_value.lower())
    return args


def wait_for_events(timeout=60, num=30, uuid=False, show_only=None,
                    event_log_id=None, entity_type_id=None,
                    entity_instance_id=None, severity=None, start=None,
                    end=None, field='Event Log ID',
                    regex=False, strict=True, check_interval=5, fail_ok=True,
                    con_ssh=None,
                    auth_info=Tenant.get('admin_platform'), **kwargs):
    """
    Wait for event(s) to appear in fm event-list
    Args:
        timeout (int): max time to wait in seconds
        num (int): max number of event logs to return
        uuid (bool): whether to show uuid
        show_only (str): 'alarms_and_events' or 'logs' to return only
        alarms_and_events or logs
        fail_ok (bool): whether to return False if event(s) did not appear
        within timeout
        field (str): list of values to return. Defaults to 'Event Log ID'
        con_ssh (SSHClient):
        auth_info (dict):
        regex (bool): Whether to use regex or string operation to
        search/match the value in kwargs
        strict (bool): whether it's a strict match (case is always ignored
        regardless of this flag)
        check_interval (int): how often to check the event logs
        event_log_id (str|None): event log id passed to system eventlog -q
        event_log_id=<event_log_id>
        entity_type_id (str|None): entity_type_id passed to system eventlog
        -q entity_type_id=<entity_type_id>
        entity_instance_id (str|None): entity_instance_id passed to
            system eventlog -q entity_instance_id=<entity_instance_id>
        severity (str|None):
        start (str|None): start date/time passed to '--query' in format
        "20170410"/"20170410 01:23:34"
        end (str|None): end date/time passed to '--query' in format
        "20170410"/"20170410 01:23:34"

        **kwargs: criteria to filter out event(s) from the events list table

    Returns:
        list: list of event log ids (or whatever specified in rtn_value) for
        matching events.

    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        events_tab = get_events_table(limit=num, show_uuid=uuid,
                                      show_only=show_only,
                                      event_log_id=event_log_id,
                                      entity_type_id=entity_type_id,
                                      entity_instance_id=entity_instance_id,
                                      severity=severity, start=start, end=end,
                                      con_ssh=con_ssh, auth_info=auth_info)
        events_tab = table_parser.filter_table(events_tab, strict=strict,
                                               regex=regex, **kwargs)
        events = table_parser.get_column(events_tab, field)
        if events:
            LOG.info("Event(s) appeared in event-list: {}".format(events))
            return events

        time.sleep(check_interval)

    msg = "Event(s) did not appear in fm event-list within timeout."
    if fail_ok:
        LOG.warning(msg)
        return []
    else:
        raise exceptions.TimeoutException(msg)


def delete_alarms(alarms=None, fail_ok=False, con_ssh=None,
                  auth_info=Tenant.get('admin_platform')):
    """
    Delete active alarms_and_events

    Args:
        alarms (list|str): UUID(s) of alarms_and_events to delete
        fail_ok (bool): whether or not to raise exception if any alarm failed
        to delete
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (rtn_code(int), message(str))
        0, "Alarms deleted successfully"
        1, "Some alarm(s) still exist on system after attempt to delete:
        <alarms_uuids>"

    """
    if alarms is None:
        alarms_tab = get_alarms_table(uuid=True)
        alarms = []
        if alarms_tab['headers']:
            alarms = table_parser.get_column(alarms_tab, 'UUID')

    if isinstance(alarms, str):
        alarms = [alarms]

    LOG.info("Deleting following alarms_and_events: {}".format(alarms))

    res = {}
    failed_clis = []
    for alarm in alarms:
        code, out = cli.fm('alarm-delete', alarm, ssh_client=con_ssh,
                           auth_info=auth_info)
        res[alarm] = code, out

        if code != 0:
            failed_clis.append(alarm)

    post_alarms_tab = get_alarms_table(uuid=True)
    if post_alarms_tab['headers']:
        post_alarms = table_parser.get_column(post_alarms_tab, 'UUID')
    else:
        post_alarms = []

    undeleted_alarms = list(set(alarms) & set(post_alarms))
    if undeleted_alarms:
        err_msg = "Some alarm(s) still exist on system after attempt to " \
                  "delete: {}\nAlarm delete results: {}". \
            format(undeleted_alarms, res)

        if fail_ok:
            return 1, err_msg
        raise exceptions.SysinvError(err_msg)

    elif failed_clis:
        LOG.warning(
            "Some alarm-delete cli(s) rejected, but alarm no longer "
            "exists.\nAlarm delete results: {}".
            format(res))

    succ_msg = "Alarms deleted successfully"
    LOG.info(succ_msg)
    return 0, succ_msg


def wait_for_alarm_gone(alarm_id, entity_id=None, reason_text=None,
                        strict=False, timeout=120, check_interval=10,
                        fail_ok=False, con_ssh=None,
                        auth_info=Tenant.get('admin_platform')):
    """
    Wait for given alarm to disappear from fm alarm-list
    Args:
        alarm_id (str): such as 200.009
        entity_id (str): entity instance id for the alarm (strict as defined
        in param)
        reason_text (str): reason text for the alarm (strict as defined in
        param)
        strict (bool): whether to perform strict string match on entity
        instance id and reason
        timeout (int): max seconds to wait for alarm to disappear
        check_interval (int): how frequent to check
        fail_ok (bool): whether to raise exception if alarm did not disappear
        within timeout
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (bool): True if alarm is gone else False

    """

    LOG.info(
        "Waiting for alarm {} to disappear from fm alarm-list".format(alarm_id))
    build_ver = get_sw_version(con_ssh=con_ssh)

    alarmcmd = 'alarm-list'
    if build_ver != '15.12':
        alarmcmd += ' --nowrap'

    end_time = time.time() + timeout
    while time.time() < end_time:
        alarms_tab = table_parser.table(
            cli.fm(alarmcmd, ssh_client=con_ssh, auth_info=auth_info)[1])

        alarm_tab = table_parser.filter_table(alarms_tab,
                                              **{'Alarm ID': alarm_id})
        if table_parser.get_all_rows(alarm_tab):
            kwargs = {}
            if entity_id:
                kwargs['Entity ID'] = entity_id
            if reason_text:
                kwargs['Reason Text'] = reason_text

            if kwargs:
                alarms = table_parser.get_values(alarm_tab,
                                                 target_header='Alarm ID',
                                                 strict=strict, **kwargs)
                if not alarms:
                    LOG.info(
                        "Alarm {} with {} is not displayed in fm "
                        "alarm-list".format(
                            alarm_id, kwargs))
                    return True

        else:
            LOG.info(
                "Alarm {} is not displayed in fm alarm-list".format(alarm_id))
            return True

        time.sleep(check_interval)

    else:
        err_msg = "Timed out waiting for alarm {} to disappear".format(alarm_id)
        if fail_ok:
            LOG.warning(err_msg)
            return False
        else:
            raise exceptions.TimeoutException(err_msg)


def _get_alarms(alarms_tab):
    alarm_ids = table_parser.get_column(alarms_tab, 'Alarm_ID')
    entity_ids = table_parser.get_column(alarms_tab, 'Entity ID')
    alarms = list(zip(alarm_ids, entity_ids))
    return alarms


def wait_for_alarm(field='Alarm ID', alarm_id=None, entity_id=None, reason=None,
                   severity=None, timeout=60,
                   check_interval=3, regex=False, strict=False, fail_ok=False,
                   con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Wait for given alarm to appear
    Args:
        field:
        alarm_id (str): such as 200.009
        entity_id (str|list|tuple): entity instance id for the alarm (strict
        as defined in param)
        reason (str): reason text for the alarm (strict as defined in param)
        severity (str): severity of the alarm to wait for
        timeout (int): max seconds to wait for alarm to appear
        check_interval (int): how frequent to check
        regex (bool): whether to use regex when matching entity instance id
        and reason
        strict (bool): whether to perform strict match on entity instance id
        and reason
        fail_ok (bool): whether to raise exception if alarm did not disappear
        within timeout
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (<res_bool>, <rtn_val>). Such as (True, '200.009') or (
    False, None)

    """

    kwargs = {}
    if alarm_id:
        kwargs['Alarm ID'] = alarm_id
    if reason:
        kwargs['Reason Text'] = reason
    if severity:
        kwargs['Severity'] = severity

    if entity_id and isinstance(entity_id, str):
        entity_id = [entity_id]

    end_time = time.time() + timeout
    while time.time() < end_time:
        current_alarms_tab = get_alarms_table(con_ssh=con_ssh,
                                              auth_info=auth_info)
        if kwargs:
            current_alarms_tab = table_parser.filter_table(
                table_=current_alarms_tab, strict=strict, regex=regex,
                **kwargs)
        if entity_id:
            val = []
            for entity in entity_id:
                entity_filter = {'Entity ID': entity}
                val_ = table_parser.get_values(current_alarms_tab, field,
                                               strict=strict, regex=regex,
                                               **entity_filter)
                if not val_:
                    LOG.info(
                        "Alarm for entity {} has not appeared".format(entity))
                    time.sleep(check_interval)
                    continue
                val += val_
        else:
            val = table_parser.get_values(current_alarms_tab, field)

        if val:
            LOG.info('Expected alarm appeared. Filters: {}'.format(kwargs))
            return True, val

        time.sleep(check_interval)

    entity_str = ' for entity {}'.format(entity_id) if entity_id else ''
    err_msg = "Alarm {}{} did not appear in fm alarm-list within {} " \
              "seconds".format(kwargs, entity_str, timeout)
    if fail_ok:
        LOG.warning(err_msg)
        return False, None

    raise exceptions.TimeoutException(err_msg)


def wait_for_alarms_gone(alarms, timeout=120, check_interval=3, fail_ok=False,
                         con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Wait for given alarms_and_events to be gone from fm alarm-list
    Args:
        alarms (list): list of tuple. [(<alarm_id1>, <entity_id1>), ...]
        timeout (int):
        check_interval (int):
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (res(bool), remaining_alarms(list of tuple))

    """
    pre_alarms = list(alarms)  # Don't update the original list
    LOG.info(
        "Waiting for alarms_and_events to disappear from fm alarm-list: "
        "{}".format(pre_alarms))
    alarms_to_check = pre_alarms.copy()

    alarms_cleared = []

    def _update_alarms(alarms_to_check_, alarms_cleared_):
        current_alarms_tab = get_alarms_table(con_ssh=con_ssh,
                                              auth_info=auth_info)
        current_alarms = _get_alarms(current_alarms_tab)

        for alarm in pre_alarms:
            if alarm not in current_alarms:
                LOG.info(
                    "Removing alarm {} from current alarms_and_events list: "
                    "{}".format(alarm, alarms_to_check))
                alarms_to_check_.remove(alarm)
                alarms_cleared_.append(alarm)

    _update_alarms(alarms_to_check_=alarms_to_check,
                   alarms_cleared_=alarms_cleared)
    if not alarms_to_check:
        LOG.info(
            "Following alarms_and_events cleared: {}".format(alarms_cleared))
        return True, []

    end_time = time.time() + timeout
    while time.time() < end_time:
        pre_alarms = alarms_to_check.copy()
        time.sleep(check_interval)
        _update_alarms(alarms_to_check_=alarms_to_check,
                       alarms_cleared_=alarms_cleared)
        if not alarms_to_check:
            LOG.info("Following alarms_and_events cleared: {}".format(
                alarms_cleared))
            return True, []
    else:
        err_msg = "Following alarms_and_events did not clear within {} " \
                  "seconds: {}".format(timeout, alarms_to_check)
        if fail_ok:
            LOG.warning(err_msg)
            return False, alarms_to_check
        else:
            raise exceptions.TimeoutException(err_msg)


def wait_for_all_alarms_gone(timeout=120, check_interval=3, fail_ok=False,
                             con_ssh=None,
                             auth_info=Tenant.get('admin_platform')):
    """
    Wait for all alarms_and_events to be cleared from fm alarm-list
    Args:
        timeout (int):
        check_interval (int):
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (res(bool), remaining_alarms(tuple))

    """

    LOG.info(
        "Waiting for all existing alarms_and_events to disappear from fm "
        "alarm-list: {}".format(
            get_alarms()))

    end_time = time.time() + timeout
    while time.time() < end_time:
        current_alarms_tab = get_alarms_table(con_ssh=con_ssh,
                                              auth_info=auth_info)
        current_alarms = _get_alarms(current_alarms_tab)

        if len(current_alarms) == 0:
            return True, []
        else:
            time.sleep(check_interval)

    else:
        existing_alarms = get_alarms()
        err_msg = "Alarms did not clear within {} seconds: {}".format(
            timeout, existing_alarms)
        if fail_ok:
            LOG.warning(err_msg)
            return False, existing_alarms
        else:
            raise exceptions.TimeoutException(err_msg)


def host_exists(host, field='hostname', con_ssh=None,
                auth_info=Tenant.get('admin_platform')):
    """

    Args:
        host:
        field:
        con_ssh:
        auth_info

    Returns (bool): whether given host exists in system host-list

    """
    if not field.lower() in ['hostname', 'id']:
        raise ValueError("field has to be either \'hostname\' or \'id\'")

    hosts = get_hosts(con_ssh=con_ssh, auth_info=auth_info, field=field)
    return host in hosts


def modify_system(fail_ok=True, con_ssh=None,
                  auth_info=Tenant.get('admin_platform'), **kwargs):
    """
    Modify the System configs/info.

    Args:
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        **kwargs:   attribute-value pairs

    Returns: (int, str)
         0  - success
         1  - error

    Test Steps:
        - Set the value via system modify <attr>=<value> [,<attr>=<value]

    Notes:
        Currently only the following are allowed to change:
        name
        description
        location
        contact

        The following attributes are readonly and not allowed CLI user to
        change:
            system_type
            software_version
            uuid
            created_at
            updated_at
    """
    if not kwargs:
        raise ValueError(
            "Please specify at least one systeminfo_attr=value pair via "
            "kwargs.")

    attr_values_ = ['--{}="{}"'.format(attr, value) for attr, value in
                    kwargs.items()]
    args_ = ' '.join(attr_values_)

    code, output = cli.system('modify', args_, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)

    if code == 1:
        return 1, output

    return 0, ''


def get_system_values(fields='name', rtn_dict=False,
                      auth_info=Tenant.get('admin_platform'), con_ssh=None):
    table_ = table_parser.table(
        cli.system('show', ssh_client=con_ssh, auth_info=auth_info)[1])

    return table_parser.get_multi_values_two_col_table(table_, fields=fields,
                                                       rtn_dict=rtn_dict)


def wait_for_file_update(file_path, grep_str, expt_val, timeout=300,
                         fail_ok=False, ssh_client=None):
    LOG.info("Wait for {} to be updated to {} in {}".format(grep_str, expt_val,
                                                            file_path))
    if not ssh_client:
        ssh_client = ControllerClient.get_active_controller()

    pattern = '{}.*=(.*)'.format(grep_str)
    end_time = time.time() + timeout
    value = None
    while time.time() < end_time:
        output = ssh_client.exec_sudo_cmd('grep "^{}" {}'.format(grep_str,
                                                                 file_path),
                                          fail_ok=False)[1]
        value = int((re.findall(pattern, output)[0]).strip())
        if expt_val == value:
            return True, value
        time.sleep(5)

    msg = "Timed out waiting for {} to reach {} in {}. Actual: {}".format(
        grep_str, expt_val, file_path, value)
    if fail_ok:
        LOG.warning(msg)
        return False, value
    raise exceptions.SysinvError(msg)


def get_dns_servers(auth_info=Tenant.get('admin_platform'), con_ssh=None, ):
    """
    Get the DNS servers currently in-use in the System

    Args:
        auth_info(dict)
        con_ssh

    Returns (list): a list of DNS servers will be returned

    """
    table_ = table_parser.table(cli.system('dns-show', ssh_client=con_ssh,
                                           auth_info=auth_info)[1])
    dns_servers = table_parser.get_value_two_col_table(table_,
                                                       'nameservers').strip(

    ).split(
        sep=',')

    region = ''
    if isinstance(auth_info, dict):
        region = auth_info.get('region', None)
        region = ' for {}'.format(region) if region else ''
    LOG.info('Current dns servers{}: {}'.format(region, dns_servers))
    return dns_servers


def set_dns_servers(nameservers, with_action_option=None, check_first=True,
                    fail_ok=True, con_ssh=None,
                    auth_info=Tenant.get('admin_platform')):
    """
    Set the DNS servers

    Args:
        fail_ok:
        check_first
        con_ssh:
        auth_info:
        nameservers (list|tuple): list of IP addresses (in plain text) of new
            DNS servers to change to
        with_action_option: whether invoke the CLI with or without "action"
            option
            - None      no "action" option at all
            - install   system dns-modify <> action=install
            - anystr    system dns-modify <> action=anystring...
    Returns (tuple):
        (-1, <dns_servers>)
        (0, <dns_servers>)
        (1, <std_err>)

    """
    if not nameservers:
        raise ValueError("Please specify DNS server(s).")

    if check_first:
        dns_servers = get_dns_servers(con_ssh=con_ssh,
                                      auth_info=auth_info)
        if dns_servers == nameservers and with_action_option is None:
            msg = 'DNS servers already set to {}. Do nothing.'.format(
                dns_servers)
            LOG.info(msg)
            return -1, dns_servers

    args_ = 'nameservers="{}"'.format(','.join(nameservers))

    if with_action_option is not None:
        args_ += ' action={}'.format(with_action_option)

    LOG.info('args_:{}'.format(args_))
    code, output = cli.system('dns-modify', args_, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info,
                              timeout=SysInvTimeout.DNS_MODIFY)
    if code == 1:
        return 1, output

    post_dns_servers = get_dns_servers(auth_info=auth_info, con_ssh=con_ssh)
    if post_dns_servers != nameservers:
        raise exceptions.SysinvError(
            'dns servers expected: {}; actual: {}'.format(nameservers,
                                                          post_dns_servers))

    LOG.info("DNS servers successfully updated to: {}".format(nameservers))
    return 0, nameservers


def get_vm_topology_tables(*table_names, con_ssh=None, combine_multiline=False,
                           exclude_one_col_table=True,
                           auth_info=Tenant.get('admin')):
    if con_ssh is None:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    show_args = ','.join(table_names)

    tables_ = table_parser.tables(con_ssh.exec_sudo_cmd('vm-topology --show {}'.
                                                        format(show_args),
                                                        expect_timeout=30)[1],
                                  combine_multiline_entry=combine_multiline)

    if exclude_one_col_table:
        new_tables = []
        for table_ in tables_:
            if len(table_['headers']) > 1:
                new_tables.append(table_)
        return new_tables

    return tables_


def __suppress_unsuppress_event(alarm_id, suppress=True, check_first=False,
                                fail_ok=False, con_ssh=None,
                                auth_info=Tenant.get('admin_platform')):
    """
    suppress/unsuppress an event by uuid
    Args:
        alarm_id (str):
        fail_ok (bool):
        con_ssh (SSHClient)
        suppress(bool) True or false

    Returns (tuple): (rtn_code, message)
        (0, )
    """

    suppressed_alarms_tab = get_suppressed_alarms(uuid=True, con_ssh=con_ssh,
                                                  auth_info=auth_info)

    alarm_status = "unsuppressed" if suppress else "suppressed"
    cmd = "event-suppress" if suppress else "event-unsuppress"
    alarm_filter = {"Suppressed Event ID's": alarm_id}

    if check_first:
        if not suppressed_alarms_tab['values']:
            pre_status = "unsuppressed"
        else:
            pre_status = table_parser.get_values(table_=suppressed_alarms_tab,
                                                 target_header='Status',
                                                 strict=True,
                                                 **alarm_filter)[0]
        if pre_status.lower() != alarm_status:
            msg = "Event is already {}. Do nothing".format(pre_status)
            LOG.info(msg)
            return -1, msg

    code, output = cli.fm(cmd, '--alarm_id ' + alarm_id, ssh_client=con_ssh,
                          fail_ok=fail_ok, auth_info=auth_info)

    if code == 1:
        return 1, output

    post_suppressed_alarms_tab = get_suppressed_alarms(uuid=True,
                                                       con_ssh=con_ssh)
    if not post_suppressed_alarms_tab['values']:
        post_status = ["unsuppressed"]
    else:
        post_status = table_parser.get_values(table_=post_suppressed_alarms_tab,
                                              target_header="Status",
                                              strict=True,
                                              **{"Event id": alarm_id})
    expt_status = "suppressed" if suppress else "unsuppressed"
    if post_status[0].lower() != expt_status:
        msg = "Alarm {} is not {}".format(alarm_id, expt_status)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.TiSError(msg)

    succ_msg = "Event {} is {} successfully".format(alarm_id, expt_status)
    LOG.info(succ_msg)
    return 0, succ_msg


def suppress_event(alarm_id, check_first=False, fail_ok=False, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    return __suppress_unsuppress_event(alarm_id, True, check_first=check_first,
                                       fail_ok=fail_ok, con_ssh=con_ssh,
                                       auth_info=auth_info)


def unsuppress_event(alarm_id, check_first=False, fail_ok=False, con_ssh=None,
                     auth_info=Tenant.get('admin_platform')):
    return __suppress_unsuppress_event(alarm_id, False, check_first=check_first,
                                       fail_ok=fail_ok, con_ssh=con_ssh,
                                       auth_info=auth_info)


def generate_event(event_id='300.005', state='set', severity='critical',
                   reason_text='Generated for testing',
                   entity_id='STXAuto', unknown_text='unknown1',
                   unknown_two='unknown2', con_ssh=None):
    cmd = '''fmClientCli -c  "### ###{}###{}###{}###{}### ###{}### ###{}###
    {}### ###True###True###"'''. \
        format(event_id, state, reason_text, entity_id, severity, unknown_text,
               unknown_two)

    LOG.info("Generate system event: {}".format(cmd))
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    output = con_ssh.exec_cmd(cmd, fail_ok=False)[1]
    event_uuid = re.findall(UUID, output)[0]
    LOG.info("Event {} generated successfully".format(event_uuid))

    return event_uuid


def get_service_parameter_values(service=None, section=None, name=None,
                                 field='value', con_ssh=None,
                                 auth_info=Tenant.get('admin_platform')):
    """
    Returns the list of values from system service-parameter-list
    service, section, name can be used to filter the table
    Args:
        field (str): field to return valueds for. Default to 'value'
        service (str):
        section (str):
        name (str):
        con_ssh:
        auth_info

    Returns (list):

    """
    kwargs = {}
    if service:
        kwargs['service'] = service
    if section:
        kwargs['section'] = section
    if name:
        kwargs['name'] = name

    table_ = table_parser.table(
        cli.system('service-parameter-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_values(table_, field, **kwargs)


def create_service_parameter(service, section, name, value, con_ssh=None,
                             fail_ok=False, check_first=True,
                             modify_existing=True, verify=True, apply=False,
                             auth_info=Tenant.get('admin_platform')):
    """
    Add service-parameter
    system service-parameter-add (service) (section) (name)=(value)
    Args:
        service (str): Required
        section (str): Required
        name (str): Required
        value (str): Required
        con_ssh:
        fail_ok:
        check_first (bool): Check if the service parameter exists before
        modify_existing (bool): Whether to modify the service parameter if it
            already exists
        verify: this enables to skip the verification. sometimes not all
            values are displayed in the
            service-parameter-list, ex password
        apply (bool): whether to apply service parameter after add
        auth_info

    Returns (tuple): (rtn_code, err_msg or param_uuid)

    """
    if check_first:
        val = get_service_parameter_values(service=service, section=section,
                                           name=name, con_ssh=con_ssh,
                                           auth_info=auth_info)
        if val:
            val = val[0]
            msg = "The service parameter {} {} {} already exists. value: " \
                  "{}".format(service, section, name, val)
            LOG.info(msg)
            if value != val and modify_existing:
                return modify_service_parameter(service, section, name, value,
                                                create=False, apply=apply,
                                                con_ssh=con_ssh,
                                                fail_ok=fail_ok,
                                                check_first=False,
                                                verify=verify,
                                                auth_info=auth_info)
            return -1, msg

    LOG.info("Creating service parameter")
    args = service + ' ' + section + ' ' + name + '=' + value
    res, out = cli.system('service-parameter-add', args, ssh_client=con_ssh,
                          fail_ok=fail_ok)
    if res == 1:
        return 1, out

    LOG.info("Verifying the service parameter value")
    val = get_service_parameter_values(service=service, section=section,
                                       name=name, con_ssh=con_ssh,
                                       auth_info=auth_info)[0]
    value = value.strip('\"')
    if verify:
        if val != value:
            msg = 'The service parameter was not added with the correct ' \
                  'value {} to {}'.format(val, value)
            if fail_ok:
                return 2, msg
            raise exceptions.SysinvError(msg)
    LOG.info("Service parameter was added with the correct value")
    uuid = get_service_parameter_values(field='uuid', service=service,
                                        section=section, name=name,
                                        con_ssh=con_ssh,
                                        auth_info=auth_info)[0]
    if apply:
        apply_service_parameters(service, wait_for_config=True,
                                 con_ssh=con_ssh,
                                 auth_info=auth_info)

    return 0, uuid


def modify_service_parameter(service, section, name, value, apply=False,
                             con_ssh=None, fail_ok=False,
                             check_first=True, create=True, verify=True,
                             auth_info=Tenant.get('admin_platform')):
    """
    Modify a service parameter
    Args:
        service (str): Required
        section (str): Required
        name (str): Required
        value (str): Required
        apply
        con_ssh:
        fail_ok:
        check_first (bool): Check if the parameter exists first
        create (bool): Whether to create the parameter if it does not exist
        verify: this enables to skip the verification. sometimes not all
            values are displayed in the service-parameter-list, ex password
        auth_info

    Returns (tuple): (rtn_code, message)

    """
    if check_first:
        val = get_service_parameter_values(service=service, section=section,
                                           name=name, con_ssh=con_ssh)
        if not val:
            msg = "The service parameter {} {} {} doesn't exist".format(service,
                                                                        section,
                                                                        name)
            LOG.info(msg)
            if create:
                return create_service_parameter(service, section, name, value,
                                                auth_info=auth_info,
                                                con_ssh=con_ssh,
                                                fail_ok=fail_ok,
                                                check_first=False)
            return -1, msg
        if val[0] == value:
            msg = "The service parameter value is already set to {}".format(val)
            return -1, msg

    LOG.info("Modifying service parameter")
    args = service + ' ' + section + ' ' + name + '=' + value
    res, out = cli.system('service-parameter-modify', args, ssh_client=con_ssh,
                          fail_ok=fail_ok, auth_info=auth_info)

    if res == 1:
        return 1, out

    LOG.info("Verifying the service parameter value")
    val = get_service_parameter_values(service=service, section=section,
                                       name=name, con_ssh=con_ssh,
                                       auth_info=auth_info)[0]
    value = value.strip('\"')
    if verify:
        if val != value:
            msg = 'The service parameter was not modified to the correct value'
            if fail_ok:
                return 2, msg
            raise exceptions.SysinvError(msg)
    msg = "Service parameter modified to {}".format(val)
    LOG.info(msg)

    if apply:
        apply_service_parameters(service, wait_for_config=True, con_ssh=con_ssh,
                                 auth_info=auth_info)

    return 0, msg


def delete_service_parameter(uuid, con_ssh=None, fail_ok=False,
                             check_first=True,
                             auth_info=Tenant.get('admin_platform')):
    """
    Delete a service parameter
    Args:
        uuid (str): Required
        con_ssh:
        fail_ok:
        check_first (bool): Check if the service parameter exists before
        auth_info

    Returns (tuple):

    """
    if check_first:
        uuids = get_service_parameter_values(field='uuid', con_ssh=con_ssh,
                                             auth_info=auth_info)
        if uuid not in uuids:
            return -1, "There is no service parameter with uuid {}".format(uuid)

    res, out = cli.system('service-parameter-delete', uuid, ssh_client=con_ssh,
                          fail_ok=fail_ok, auth_info=auth_info)

    if res == 1:
        return 1, out

    LOG.info("Deleting service parameter")
    uuids = get_service_parameter_values(field='uuid', con_ssh=con_ssh,
                                         auth_info=auth_info)
    if uuid in uuids:
        err_msg = "Service parameter was not deleted"
        if fail_ok:
            return 2, err_msg
        raise exceptions.SysinvError(err_msg)
    msg = "The service parameter {} was deleted".format(uuid)
    LOG.info(msg)
    return 0, msg


def apply_service_parameters(service, wait_for_config=True, timeout=300,
                             con_ssh=None,
                             fail_ok=False,
                             auth_info=Tenant.get('admin_platform')):
    """
    Apply service parameters
    Args:
        service (str): Required
        wait_for_config (bool): Wait for config out of date alarms to clear
        timeout (int):
        con_ssh:
        auth_info
        fail_ok:

    Returns (tuple): (rtn_code, message)

    """
    LOG.info("Applying service parameters {}".format(service))
    res, out = cli.system('service-parameter-apply', service,
                          ssh_client=con_ssh, fail_ok=fail_ok,
                          auth_info=auth_info)

    if res == 1:
        return res, out

    alarm_id = '250.001'
    time.sleep(10)

    if wait_for_config:
        LOG.info("Waiting for config-out-of-date alarms to clear. "
                 "There may be cli errors when active controller's config "
                 "updates")
        end_time = time.time() + timeout
        while time.time() < end_time:
            table_ = get_alarms_table(uuid=True, con_ssh=con_ssh, retry=3)
            alarms_tab = table_parser.filter_table(table_,
                                                   **{'Alarm ID': alarm_id})
            uuids = table_parser.get_values(alarms_tab, 'uuid')
            if not uuids:
                LOG.info("Config has been applied")
                break
            time.sleep(5)
        else:
            err_msg = "The config has not finished applying after timeout"
            if fail_ok:
                return 2, err_msg
            raise exceptions.TimeoutException(err_msg)

    return 0, "The {} service parameter was applied".format(service)


def get_system_health_query(con_ssh=None,
                            auth_info=Tenant.get('admin_platform')):
    output = cli.system('health-query', ssh_client=con_ssh, fail_ok=False,
                        auth_info=auth_info, source_openrc=True)[1]
    output = output.splitlines()
    failed = []
    for line in output:
        if "[Fail]" in line:
            failed_item = line.split(sep=': ')[0]
            failed.append(failed_item.strip())

    if failed:
        return 1, failed
    else:
        return 0, None


def get_build_info(con_ssh=None, refresh=False):
    """
    Get build info from /etc/build.info
    Args:
        con_ssh:
        refresh:

    Returns (dict):

    """

    build_info = ProjVar.get_var('BUILD_INFO')
    if build_info and not refresh:
        return build_info

    con_client = con_ssh
    code, output = con_client.exec_cmd('cat /etc/build.info')
    build_info = {}
    for line in output.splitlines():
        if '="' in line:
            key, value = re.findall('(.*)="(.*)"', line)[0]
            build_info[key] = value

    for mandatory_key in ('BUILD_ID', 'BUILD_HOST', 'BUILD_BY', 'JOB'):
        if mandatory_key not in build_info:
            build_info[mandatory_key] = ''

    ProjVar.set_var(BUILD_INFO=build_info)
    sw_version = build_info.get('SW_VERSION')
    if sw_version:
        existing_versions = ProjVar.get_var('SW_VERSION')
        if not (existing_versions and sw_version == existing_versions[-1]):
            ProjVar.set_var(append=True, SW_VERSION=sw_version)

    return build_info


def get_sw_version(con_ssh=None, use_existing=True):
    """

    Args:
        con_ssh:
        use_existing

    Returns (str): e.g., 16.10

    """
    sw_versions = ProjVar.get_var('SW_VERSION')
    if use_existing and sw_versions:
        return sw_versions[-1]

    info_dict = get_build_info(con_ssh=con_ssh, refresh=True)
    return info_dict.get('SW_VERSION')


def install_license(license_path, timeout=30, con_ssh=None):
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    cmd = "test -e {}".format(license_path)
    rc = con_ssh.exec_cmd(cmd, fail_ok=True)[0]

    if rc != 0:
        msg = "The {} file missing from active controller".format(license_path)
        return rc, msg

    cmd = "sudo license-install " + license_path
    con_ssh.send(cmd)
    end_time = time.time() + timeout
    rc = 1
    while time.time() < end_time:
        index = con_ssh.expect(
            [con_ssh.prompt, Prompt.PASSWORD_PROMPT, Prompt.Y_N_PROMPT],
            timeout=timeout)
        if index == 2:
            con_ssh.send('y')

        if index == 1:
            con_ssh.send(HostLinuxUser.get_password())

        if index == 0:
            rc = con_ssh.exec_cmd("echo $?")[0]
            con_ssh.flush()
            break

    return rc


def wait_for_services_enable(timeout=300, fail_ok=False, con_ssh=None):
    """
    Wait for services to be enabled-active in system service-list
    Args:
        timeout (int): max wait time in seconds
        fail_ok (bool): whether return False or raise exception when some
        services fail to reach enabled-active state
        con_ssh (SSHClient):

    Returns (tuple): (<res>(bool), <msg>(str))
        (True, "All services are enabled-active")
        (False, "Some services are not enabled-active: <failed_rows>")
        Applicable if fail_ok=True

    """
    LOG.info("Wait for services to be enabled-active in system service-list")
    service_list_tab = None
    end_time = time.time() + timeout
    while time.time() < end_time:
        service_list_tab = table_parser.table(
            cli.system('service-list', ssh_client=con_ssh)[1])
        states = table_parser.get_column(service_list_tab, 'state')
        if all(state == 'enabled-active' for state in states):
            LOG.info("All services are enabled-active in system service-list")
            return True, "All services are enabled-active"

    LOG.warning(
        "Not all services are enabled-ative within {} seconds".format(timeout))
    inactive_services_tab = table_parser.filter_table(service_list_tab,
                                                      exclude=True,
                                                      state='enabled-active')
    msg = "Some services are not enabled-active: {}".format(
        table_parser.get_all_rows(inactive_services_tab))
    if fail_ok:
        return False, msg
    raise exceptions.SysinvError(msg)


def enable_service(service_name, con_ssh=None,
                   auth_info=Tenant.get('admin_platform'), fail_ok=False):
    """
    Enable Service
    Args:
        service_name (str):
        con_ssh (SSHClient):
        auth_info (dict):
        fail_ok: whether return False or raise exception when some services
        fail to reach enabled-active state

    Returns (tuple):

    """

    res, output = cli.system('service-enable', service_name, ssh_client=con_ssh,
                             fail_ok=fail_ok, auth_info=auth_info)
    if res == 1:
        return 1, output

    msg = "Service enabled: {]".format(service_name)
    LOG.info(msg)
    return 0, msg


def disable_service(service_name, con_ssh=None,
                    auth_info=Tenant.get('admin_platform'), fail_ok=False):
    """
    Disable Service
    Args:
        service_name (str)
        con_ssh (SSHClient):
        auth_info (dict):
        fail_ok: whether return False or raise exception when some services
        fail to reach enabled-active state

    Returns (tuple):

    """

    res, output = cli.system('service-disable', service_name,
                             ssh_client=con_ssh, fail_ok=fail_ok,
                             auth_info=auth_info)
    if res == 1:
        return 1, output

    msg = "Service disabled: {}".format(service_name)
    LOG.info(msg)
    return 0, msg


def get_system_networks(field='uuid', uuid=None, net_type=None, mtu=None,
                        dynamic=None, pool_uuid=None,
                        auth_info=Tenant.get('admin_platform'), con_ssh=None,
                        strict=True,
                        regex=None, **kwargs):
    """
    Get networks values from system network-list
    Args:
        field: 'uuid' (default)
        uuid:
        net_type:
        mtu:
        dynamic:
        pool_uuid:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):
    """
    table_ = table_parser.table(
        cli.system('network-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'uuid': uuid,
        'type': net_type,
        'mtu': mtu,
        'dynamic': dynamic,
        'pool_uuid': pool_uuid
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_clusters(field='uuid', uuid=None, cluster_uuid=None, ntype=None,
                 name=None,
                 auth_info=Tenant.get('admin_platform'), con_ssh=None,
                 strict=True, regex=None, **kwargs):
    """
    Get cluster values from system cluster-list
    Args:
        field: 'uuid' (default)
        uuid:
        cluster_uuid:
        ntype: (mapped as ntype)
        name:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('cluster-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'uuid': uuid,
        'cluster_uuid': cluster_uuid,
        'ntype': ntype,
        'name': name,
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_services(field='id', service_id=None, service_name=None, hostname=None,
                 state=None,
                 auth_info=Tenant.get('admin_platform'), con_ssh=None,
                 strict=True, regex=None, **kwargs):
    """
    Get service_list through service service-list command
    Args:
        field: 'id' (default value)
        service_id:
        service_name:
        hostname:
        state:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('service-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'id': service_id,
        'service_name': service_name,
        'hostname': hostname,
        'state': state
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_servicenodes(field='id', servicenode_id=None, name=None,
                     operational=None, availability=None,
                     ready_state=None, auth_info=Tenant.get('admin_platform'),
                     con_ssh=None, strict=True,
                     regex=None, **kwargs):
    """
    Get servicenodes list through service servicenode-list

    Args:
        field (str|tuple|list): 'id' (default)
        servicenode_id:
        name:
        operational:
        availability:
        ready_state:
        auth_info:
        con_ssh:
        strict:
        regex:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('servicenode-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'id': servicenode_id,
        'name': name,
        'operational': operational,
        'ready_state': ready_state,
        'availability': availability
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_servicegroups(fields='uuid', uuid=None, service_group_name=None,
                      hostname=None, state=None,
                      auth_info=Tenant.get('admin_platform'), con_ssh=None,
                      strict=True, regex=None, **kwargs):
    """
    Get servicegroups via system servicegroup-list
    Args:
        fields: 'uuid' (default)
        uuid:
        service_group_name:
        hostname:
        state:
        auth_info:
        con_ssh:
        strict:
        regex
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('servicegroup-list', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    args_temp = {
        'uuid': uuid,
        'service_group_name': service_group_name,
        'hostname': hostname,
        'state': state
    }
    kwargs.update({k: v for k, v in args_temp.items() if v is not None})
    return table_parser.get_multi_values(table_, fields, strict=strict,
                                         regex=regex, **kwargs)


def create_snmp_comm(comm_string, field='uuid', fail_ok=False, con_ssh=None,
                     auth_info=Tenant.get('admin_platform')):
    """
    Create a new SNMP community string
    Args:
        comm_string (str): Community string to create
        field (str): property to return
        fail_ok (bool)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):

    """
    args = '-c "{}"'.format(comm_string)
    code, out = cli.system('snmp-comm-add', args, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, out

    val = table_parser.get_value_two_col_table(table_parser.table(out),
                                               field=field)

    return 0, val


def create_snmp_trapdest(comm_string, ip_addr, field='uuid', fail_ok=False,
                         con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Create a new SNMP trap destination
    Args:
        comm_string (str): SNMP community string
        ip_addr (str): IP address of the trap destination
        field (str): property to return
        fail_ok (bool)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):

    """
    args = '-c "{}" -i "{}"'.format(comm_string, ip_addr)
    code, out = cli.system('snmp-trapdest-add', args, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, out

    val = table_parser.get_value_two_col_table(table_parser.table(out),
                                               field=field)

    return 0, val


def get_snmp_comms(field='SNMP community', con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get SNMP community strings
    Args:
        field (str|list|tuple)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('snmp-comm-list', ssh_client=con_ssh, auth_info=auth_info)[
            1])

    return table_parser.get_multi_values(table_, field)


def get_snmp_trapdests(field='IP Address', con_ssh=None,
                       auth_info=Tenant.get('admin_platform'),
                       exclude_system=True,
                       **kwargs):
    """
    Get SNMP trap destination ips
    Args:
        field (str|tuple|list):
        con_ssh (SSHClient):
        auth_info (dict):
        exclude_system
        kwargs

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('snmp-trapdest-list', ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    if exclude_system:
        table_ = table_parser.filter_table(table_, exclude=True, **{
            'SNMP Community': 'dcorchAlarmAggregator'})

    return table_parser.get_multi_values(table_, field, **kwargs)


def delete_snmp_comm(comms, check_first=True, fail_ok=False, con_ssh=None,
                     auth_info=Tenant.get('admin_platform')):
    """
    Delete snmp community string
    Args:
        comms (str): Community string or uuid to delete
        check_first (bool)
        fail_ok (bool)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):

    """
    if isinstance(comms, str):
        comms = comms.split(sep=' ')
    else:
        comms = list(comms)

    if check_first:
        current_comms = get_snmp_comms(con_ssh=con_ssh, auth_info=auth_info)
        comms = [comm for comm in comms if comm in current_comms]
        if not comms:
            msg = '"{}" SNMP community string does not exist. Do ' \
                  'nothing.'.format(comms)
            LOG.info(msg)
            return -1, msg

    LOG.info('Deleting SNMP community strings: {}'.format(comms))
    comms = ' '.join(['"{}"'.format(comm) for comm in comms])
    code, out = cli.system('snmp-comm-delete', comms, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)

    post_comms = get_snmp_comms(con_ssh=con_ssh, auth_info=auth_info)
    undeleted_comms = [comm for comm in comms if comm in post_comms]
    if undeleted_comms:
        raise exceptions.SysinvError(
            "Community string still exist after deletion: {}".format(
                undeleted_comms))

    if code == 0:
        msg = 'SNMP community string "{}" is deleted successfully'.format(comms)
    else:
        msg = 'SNMP community string "{}" failed to delete'.format(comms)

    LOG.info(msg)
    return code, out


def delete_snmp_trapdest(ip_addrs, fail_ok=False, con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Delete SNMP trap destination
    Args:
        ip_addrs (str|list): SNMP trap destination IP address(es)
        fail_ok (bool)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (dict):

    """
    if isinstance(ip_addrs, str):
        ip_addrs = ip_addrs.split(sep=' ')

    arg = ''
    for ip_addr in ip_addrs:
        arg += '"{}" '.format(ip_addr)
    code, out = cli.system('snmp-trapdest-delete', arg, ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)

    return code, out


def get_oam_values(fields=None, con_ssh=None,
                   auth_info=Tenant.get('admin_platform'), rtn_dict=True):
    """
    Get oam info via system oam-show
    Args:
        fields:
        con_ssh:
        auth_info:
        rtn_dict

    Returns (dict|list):

    """
    table_ = table_parser.table(
        cli.system('oam-show', ssh_client=con_ssh, auth_info=auth_info)[1])

    if not fields:
        fields = table_parser.get_column(table_, 'Property')
        fields = [field for field in fields if field.startswith('oam_')]

    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       rtn_dict=rtn_dict)


def modify_oam_ips(fail_ok=False, con_ssh=None,
                   auth_info=Tenant.get('admin_platform'), **kwargs):
    """
    Modify oam ip(s)
    Args:
        fail_ok:
        con_ssh:
        auth_info:

    Returns:

    """
    if not kwargs:
        raise ValueError("Nothing is provided to modify")

    args = ' '.join(['{}={}'.format(key, val) for key, val in kwargs.items()])
    LOG.info("Modify oam ip(s): {}".format(args))
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    original = get_oam_values(fields=list(kwargs.keys()), auth_info=auth_info,
                              con_ssh=con_ssh)
    code, output = cli.system('oam-modify', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    oam_info = get_oam_values(fields=list(kwargs.keys()), auth_info=auth_info,
                              con_ssh=con_ssh)
    for field, expt_val in kwargs.items():
        actual_val = oam_info[field]
        if expt_val != actual_val:
            raise exceptions.SysinvError(
                "{} expected: {}, actual: {}".format(field, expt_val,
                                                     actual_val))

    from keywords import host_helper
    active, standby = get_active_standby_controllers(con_ssh=con_ssh,
                                                     auth_info=auth_info)
    standby_configured = True
    if standby:
        standby_configured = False
        if wait_for_alarm(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                          entity_id=standby, timeout=120,
                          con_ssh=con_ssh, fail_ok=True,
                          auth_info=auth_info)[0]:
            host_helper.lock_unlock_hosts(standby, auth_info=auth_info,
                                          con_ssh=con_ssh)
            standby_configured = True

    if not standby_configured:
        revert_args = ' '.join(
            ['{}={}'.format(key, val) for key, val in original.items()])
        LOG.error("Failed to modify oam ip. Revert to: {}".format(revert_args))
        cli.system('oam-modify', revert_args, ssh_client=con_ssh,
                   auth_info=auth_info)
        raise exceptions.SysinvError(
            "Config out-of-date alarm did not appear or standby controller "
            "lock/unlock"
            "failed after oam-modify.")

    # Update system ssh client and global var
    fip_field = 'oam_if' if is_aio_simplex(con_ssh=con_ssh,
                                           auth_info=auth_info) else \
        'oam_floating_ip'
    new_lab = ProjVar.get_var('lab')
    if fip_field in kwargs:
        new_fip = kwargs[fip_field]
        con_ssh.update_host()
        new_lab['floating ip'] = new_fip
    if 'oam_c0_ip' in kwargs:
        new_lab['controller-0 ip'] = kwargs['oam_c0_ip']
    if 'oam_c1_ip' in kwargs:
        new_lab['controller-1 ip'] = kwargs['oam_c1_ip']
    ProjVar.set_var(LAB=new_lab)

    host_helper.lock_unlock_hosts(active, con_ssh=con_ssh, auth_info=auth_info)
    LOG.info("Wait for config out-of-date alarm to clear on system")
    wait_for_alarm_gone(alarm_id=EventLogID.CONFIG_OUT_OF_DATE, timeout=120,
                        auth_info=auth_info,
                        con_ssh=con_ssh)

    msg = "OAM IP(s) modified successfully."
    LOG.info(msg)
    return 0, msg


def modify_spectre_meltdown_version(version='spectre_meltdown_all',
                                    check_first=True, con_ssh=None,
                                    fail_ok=False,
                                    auth_info=Tenant.get('admin_platform')):
    """
    Modify spectre meltdown version
    Args:
        version (str): valid values: spectre_meltdown_v1, spectre_meltdown_all.
            Other values will be rejected by system modify cmd.
        check_first (bool):
        con_ssh:
        fail_ok (bool):
        auth_info

    Returns (tuple):
        (-1, "Security feature already set to <version>. Do nothing")
        (0, "System security_feature is successfully modified to: <version>")
        (1, <std_err>)

    """
    current_version = get_system_values(fields='security_feature')[0]
    if not current_version:
        skip('spectre_meltdown update feature is unavailable in current load')

    from keywords import host_helper
    hosts = get_hosts(con_ssh=con_ssh)
    check_val = 'nopti nospectre_v2'
    if check_first and version == current_version:
        LOG.info(
            "{} already set in 'system show'. Checking actual cmdline options "
            "on each host.".format(
                version))
        hosts_to_configure = []
        for host in hosts:
            cmdline_options = host_helper.get_host_cmdline_options(host=host)
            if 'v1' in version:
                if check_val not in cmdline_options:
                    hosts_to_configure.append(host)
            elif check_val in cmdline_options:
                hosts_to_configure.append(host)

        hosts = hosts_to_configure
        if not hosts_to_configure:
            msg = 'Security feature already set to {}. Do nothing.'.format(
                current_version)
            LOG.info(msg)
            return -1, msg

    LOG.info("Set spectre_meltdown version to {}".format(version))
    code, output = cli.system('modify -S {}'.format(version),
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, output

    conf_storage0 = False
    if 'storage-0' in hosts:
        hosts.remove('storage-0')
        conf_storage0 = True

    active_controller = get_active_controller_name(con_ssh=con_ssh,
                                                   auth_info=auth_info)
    conf_active = False
    if active_controller in hosts:
        hosts.remove(active_controller)
        conf_active = True

    if hosts:
        LOG.info(
            "Lock/unlock unconfigured hosts other than active controller: "
            "{}".format(hosts))
        try:
            for host in hosts:
                host_helper.lock_host(host=host, con_ssh=con_ssh,
                                      auth_info=auth_info)
        finally:
            host_helper.unlock_hosts(hosts=hosts, fail_ok=False,
                                     con_ssh=con_ssh, auth_info=auth_info)
            host_helper.wait_for_hosts_ready(hosts=hosts, con_ssh=con_ssh,
                                             auth_info=auth_info)

    if conf_storage0:
        LOG.info("Lock/unlock storage-0")
        try:
            host_helper.lock_host(host='storage-0', con_ssh=con_ssh,
                                  auth_info=auth_info)
        finally:
            host_helper.unlock_host(host='storage-0', con_ssh=con_ssh,
                                    auth_info=auth_info)

    if conf_active:
        LOG.info(
            "Lock/unlock active controller (swact first if needed): {}".format(
                active_controller))
        try:
            host_helper.lock_host(host=active_controller, swact=True,
                                  con_ssh=con_ssh, auth_info=auth_info)
        finally:
            host_helper.unlock_host(host=active_controller, con_ssh=con_ssh,
                                    auth_info=auth_info)

    LOG.info("Check 'system show' is updated to {}".format(version))
    post_version = \
        get_system_values(fields='security_feature', auth_info=auth_info)[0]
    assert version == post_version, 'Value is not {} after system ' \
                                    'modify'.format(version)

    LOG.info('Check cmdline options are updated on each host via /proc/cmdline')
    hosts.append(active_controller)
    for host in hosts:
        options = host_helper.get_host_cmdline_options(host=host)
        if 'v1' in version:
            assert check_val in options, '{} not in cmdline options after set' \
                                         ' to {}'.format(check_val, version)
        else:
            assert check_val not in options, '{} in cmdline options after set' \
                                             ' to {}'.format(check_val, version)

    msg = 'System spectre meltdown version is successfully modified to: ' \
          '{}'.format(version)
    LOG.info(msg)
    return 0, msg


def is_avs(con_ssh=None):
    vswitch_type = ProjVar.get_var('VSWITCH_TYPE')
    if vswitch_type is None:
        vswitch_type = get_system_values(fields='vswitch_type',
                                         con_ssh=con_ssh)[0]
        ProjVar.set_var(VSWITCH_TYPE=vswitch_type)
    return 'ovs' not in vswitch_type


def get_controller_uptime(con_ssh, auth_info=Tenant.get('admin_platform')):
    """
    Get uptime for all controllers. If no standby controller, then we only
    calculate for current active controller.
    Args:
        con_ssh
        auth_info

    Returns (int): in seconds
    """
    active_con, standby_con = get_active_standby_controllers(
        con_ssh=con_ssh, auth_info=auth_info)
    active_con_uptime = int(
        get_host_values(host=active_con, fields='uptime', con_ssh=con_ssh,
                        auth_info=auth_info)[0])

    con_uptime = active_con_uptime
    if standby_con:
        standby_con_uptime = int(
            get_host_values(host=standby_con, fields='uptime', con_ssh=con_ssh,
                            auth_info=auth_info)[0])
        con_uptime = min(active_con_uptime, standby_con_uptime)

    return con_uptime


def add_ml2_extension_drivers(drivers, auth_info=Tenant.get('admin_platform'),
                              con_ssh=None):
    """
    Add given ml2 extension drivers to helm charts override if they don't
    currently exist
    Args:
        drivers (str|list|tuple):
        auth_info:
        con_ssh:

    Returns (tuple):

    """
    return __update_ml2_extension_drivers(drivers=drivers, enable=True,
                                          auth_info=auth_info, con_ssh=con_ssh)


def remove_ml2_extension_drivers(drivers,
                                 auth_info=Tenant.get('admin_platform'),
                                 con_ssh=None):
    """
    Remove given ml2 extension drivers from helm charts override if they exist
    Args:
        drivers (str|list|tuple):
        auth_info:
        con_ssh:

    Returns (tuple):

    """
    return __update_ml2_extension_drivers(drivers=drivers, enable=False,
                                          auth_info=auth_info, con_ssh=con_ssh)


def __update_ml2_extension_drivers(drivers, enable=True,
                                   auth_info=Tenant.get('admin_platform'),
                                   con_ssh=None):
    """
    Add or remove ml2 extension drivers by updating helm charts user override

    Args:
        drivers (str|list|tuple):
        enable (bool): whether to enable or disable given ml2 extension
            driver(s)
        auth_info:
        con_ssh:

    Returns (tuple):

    """
    if isinstance(drivers, str):
        drivers = (drivers,)

    from keywords import container_helper
    known_drivers = ['port_security', 'qos', 'dns']
    all_drivers = known_drivers + [driver for driver in drivers if
                                   driver not in known_drivers]
    chart = 'neutron'

    LOG.info("Check existing ml2 extension_drivers")
    field = 'combined_overrides'
    combined_overrides = \
        container_helper.get_helm_override_values(chart, namespace='openstack',
                                                  fields=field)[0]
    current_drivers = combined_overrides['conf'].get('plugins', {}).get(
        'ml2_conf', {}).get('ml2', {}). \
        get('extension_drivers', '').split(sep=',')

    if enable:
        expt_drivers = set(current_drivers + list(drivers))
        # convert expt_drivers to ordered list by removing unwanted drivers
        # from ordered all_drivers list
        drivers_to_remove = set(all_drivers) - expt_drivers
        expt_drivers = [driver for driver in all_drivers if
                        driver not in drivers_to_remove]
    else:
        expt_drivers = [driver for driver in current_drivers if
                        driver not in drivers]

    if expt_drivers == current_drivers:
        LOG.info("ml2 extension drivers already set to {}. Do nothing.".format(
            expt_drivers))
        return -1, current_drivers

    path = 'conf.plugins.ml2_conf.ml2.extension_drivers'
    new_value = ','.join(expt_drivers)
    LOG.info("Update neutron helm-override: {}={}".format(path, new_value))
    if len(expt_drivers) <= 1:
        kw_args = {'kv_pairs': {path: new_value}}
    else:
        content = """
        conf:
          plugins:
            ml2_conf:
              ml2: 
                extension_drivers: {}
        """.format(new_value)
        yaml_file = os.path.join(HostLinuxUser.get_home(), 'ml2_drivers.yaml')
        if not con_ssh:
            con_ssh = ControllerClient.get_active_controller()
            con_ssh.exec_cmd('rm -f {}'.format(yaml_file), get_exit_code=False)
            con_ssh.exec_cmd("echo '{}' >> {}".format(content, yaml_file))
        kw_args = {'yaml_file': yaml_file}

    container_helper.update_helm_override(chart=chart, namespace='openstack',
                                          auth_info=auth_info, con_ssh=con_ssh,
                                          **kw_args)
    post_overrides = \
        container_helper.get_helm_override_values(chart, namespace='openstack',
                                                  fields=field)[0]
    post_drivers = post_overrides['conf'].get('plugins', {}).\
        get('ml2_conf', {}).get('ml2', {}).get('extension_drivers', '').\
        split(sep=',')

    if not post_drivers == expt_drivers:
        raise exceptions.SysinvError(
            "ml2 extension_drivers override is not reflected")

    LOG.info("Re-apply stx-openstack application")
    container_helper.apply_app(app_name='stx-openstack', applied_timeout=1200,
                               auth_info=auth_info, con_ssh=con_ssh)
    return 0, post_drivers


def get_ptp_values(fields='mode', rtn_dict=False, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get values from system ptp-show table.
    Args:
        fields (str|tuple|list):
        rtn_dict (bool): whether to return dict or list
        con_ssh:
        auth_info

    Returns (list|dict):

    """
    table_ = table_parser.table(
        cli.system('ptp-show', ssh_client=con_ssh, auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       rtn_dict=rtn_dict,
                                                       merge_lines=True)


def modify_ptp(enabled=None, mode=None, transport=None, mechanism=None,
               fail_ok=False, con_ssh=None, clear_alarm=True,
               wait_with_best_effort=False, check_first=True,
               auth_info=Tenant.get('admin_platform')):
    """
    Modify ptp with given parameters
    Args:
        enabled (bool|None):
        mode (str|None):
        transport (str|None):
        mechanism (str|None):
        fail_ok (bool):
        clear_alarm (bool):
        wait_with_best_effort (bool):
        check_first:
        auth_info (dict):
        con_ssh:

    Returns:

    """
    args_map = {
        'enabled': enabled,
        'mode': mode,
        'transport': transport,
        'mechanism': mechanism,
    }

    args_dict = {}
    for key, val in args_map.items():
        if val is not None:
            args_dict[key] = str(val)

    if not args_dict:
        raise ValueError("At least one parameter has to be specified.")

    arg_str = ' '.join(['--{} {}'.format(k, v) for k, v in args_dict.items()])

    if check_first:
        actual_val_list = get_ptp_values(fields=list(args_dict.keys()),
                                         con_ssh=con_ssh, rtn_dict=True,
                                         auth_info=auth_info)
        changeparm = False
        for field in args_dict:
            param_val = args_dict[field]
            actual_val = actual_val_list[field]
            if actual_val != param_val:
                changeparm = True
                break
        if not changeparm:
            return -1, 'No parameter chage'

    code, output = cli.system('ptp-modify', arg_str, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    if clear_alarm:
        wait_and_clear_config_out_of_date_alarms(
            host_type='controller',
            wait_with_best_effort=wait_with_best_effort,
            con_ssh=con_ssh,
            auth_info=auth_info)

    post_args = get_ptp_values(fields=list(args_dict.keys()), con_ssh=con_ssh,
                               rtn_dict=True, auth_info=auth_info)
    for field in args_dict:
        expt_val = args_dict[field]
        actual_val = post_args[field]
        if actual_val != expt_val:
            raise exceptions.SysinvError(
                "{} in ptp-show is not as expected after modify. Expt: {}; "
                "actual: {}".
                format(field, expt_val, actual_val))

    msg = 'ptp modified successfully. {}'.format(
        'Alarm not cleared yet.' if not clear_alarm else '')
    return 0, msg


def get_ntp_values(fields='ntpservers', rtn_dict=False, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get values from system ntp-show table.
    Args:
        fields (str|tuple|list):
        rtn_dict (bool)
        con_ssh:
        auth_info

    Returns (list|dict):

    """
    table_ = table_parser.table(
        cli.system('ntp-show', ssh_client=con_ssh, auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       rtn_dict=rtn_dict)


def get_ntp_servers(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Get ntp servers via system ntp-show
    Args:
        con_ssh:
        auth_info:

    Returns (list):

    """
    ntp_servers = get_ntp_values(fields='ntpservers', rtn_dict=False,
                                 con_ssh=con_ssh, auth_info=auth_info)
    ntp_servers = ntp_servers[0].split(',')
    return ntp_servers


def modify_ntp(enabled=None, ntp_servers=None, check_first=True, fail_ok=False,
               clear_alarm=True,
               wait_with_best_effort=False, con_ssh=None,
               auth_info=Tenant.get('admin_platform'), **kwargs):
    """

    Args:
        enabled (bool|None):
        ntp_servers (str|None|list|tuple):
        check_first (bool)
        fail_ok (bool)
        clear_alarm (bool): Whether to wait and lock/unlock hosts to clear alarm
        wait_with_best_effort (bool): whether to wait for alarm with best
        effort only
        con_ssh:
        check_first:
        auth_info:
        **kwargs

    Returns (tuple):
        (0, <success_msg>)
        (1, <std_err>)      # cli rejected

    """
    arg = ''
    verify_args = {}
    if enabled is not None:
        arg += '--enabled {}'.format(enabled).lower()
        verify_args['enabled'] = str(enabled)

    if ntp_servers:
        if isinstance(ntp_servers, (tuple, list)):
            ntp_servers = ','.join(ntp_servers)
        arg += ' ntpservers="{}"'.format(ntp_servers)
        verify_args['ntpservers'] = ntp_servers

    if kwargs:
        for k, v in kwargs.items():
            arg += ' {}={}'.format(k, v)
            verify_args[k] = v

    if not arg:
        raise ValueError(
            "Nothing to modify. enable, ntp_servers or kwwargs has to be "
            "provided")

    prev_args = None
    toggle_state = False
    if enabled is not None:
        prev_args = get_ntp_values(fields=list(verify_args.keys()),
                                   con_ssh=con_ssh, rtn_dict=True,
                                   auth_info=auth_info)
        if prev_args['enabled'] != verify_args['enabled']:
            toggle_state = True

    if check_first and not toggle_state:
        if not clear_alarm or (clear_alarm and not get_alarms(
                alarm_id=EventLogID.CONFIG_OUT_OF_DATE, con_ssh=con_ssh,
                entity_id='controller', auth_info=auth_info)):
            if not prev_args:
                prev_args = get_ntp_values(fields=list(verify_args.keys()),
                                           con_ssh=con_ssh, rtn_dict=True,
                                           auth_info=auth_info)

            for field in verify_args:
                expt_val = verify_args[field]
                actual_val = prev_args[field]
                if actual_val != expt_val:
                    break
            else:
                msg = 'NTP already configured with given criteria {}. Do ' \
                      'nothing.'.format(verify_args)
                LOG.info(msg)
                return -1, msg

    code, out = cli.system('ntp-modify', arg.strip(), ssh_client=con_ssh,
                           fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, out

    if clear_alarm:
        # config out-of-date alarm only on controller if only ntp servers are
        # changed.
        # If ntp state changes, ALL hosts need to be lock/unlock.
        host_type = None if toggle_state else 'controller'
        wait_and_clear_config_out_of_date_alarms(
            host_type=host_type,
            con_ssh=con_ssh,
            auth_info=auth_info,
            wait_with_best_effort=wait_with_best_effort)

    post_args = get_ntp_values(fields=list(verify_args.keys()), con_ssh=con_ssh,
                               rtn_dict=True, auth_info=auth_info)
    for field in verify_args:
        expt_val = verify_args[field]
        actual_val = post_args[field]
        if actual_val != expt_val:
            raise exceptions.SysinvError(
                "{} in ntp-show is not as expected after modify. Expt: {}; "
                "actual: {}".
                format(field, expt_val, actual_val))

    msg = 'ntp modified successfully. {}'.format(
        'Alarm not cleared yet.' if not clear_alarm else '')
    return 0, msg


def wait_and_clear_config_out_of_date_alarms(
        hosts=None, host_type=None, lock_unlock=True, wait_timeout=60,
        wait_with_best_effort=False, clear_timeout=60, con_ssh=None,
        auth_info=Tenant.get('admin_platform')):
    """
    Wait for config out-of-date alarms on given hosts and (lock/unlock and)
    wait for clear
    Args:
        hosts:
        host_type (str|list|tuple): valid types: controller, compute, storage
        lock_unlock (bool)
        wait_timeout (int)
        wait_with_best_effort (bool):
        clear_timeout (int)
        con_ssh:
        auth_info

    Returns:

    """
    from keywords.host_helper import lock_unlock_hosts

    if not hosts:
        if not host_type:
            host_type = ('controller', 'compute', 'storage')
        elif isinstance(host_type, str):
            host_type = (host_type,)

        avail_states = (HostAvailState.DEGRADED, HostAvailState.AVAILABLE,
                        HostAvailState.ONLINE)
        hosts_per_type = get_hosts_per_personality(availability=avail_states,
                                                   con_ssh=con_ssh,
                                                   auth_info=auth_info)

        # host_groups: ordered list for controller, compute, storage hosts
        host_groups = [hosts_per_type[type_] for type_ in host_type if
                       hosts_per_type[type_]]
        if not host_groups:
            raise exceptions.HostError(
                "No valid hosts found for host_type: {}".format(host_type))

    else:
        if isinstance(hosts, str):
            hosts = [hosts]
        host_groups = [hosts]

    hosts_out_of_date = []
    all_hosts = []
    for hosts_ in host_groups:
        LOG.info(
            "Wait for config out-of-date alarms for {} with best effort".format(
                hosts_))
        all_hosts += hosts_
        if wait_for_alarm(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                          entity_id=hosts_, timeout=wait_timeout,
                          con_ssh=con_ssh, fail_ok=True,
                          auth_info=auth_info)[0]:
            hosts_out_of_date += hosts_

    hosts_out_of_date = list(set(hosts_out_of_date))
    all_hosts = list(set(all_hosts))
    LOG.info("Config out-of-date hosts: {}".format(hosts_out_of_date))
    if hosts_out_of_date:
        if lock_unlock:
            LOG.info(
                "Wait for 60 seconds, then lock/unlock config out-of-date "
                "hosts: {}".format(hosts_out_of_date))
            time.sleep(60)
            lock_unlock_hosts(hosts_out_of_date, con_ssh=con_ssh,
                              auth_info=auth_info)

        LOG.info("Wait for config out-of-date alarm to clear on system")
        wait_for_alarm_gone(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                            timeout=clear_timeout, auth_info=auth_info,
                            con_ssh=con_ssh)

    if not wait_with_best_effort and all_hosts != hosts_out_of_date:
        raise exceptions.SysinvError(
            "Expect config out of date: {}; actual: {}".format(
                all_hosts, hosts_out_of_date))


def get_timezone(auth_info=Tenant.get('admin_platform'), con_ssh=None):
    return get_system_values(fields='timezone', auth_info=auth_info,
                             con_ssh=con_ssh)[0]


def modify_timezone(timezone, check_first=True, fail_ok=False, clear_alarm=True,
                    auth_info=Tenant.get('admin_platform'),
                    con_ssh=None):
    """
    Modify timezone to given zone
    Args:
        timezone:
        check_first:
        fail_ok:
        clear_alarm:
        auth_info:
        con_ssh:

    Returns (tuple):

    """
    if check_first:
        current_timezone = get_timezone(auth_info=auth_info, con_ssh=con_ssh)
        if current_timezone == timezone:
            msg = "Timezone is already set to {}. Do nothing.".format(timezone)
            LOG.info(msg)
            return -1, msg

    LOG.info("Modifying Timezone to {}".format(timezone))
    code, out = modify_system(fail_ok=fail_ok, auth_info=auth_info,
                              con_ssh=con_ssh, timezone=timezone)
    if code > 0:
        return 1, out

    if clear_alarm:
        if wait_for_alarm(alarm_id=EventLogID.CONFIG_OUT_OF_DATE, timeout=30,
                          con_ssh=con_ssh, fail_ok=True,
                          auth_info=auth_info)[0]:
            wait_for_alarm_gone(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                                timeout=180, con_ssh=con_ssh,
                                auth_info=auth_info)

    time.sleep(10)
    post_timezone = get_timezone(auth_info=auth_info, con_ssh=con_ssh)
    if post_timezone != timezone:
        msg = 'Timezone is {} instead of {} after modify'.format(post_timezone,
                                                                 timezone)
        if fail_ok:
            LOG.warning(msg)
            return 2, post_timezone

        raise exceptions.SysinvError(msg)

    LOG.info("Timezone is successfully modified to {}".format(timezone))
    return 0, timezone


def create_data_network(name, net_type='vlan', mode=None, mtu=None,
                        port_num=None, multicast_group=None, ttl=None,
                        description=None, field='uuid', fail_ok=False,
                        con_ssh=None,
                        auth_info=Tenant.get('admin_platform'), cleanup=None):
    """
    Add a datanetwork
    Args:
        name (str):
        net_type (str): vlan, vxlan or flat
        mode (None|str|None):
        mtu (int|str|None):
        port_num (int|str|None):
        multicast_group (str|None):
        ttl (int|str|None):
        description (str|None):
        field (str): uuid or name
        fail_ok:
        con_ssh:
        auth_info:
        cleanup (str|None): function, class, module or session

    Returns (tuple):
        (0, <datanetwork>)
        (1, <std_err>)

    """
    args_dict = {
        'description': description,
        'mtu': mtu,
        'port_num': port_num,
        'multicast_group': multicast_group,
        'ttl': ttl,
        'mode': mode,
    }
    args = '{} {} {}'.format(common.parse_args(args_dict), name, net_type)
    code, output = cli.system('datanetwork-add', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    table_ = table_parser.table(output)
    LOG.info("data network {} is created successfully".format(name))

    if cleanup:
        uuid = table_parser.get_value_two_col_table(table_, field='uuid')
        ResourceCleanup.add('datanetwork', uuid, scope=cleanup)

    return 0, table_parser.get_value_two_col_table(table_, field)


def get_data_networks(field='name', con_ssh=None,
                      auth_info=Tenant.get('admin_platform'), strict=True,
                      **kwargs):
    """
    Get values from system datanetwork-list
    Args:
        field (str|tuple|list):
        con_ssh:
        auth_info:
        strict:
        **kwargs:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('datanetwork-list', ssh_client=con_ssh, auth_info=auth_info)[
            1])
    return table_parser.get_multi_values(table_, fields=field, strict=strict,
                                         **kwargs)


def get_data_network_values(datanetwork, fields=('uuid',), fail_ok=False,
                            con_ssh=None,
                            auth_info=Tenant.get('admin_platform')):
    """
    Get datanetwork values from system datanetwork-show table.
    Args:
        datanetwork (str): name or uuid of datanetwork
        fields (str|tuple|list):
        fail_ok:
        con_ssh:
        auth_info:

    Returns (list|None): values for given fields. None if cli is rejected.

    """
    code, output = cli.system('datanetwork-show', datanetwork,
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return None

    table_ = table_parser.table(output)
    return table_parser.get_multi_values_two_col_table(table_=table_,
                                                       fields=fields)


def delete_data_network(datanetwork_uuid, fail_ok=False, con_ssh=None,
                        auth_info=Tenant.get('admin_platform')):
    """
    Delete given datanetwork
    Args:
        datanetwork_uuid (str):
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):
        (0, "datanetwork <uuid> deleted successfully")
        (1, <std_err>)
        (2, "datanetwork <uuid> still exists after deletion")

    """
    code, output = cli.system('datanetwork-delete', datanetwork_uuid,
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, output

    if get_data_network_values(datanetwork=datanetwork_uuid, con_ssh=con_ssh,
                               auth_info=auth_info, fail_ok=True):
        err = 'datanetwork {} still exists after deletion'.format(
            datanetwork_uuid)
        LOG.warning(err)
        if fail_ok:
            return 2, err
        else:
            raise exceptions.SysinvError(err)

    msg = 'datanetwork {} deleted successfully'.format(datanetwork_uuid)
    LOG.info(msg)
    return 0, msg


def get_addr_pools(field, name=None, uuid=None, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get values from system addrpool-list
    Args:
        field (str|list|tuple):
        name:
        uuid:
        con_ssh:
        auth_info:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('addrpool-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    kwargs = {'name': name, 'uuid': uuid}
    return table_parser.get_multi_values(table_=table_, fields=field,
                                         **{k: v for k, v in kwargs.items()})


def get_addr_pool_values(fields, addr_pool=None, network_type=None,
                         con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Get values from system addrpool-show
    Args:
        fields (str|tuple|list):
        addr_pool:
        network_type:
        con_ssh:
        auth_info:

    Returns (list):

    """
    if not addr_pool and not network_type:
        raise ValueError('addr_pool uuid or network_type has to be provided')

    if not addr_pool:
        addr_pool = \
            get_system_networks(field='pool_uuid', net_type=network_type,
                                con_ssh=con_ssh, auth_info=auth_info)[0]
        if not addr_pool:
            raise exceptions.SysinvError(
                "No pool_uuid found for network type {}".format(network_type))

    table_ = table_parser.table(
        cli.system('addrpool-show', addr_pool, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields=fields)


def get_system_network_cidr(network_type, con_ssh=None,
                            auth_info=Tenant.get('admin_platform')):
    """
    Get cidr for given network type, such as mgmt, oam, cluster-host, etc.
    Args:
        network_type:
        con_ssh:
        auth_info:

    Returns (str):

    """
    network, prefix = get_addr_pool_values(fields=('network', 'prefix'),
                                           network_type=network_type,
                                           con_ssh=con_ssh,
                                           auth_info=auth_info)

    return '{}/{}'.format(network, prefix)


def get_host_values(host, fields, rtn_dict=False, merge_lines=True,
                    auth_info=Tenant.get('admin_platform'),
                    con_ssh=None):
    """
    Get values from system host-show
    Args:
        host (str):
        fields (str|list|tuple):
        rtn_dict:
        merge_lines
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('host-show', host, ssh_client=con_ssh, auth_info=auth_info)[
            1],
        combine_multiline_entry=merge_lines)
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       rtn_dict=rtn_dict,
                                                       evaluate=True)


def get_hosts_values(hosts, fields, merge_lines=False, rtn_dict_per_host=True,
                     con_ssh=None,
                     auth_info=Tenant.get('admin_platform')):
    """
    Get values for multiple hosts via system host-show
    Args:
        hosts:
        fields:
        merge_lines:
        rtn_dict_per_host:
        con_ssh:
        auth_info:

    Returns (dict):
        e.g., {'controller-0': {'task': booting, 'subfunctions': ...},
               'controller-1':...}

    """
    if isinstance(fields, str):
        fields = [fields]

    states_vals = {}
    for host in hosts:
        vals = get_host_values(host, fields, merge_lines=merge_lines,
                               con_ssh=con_ssh,
                               rtn_dict=rtn_dict_per_host, auth_info=auth_info)
        states_vals[host] = vals

    return states_vals


def get_ntpq_status(host, mgmt_cidr=None, con_ssh=None,
                    auth_info=Tenant.get('admin_platform')):
    """
    Get ntp status via 'sudo ntpq -pn'

    Args:
        host (str): host to check
        mgmt_cidr (str): internal management ip from peer host
        con_ssh (SSHClient)
        auth_info

    Returns(tuple): (<code>, <msg>)
        - (0, "<host> NTPQ is in healthy state")
        - (1, "No NTP server selected")
        - (2, "Some NTP servers are discarded")

    """
    if not mgmt_cidr:
        mgmt_cidr = get_system_network_cidr('mgmt', con_ssh=con_ssh,
                                            auth_info=auth_info)

    cmd = 'ntpq -pn'
    from keywords import host_helper
    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        output = host_ssh.exec_sudo_cmd(cmd, fail_ok=False)[1]

    output_lines = output.splitlines()
    server_lines = list(output_lines)
    for line in output_lines:
        server_lines.remove(line)
        if '======' in line:
            break

    selected = None
    discarded = []
    for server_line in server_lines:
        try:
            # Check if its an internal mgmt net ip
            if ipaddress.ip_address(server_line[1:]) in ipaddress.ip_network(
                    mgmt_cidr):
                continue
        except ValueError:
            pass

        if server_line.startswith('*'):
            selected = server_line
        elif server_line.startswith('-') or server_line.startswith(
                'x') or server_line.startswith(' '):
            discarded.append(server_line)

    if not selected:
        return 1, "No NTP server selected"

    if discarded:
        return 2, "Some NTP servers are discarded"

    return 0, "{} NTPQ is in healthy state".format(host)


def wait_for_ntp_sync(host, timeout=MiscTimeout.NTPQ_UPDATE, fail_ok=False,
                      con_ssh=None,
                      auth_info=Tenant.get('admin_platform')):
    """
    Wait for ntp alarm inline with sudo ntpq output.
    Args:
        host:
        timeout:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (bool):

    """

    LOG.info("Waiting for ntp alarm to clear or sudo ntpq -pn indicate "
             "unhealthy server for {}".format(host))
    end_time = time.time() + timeout
    msg = ntp_alarms = None
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    mgmt_cidr = get_system_network_cidr('mgmt', con_ssh=con_ssh,
                                        auth_info=auth_info)
    while time.time() < end_time:
        ntp_alarms = get_alarms(alarm_id=EventLogID.NTP_ALARM, entity_id=host,
                                strict=False,
                                con_ssh=con_ssh, auth_info=auth_info)
        status, msg = get_ntpq_status(host, mgmt_cidr=mgmt_cidr,
                                      con_ssh=con_ssh, auth_info=auth_info)
        if ntp_alarms and status != 0:
            LOG.info("Valid NTP alarm")
            return True
        elif not ntp_alarms and status == 0:
            LOG.info("NTP alarm cleared and sudo ntpq shows servers healthy")
            return True

        LOG.info("NTPQ status: {}; NTP alarms: {}".format(msg, ntp_alarms))
        time.sleep(30)

    err_msg = "Timed out waiting for NTP alarm to be in sync with ntpq " \
              "output. NTPQ status: {}; NTP alarms: {}".format(msg, ntp_alarms)
    if fail_ok:
        LOG.warning(err_msg)
        return False

    raise exceptions.HostTimeout(err_msg)


def __hosts_stay_in_states(hosts, duration=10, con_ssh=None,
                           auth_info=Tenant.get('admin_platform'),
                           **states):
    """
    Check if hosts stay in specified state(s) for given duration.

    Args:
        hosts (list|str): hostname(s)
        duration (int): duration to check for in seconds
        con_ssh (SSHClient):
        **states: such as availability=[online, available]

    Returns:
        bool: True if host stayed in specified states for given duration;
            False if host is not in specified states
            anytime in the duration.

    """
    end_time = time.time() + duration
    while time.time() < end_time:
        if not __hosts_in_states(hosts=hosts, con_ssh=con_ssh,
                                 auth_info=auth_info, **states):
            return False
        time.sleep(1)

    return True


def wait_for_hosts_states(hosts, timeout=HostTimeout.REBOOT, check_interval=5,
                          duration=3, con_ssh=None,
                          fail_ok=True, auth_info=Tenant.get('admin_platform'),
                          **states):
    """
    Wait for hosts to go in specified states via system host-list

    Args:
        hosts (str|list):
        timeout (int):
        check_interval (int):
        duration (int): wait for a host to be in given state(s) for at
            least <duration> seconds
        con_ssh (SSHClient):
        fail_ok (bool)
        auth_info
        **states: such as availability=[online, available]

    Returns (bool): True if host reaches specified states within timeout,
        and stays in states for given duration; False otherwise

    """
    if not hosts:
        raise ValueError("No host(s) provided to wait for states.")

    if isinstance(hosts, str):
        hosts = [hosts]
    for key, value in states.items():
        if isinstance(value, str):
            value = [value]
            states[key] = value

    LOG.info("Waiting for {} to reach state(s): {}...".format(hosts, states))
    end_time = time.time() + timeout
    while time.time() < end_time:
        if __hosts_stay_in_states(hosts, con_ssh=con_ssh,
                                  duration=duration, auth_info=auth_info,
                                  **states):
            LOG.info("{} have reached state(s): {}".format(hosts, states))
            return True
        time.sleep(check_interval)
    else:
        msg = "Timed out waiting for {} in state(s) - {}".format(hosts, states)
        if fail_ok:
            LOG.warning(msg)
            return False
        raise exceptions.HostTimeout(msg)


def __hosts_in_states(hosts, con_ssh=None,
                      auth_info=Tenant.get('admin_platform'),
                      **states):
    actual_values = get_hosts(hostname=hosts, field=list(states.keys()),
                              con_ssh=con_ssh,
                              auth_info=auth_info, rtn_dict=True)
    for field, expt_values in states.items():
        actual_states = actual_values[field]
        for actual_state in actual_states:
            if actual_state not in expt_values:
                LOG.debug("At least one host from {} has {} state(s) in {} "
                          "instead of {}".format(hosts, field, actual_state,
                                                 expt_values))
                return False

    return True


def wait_for_host_values(host, timeout=HostTimeout.REBOOT, check_interval=3,
                         strict=True, regex=False, fail_ok=True,
                         con_ssh=None, auth_info=Tenant.get('admin_platform'),
                         **kwargs):
    """
    Wait for host values via system host-show
    Args:
        host:
        timeout:
        check_interval:
        strict:
        regex:
        fail_ok:
        con_ssh:
        auth_info
        **kwargs: key/value pair to wait for.

    Returns:

    """
    if not kwargs:
        raise ValueError(
            "Expected host state(s) has to be specified via "
            "keyword argument states")

    LOG.info("Waiting for {} to reach state(s) - {}".format(host, kwargs))
    end_time = time.time() + timeout
    last_vals = {}
    for field in kwargs:
        last_vals[field] = None

    while time.time() < end_time:
        actual_vals = get_host_values(host, fields=list(kwargs.keys()),
                                      con_ssh=con_ssh, rtn_dict=True,
                                      auth_info=auth_info, merge_lines=False)
        for field, expt_vals in kwargs.items():
            actual_val = actual_vals[field]
            if isinstance(actual_val, list):
                actual_val = ' '.join(actual_val)

            actual_val_lower = actual_val.lower()
            if isinstance(expt_vals, str):
                expt_vals = [expt_vals]

            for expected_val in expt_vals:
                expected_val_lower = expected_val.strip().lower()
                found_match = False
                if regex:
                    if strict:
                        res_ = re.match(expected_val_lower, actual_val_lower)
                    else:
                        res_ = re.search(expected_val_lower, actual_val_lower)
                    if res_:
                        found_match = True
                else:
                    if strict:
                        found_match = actual_val_lower == expected_val_lower
                    else:
                        found_match = actual_val_lower in expected_val_lower

                if found_match:
                    LOG.info(
                        "{} {} has reached: {}".format(host, field, actual_val))
                    break
            else:  # no match found. run system host-show again
                if last_vals[field] != actual_val_lower:
                    LOG.info("{} {} is {}.".format(host, field, actual_val))
                    last_vals[field] = actual_val_lower
                break
        else:
            LOG.info("{} is in state(s): {}".format(host, kwargs))
            return True
        time.sleep(check_interval)
    else:
        msg = "{} did not reach state(s) within {}s - {}".format(host, timeout,
                                                                 kwargs)
        if fail_ok:
            LOG.warning(msg)
            return False
        raise exceptions.TimeoutException(msg)


def is_active_controller(host, con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    personality = get_host_values(host, fields='capabilities',
                                  auth_info=auth_info,
                                  merge_lines=True,
                                  con_ssh=con_ssh)[0].get('Personality', '')
    return personality.lower() == 'Controller-Active'.lower()


def is_lowlatency_host(host):
    subfuncs = get_host_values(host=host, fields='subfunctions')[0]
    return 'lowlatency' in subfuncs
