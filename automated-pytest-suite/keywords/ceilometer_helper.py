#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from consts.auth import Tenant
from utils import table_parser, cli
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG


def get_alarms(header='alarm_id', name=None, strict=False,
               auth_info=Tenant.get('admin'), con_ssh=None):
    """

    Args:
        header
        name:
        strict:
        auth_info:
        con_ssh:

    Returns:

    """

    table_ = table_parser.table(cli.openstack('alarm list',
                                              ssh_client=con_ssh,
                                              auth_info=auth_info)[1],
                                combine_multiline_entry=True)
    if name is None:
        return table_parser.get_column(table_, header)

    return table_parser.get_values(table_, header, Name=name, strict=strict)


def get_events(event_type, limit=None, header='message_id', con_ssh=None,
               auth_info=None, **filters):
    """

    Args:
        event_type:
        limit
        header:
        con_ssh:
        auth_info:

    Returns:

    """
    args = ''
    if limit:
        args = '--limit {}'.format(limit)

    if event_type or filters:
        if event_type:
            filters['event_type'] = event_type

        extra_args = ['{}={}'.format(k, v) for k, v in filters.items()]
        args += ' --filter {}'.format(';'.join(extra_args))

    table_ = table_parser.table(cli.openstack('event list', args,
                                              ssh_client=con_ssh,
                                              auth_info=auth_info)[1])
    return table_parser.get_values(table_, header)
