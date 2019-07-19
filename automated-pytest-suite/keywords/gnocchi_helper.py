#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from utils import cli
from utils import table_parser
from utils.tis_log import LOG

from consts.auth import Tenant
from keywords import common


def get_aggregated_measures(field='value', resource_type=None, metrics=None,
                            start=None, stop=None, overlap=None,
                            refresh=None, resource_ids=None, extra_query=None,
                            fail_ok=False, auth_info=Tenant.get('admin'),
                            con_ssh=None):
    """
    Get measurements via 'openstack metric measures aggregation'
    Args:
        field (str): header of a column
        resource_type (str|None):  used in --resource-type <resource_type>
        metrics (str|list|tuple|None): used in --metric <metric1> [metric2 ...]
        start (str|None): used in --start <start>
        stop (str|None): used in --stop <stop>
        refresh (bool): used in --refresh
        overlap (str|None): overlap percentage. used in
            --needed-overlap <overlap>
        resource_ids (str|list|tuple|None): used in --query "id=<resource_id1>[
            or id=<resource_id2> ...]"
        extra_query (str|None): used in --query <extra_query>
        fail_ok:
        auth_info:
        con_ssh:

    Returns (list): list of strings

    """
    LOG.info("Getting aggregated measurements...")
    args_dict = {
        'resource-type': resource_type,
        'metric': metrics,
        'start': start,
        'stop': stop,
        'needed-overlap': overlap,
        'refresh': refresh,
    }

    args = common.parse_args(args_dict, vals_sep=' ')
    query_str = ''
    if resource_ids:
        if isinstance(resource_ids, str):
            resource_ids = [resource_ids]
        resource_ids = ['id={}'.format(val) for val in resource_ids]
        query_str = ' or '.join(resource_ids)

    if extra_query:
        if resource_ids:
            query_str += ' and '
        query_str += '{}'.format(extra_query)

    if query_str:
        args += ' --query "{}"'.format(query_str)

    code, out = cli.openstack('metric measures aggregation', args,
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, out

    table_ = table_parser.table(out)
    return 0, table_parser.get_values(table_, field)


def get_metric_values(metric_id=None, metric_name=None, resource_id=None,
                      fields='id', fail_ok=False,
                      auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get metric info via 'openstack metric show'
    Args:
        metric_id (str|None):
        metric_name (str|None): Only used if metric_id is not provided
        resource_id (str|None):  Only used if metric_id is not provided
        fields (str|list|tuple): field name
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (list):

    """
    if metric_id is None and metric_name is None:
        raise ValueError("metric_id or metric_name has to be provided.")

    if metric_id:
        arg = metric_id
    else:
        if resource_id:
            arg = '--resource-id {} "{}"'.format(resource_id, metric_name)
        else:
            if not fail_ok:
                raise ValueError("resource_id needs to be provided when using "
                                 "metric_name")
            arg = '"{}"'.format(metric_name)

    code, output = cli.openstack('openstack metric show', arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return output

    table_ = table_parser.table(output)
    return table_parser.get_multi_values_two_col_table(table_, fields)


def get_metrics(field='id', metric_name=None, resource_id=None, fail_ok=True,
                auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get metrics values via 'openstack metric list'
    Args:
        field (str|list|tuple): header of the metric list table
        metric_name (str|None):
        resource_id (str|None):
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (list): list of strings

    """
    columns = ['id', 'archive_policy/name', 'name', 'unit', 'resource_id']
    arg = '-f value '
    arg += ' '.join(['-c {}'.format(column) for column in columns])

    grep_str = ''
    if resource_id:
        grep_str += ' | grep --color=never -E -i {}'.format(resource_id)
    if metric_name:
        grep_str += ' | grep --color=never -E -i {}'.format(metric_name)

    arg += grep_str

    code, output = cli.openstack('metric list', arg, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return []

    values = []
    convert = False
    if isinstance(field, str):
        field = (field, )
        convert = True

    for header in field:
        lines = output.splitlines()
        index = columns.index(header.lower())
        vals = [line.split(sep=' ')[index] for line in lines]
        values.append(vals)

    if convert:
        values = values[0]
    return values
