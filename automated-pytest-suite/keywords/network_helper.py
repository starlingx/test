#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import ipaddress
import math
import re
import os
import time
from collections import Counter
from contextlib import contextmanager

import pexpect

from consts.auth import Tenant, HostLinuxUser
from consts.filepaths import UserData
from consts.stx import Networks, PING_LOSS_RATE, MELLANOX4, \
    VSHELL_PING_LOSS_RATE, DevClassID, UUID
from consts.proj_vars import ProjVar
from consts.timeout import VMTimeout
from keywords import common, keystone_helper, host_helper, system_helper
from testfixtures.fixture_resources import ResourceCleanup
from utils import table_parser, cli, exceptions
from utils.clients.ssh import NATBoxClient, get_cli_client, ControllerClient
from utils.tis_log import LOG


def is_valid_ip_address(ip=None):
    """
    Validate the input IP address

    Args:
        ip:  IPv4 or IPv6 address

    Returns:
        True: valid IPv4 or IPv6 address
        False: otherwise
    """
    return bool(get_ip_address_str(ip))


def get_ip_address_str(ip=None):
    """
    Get the representation of the input IP address

    Args:
        ip:  IPv4 or IPv6 address

    Returns:
        str: string representation of the input IP address if it's valid
        None: otherwise
    """
    try:
        ipaddr = ipaddress.ip_address(ip)
        return str(ipaddr)
    except ValueError:
        # invalid IPv4 or IPv6 address
        return None


def create_network(name=None, shared=None, project=None, network_type=None,
                   segmentation_id=None, qos=None,
                   physical_network=None, vlan_transparent=None,
                   port_security=None, avail_zone=None, external=None,
                   default=None, tags=None, fail_ok=False, auth_info=None,
                   con_ssh=None, cleanup=None):
    """
    Create a network for given tenant

    Args:
        name (str): name of the network
        shared (bool)
        project: such as tenant1, tenant2.
        network_type (str): The physical mechanism by which the virtual
            network is implemented
        segmentation_id (None|str): w VLAN ID for VLAN networks
        qos
        physical_network (str): Name of the physical network over which the
            virtual network is implemented
        vlan_transparent(None|bool): Create a VLAN transparent network
        port_security (None|bool)
        avail_zone (None|str)
        external (None|bool)
        default (None|bool): applicable only if external=True.
        tags (None|False|str|list|tuple)
        fail_ok (bool):
        auth_info (dict): run 'openstack network create' cli using these
        authorization info
        con_ssh (SSHClient):
        cleanup (str|None): function, module, class, session or None

    Returns (tuple): (rnt_code (int), net_id (str), message (str))

    """
    if name is None:
        name = common.get_unique_name(name_str='net')

    args = name
    if project is not None:
        tenant_id = keystone_helper.get_projects(field='ID', name=project,
                                                 con_ssh=con_ssh)[0]
        args += ' --project ' + tenant_id

    if shared is not None:
        args += ' --share' if shared else ' --no-share'
    if vlan_transparent is not None:
        args += ' --transparent-vlan' if vlan_transparent else \
            ' --no-transparent-vlan'
    if port_security is not None:
        args += ' --enable-port-security' if port_security else \
            ' --disable-port-security'

    if external:
        args += ' --external'
        if default is not None:
            args += ' --default' if default else ' --no-default'
    elif external is False:
        args += ' --internal'

    if tags is False:
        args += ' --no-tag'
    elif tags:
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            args += ' --tag ' + tag

    if segmentation_id:
        args += ' --provider:segmentation_id ' + segmentation_id
    if network_type:
        args += ' --provider:network_type ' + network_type
    if physical_network:
        args += ' --provider:physical_network ' + physical_network
    if avail_zone:
        args += ' --availability-zone-hint ' + avail_zone
    if qos:
        args += ' --wrs-tm:qos ' + qos

    LOG.info("Creating network: Args: {}".format(args))
    code, output = cli.openstack('network create', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    table_ = table_parser.table(output)
    net_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup and net_id:
        ResourceCleanup.add('network', net_id, scope=cleanup)

    if code == 1:
        return 1, output

    succ_msg = "Network {} is successfully created".format(net_id)
    LOG.info(succ_msg)
    return 0, net_id


def create_subnet(network, name=None, subnet_range=None, gateway=None,
                  dhcp=None, dns_servers=None,
                  allocation_pools=None, ip_version=None, subnet_pool=None,
                  use_default_subnet_pool=None,
                  project=None, project_domain=None, prefix_length=None,
                  description=None, host_routes=None,
                  ipv6_ra_mode=None, ipv6_addr_mode=None, network_segment=None,
                  service_types=None,
                  tags=None, no_tag=None, fail_ok=False, auth_info=None,
                  con_ssh=None, cleanup=None):
    """
    Create a subnet with given parameters

    Args:
        network (str): id of the network to create subnet for
        name (str|None): name of the subnet
        subnet_range (str|None): such as "192.168.3.0/24"
        project (str|None): such as tenant1, tenant2.
        project_domain (str|None)
        gateway (str): Valid values: <ip address>, auto, none
        dhcp (bool): whether or not to enable DHCP
        dns_servers (list|tuple|str|None): DNS name servers. e.g.,
            ["147.11.57.133", "128.224.144.130", "147.11.57.128"]
        allocation_pools (list|dict|None): {'start': <start_ip>, 'end':
        'end_ip'}
        ip_version (int|str|None): 4, or 6
        subnet_pool (str|None): ID or name of subnetpool from which this
        subnet will obtain a CIDR.
        use_default_subnet_pool (bool|None)
        prefix_length (str|None)
        description (str|None)
        host_routes (str|None)
        ipv6_addr_mode (str|None)
        ipv6_ra_mode (str|None)
        network_segment (str|None)
        service_types (list|tuple|str|None)
        tags (list|tuple|str|None)
        no_tag (bool|None)
        fail_ok (bool):
        auth_info (dict): run the neutron subnet-create cli using these
        authorization info
        con_ssh (SSHClient):
        cleanup (str|None)

    Returns (tuple): (rnt_code (int), subnet_id (str))

    """

    if subnet_range is None and subnet_pool is None:
        raise ValueError("Either cidr or subnet_pool has to be specified.")

    args_dict = {
        '--project': project,
        '--project-domain': project_domain,
        '--subnet-pool': subnet_pool,
        '--use-default-subnet-pool': use_default_subnet_pool,
        '--prefix-length': prefix_length,
        '--subnet-range': subnet_range,
        '--dhcp': True if dhcp else None,
        '--no-dhcp': True if dhcp is False else None,
        '--gateway': gateway,
        '--ip-version': ip_version,
        '--ipv6-ra-mode': ipv6_ra_mode,
        '--ipv6-address-mode': ipv6_addr_mode,
        '--network-segment': network_segment,
        '--network': network,
        '--description': description,
        '--allocation-pool': allocation_pools,
        '--dns-nameserver': dns_servers,
        '--host-route': host_routes,
        '--service-type': service_types,
        '--tag': tags,
        '--no-tag': no_tag
    }

    if not name:
        name = '{}-subnet'.format(
            get_net_name_from_id(network, con_ssh=con_ssh, auth_info=auth_info))
    name = "{}-{}".format(name, common.Count.get_subnet_count())
    args = '{} {}'.format(
        common.parse_args(args_dict, repeat_arg=True, vals_sep=','), name)

    LOG.info("Creating subnet for network: {}. Args: {}".format(network, args))
    code, output = cli.openstack('subnet create', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    table_ = table_parser.table(output)
    subnet_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup and subnet_id:
        ResourceCleanup.add('subnet', subnet_id, scope=cleanup)

    if code > 0:
        return 1, output

    LOG.info(
        "Subnet {} is successfully created for network {}".format(subnet_id,
                                                                  network))
    return 0, subnet_id


def delete_subnets(subnets, auth_info=Tenant.get('admin'), con_ssh=None,
                   fail_ok=False):
    """
    Delete subnet(s)
    Args:
        subnets (str|list|tuple):
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):

    """
    if isinstance(subnets, str):
        subnets = (subnets,)

    args = ' '.join(subnets)
    LOG.info("Deleting subnet {}".format(subnets))
    code, output = cli.openstack('subnet delete', args, ssh_client=con_ssh,
                                 fail_ok=True, auth_info=auth_info)

    if code > 0:
        return 1, output

    field = 'ID' if re.match(UUID, subnets[0]) else 'Name'
    undeleted_subnets = list(set(subnets) & set(
        get_subnets(auth_info=auth_info, con_ssh=con_ssh, field=field)))
    if undeleted_subnets:
        msg = "Subnet(s) still listed in openstack subnet list after " \
              "deletion: {}".format(undeleted_subnets)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.NeutronError(msg)

    succ_msg = "Subnet(s) successfully deleted: {}".format(subnets)
    LOG.info(succ_msg)
    return 0, succ_msg


def set_subnet(subnet, allocation_pools=None, dns_servers=None,
               host_routes=None, service_types=None,
               tags=None, no_tag=None, name=None, dhcp=None, gateway=None,
               network_segment=None, description=None,
               no_dns_servers=None, no_host_routes=None,
               no_allocation_pool=None,
               auth_info=Tenant.get('admin'), fail_ok=False, con_ssh=None):
    kwargs = locals()
    kwargs['unset'] = False
    return __update_subnet(**kwargs)


def unset_subnet(subnet, allocation_pools=None, dns_servers=None,
                 host_routes=None, service_types=None,
                 tags=None, no_tag=None, auth_info=Tenant.get('admin'),
                 fail_ok=False, con_ssh=None):
    kwargs = locals()
    kwargs['unset'] = True
    return __update_subnet(**kwargs)


def __update_subnet(subnet, unset=False, allocation_pools=None,
                    dns_servers=None, host_routes=None, service_types=None,
                    tags=None, no_tag=None, name=None, dhcp=None, gateway=None,
                    network_segment=None, description=None,
                    no_dns_servers=None, no_host_routes=None,
                    no_allocation_pool=None,
                    auth_info=Tenant.get('admin'), fail_ok=False, con_ssh=None):
    """
    set/unset given setup
    Args:
        subnet (str):
        unset (bool): set or unset
        allocation_pools (None|str|tuple|list):
        dns_servers (None|str|tuple|list):
        host_routes (None|str|tuple|list):
        service_types (None|str|tuple|list):
        tags (None|bool):
        name (str|None):
        dhcp (None|bool):
        gateway (str|None): valid str: <ip> or 'none'
        description:
        auth_info:
        fail_ok:
        con_ssh:

    Returns:

    """
    LOG.info("Update subnet {}".format(subnet))

    arg_dict = {
        '--allocation-pool': allocation_pools,
        '--dns-nameserver': dns_servers,
        '--host-route': host_routes,
        '--service-type': service_types,
        '--tag': tags,
    }

    if unset:
        arg_dict.update(**{'all-tag': True if no_tag else None})
        cmd = 'unset'
    else:
        set_only_dict = {
            '--name': name,
            '--dhcp': True if dhcp else None,
            '--gateway': gateway,
            '--description': description,
            '--network-segment': network_segment,
            '--no-dhcp': True if dhcp is False else None,
            '--no-tag': True if no_tag else None,
            '--no-dns-nameservers': True if no_dns_servers else None,
            '--no-host-route': True if no_host_routes else None,
            '--no-allocation-pool': True if no_allocation_pool else None,
        }
        arg_dict.update(**set_only_dict)
        cmd = 'set'

    args = '{} {}'.format(
        common.parse_args(args_dict=arg_dict, repeat_arg=True, vals_sep=','),
        subnet)

    code, output = cli.openstack('subnet {}'.format(cmd), args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    LOG.info("Subnet {} {} successfully".format(subnet, cmd))
    return 0, subnet


def get_subnets(field='ID', long=False, network=None, subnet_range=None,
                gateway_ip=None, full_name=None,
                ip_version=None, dhcp=None, project=None, project_domain=None,
                service_types=None,
                tags=None, any_tags=None, not_tags=None, not_any_tags=None,
                name=None, strict=True, regex=False, auth_info=None,
                con_ssh=None):
    """
    Get subnets ids based on given criteria.

    Args:
        field (str): header of subnet list table
        long (bool)
        network (str|None):
        subnet_range (str|None):
        gateway_ip (str|None):
        full_name (str|None):
        ip_version (str|None):
        dhcp (bool)
        project (str|None):
        project_domain (str|None):
        service_types (str|list|tuple|None):
        tags (str|list|tuple|None):
        any_tags (str|list|tuple|None):
        not_tags (str|list|tuple|None):
        not_any_tags (str|list|tuple|None):
        name (str): name of the subnet
        strict (bool): whether to perform strict search on given name and cidr
        regex (bool): whether to use regext to search
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): a list of subnet ids

    """
    args_dict = {
        '--long': long,
        '--ip-version': ip_version,
        '--network': network,
        '--subnet-range': subnet_range,
        '--gateway': gateway_ip,
        '--name': full_name,
        '--dhcp': True if dhcp else None,
        '--no-dhcp': True if dhcp is False else None,
        '--project': project,
        '--project-domain': project_domain,
        '--tags': tags,
        '--any-tags': any_tags,
        '--not-tags': not_tags,
        '--not-any-tags': not_any_tags
    }
    args = common.parse_args(args_dict, repeat_arg=False, vals_sep=',')
    service_type_args = common.parse_args({'--server-type': service_types},
                                          repeat_arg=True)
    args = ' '.join((args, service_type_args))

    table_ = table_parser.table(
        cli.openstack('subnet list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if name is not None:
        table_ = table_parser.filter_table(table_, strict=strict, regex=regex,
                                           name=name)

    return table_parser.get_multi_values(table_, field)


def get_subnet_values(subnet, fields, con_ssh=None,
                      auth_info=Tenant.get('admin')):
    """
    Subnet values for given fields via openstack subnet show
    Args:
        subnet:
        fields:
        con_ssh:
        auth_info:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('subnet show', subnet, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields)


def get_network_values(network, fields, strict=True, rtn_dict=False,
                       con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get network values via openstack network show
    Args:
        network:
        fields:
        strict:
        rtn_dict:
        con_ssh:
        auth_info:

    Returns (list|dict):

    """
    if isinstance(fields, str):
        fields = [fields]

    table_ = table_parser.table(
        cli.openstack('network show', network, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    vals = []
    for field in fields:
        val = table_parser.get_value_two_col_table(table_, field, strict=strict,
                                                   merge_lines=True)
        if field == 'subnets':
            val = val.split(',')
            val = [val_.strip() for val_ in val]
        vals.append(val)

    if rtn_dict:
        return {fields[i]: vals[i] for i in range(len(fields))}
    return vals


def set_network(net_id, name=None, enable=None, share=None,
                enable_port_security=None, external=None, default=None,
                provider_net_type=None, provider_phy_net=None,
                provider_segment=None, transparent_vlan=None,
                auth_info=Tenant.get('admin'), fail_ok=False, con_ssh=None,
                **kwargs):
    """
    Update network with given parameters
    Args:
        net_id (str):
        name (str|None): name to update to. Don't update name when None.
        enable (bool|None): True to add --enable. False to add --disable.
        Don't update enable/disable when None.
        share (bool|None):
        enable_port_security (bool|None):
        external (bool|None):
        default (bool|None):
        provider_net_type (str|None):
        provider_phy_net (str|None):
        provider_segment (str|int|None):
        transparent_vlan (bool|None):
        auth_info (dict):
        fail_ok (bool):
        con_ssh (SSHClient):
        **kwargs: additional key/val pairs that are not listed in 'openstack
            network update -h'.
            e,g.,{'wrs-tm:qos': <qos_id>}

    Returns (tuple): (code, msg)
        (0, "Network <net_id> is successfully updated")   Network updated
        successfully
        (1, <std_err>)    'openstack network update' cli is rejected

    """
    args_dict = {
        '--name': (name, {'name': name}),
        '--enable': (
            True if enable is True else None, {'admin_state_up': 'UP'}),
        '--disable': (
            True if enable is False else None, {'admin_state_up': 'DOWN'}),
        '--share': (True if share is True else None, {'shared': 'True'}),
        '--no-share': (True if share is False else None, {'shared': 'False'}),
        '--enable-port-security': (
            True if enable_port_security is True else None,
            {'port_security_enabled': 'True'}),
        '--disable-port-security': (
            True if enable_port_security is False else None,
            {'port_security_enabled': 'False'}),
        '--external': (
            True if external is True else None,
            {'router:external': 'External'}),
        '--internal': (
            True if external is False else None,
            {'router:external': 'Internal'}),
        '--default': (
            True if default is True else None, {'is_default': 'True'}),
        '--no-default': (
            True if default is False else None, {'is_default': 'False'}),
        '--transparent-vlan': (True if transparent_vlan is True else None,
                               {'vlan_transparent': 'True'}),
        '--no-transparent-vlan': (True if transparent_vlan is False else None,
                                  {'vlan_transparent': 'False'}),
        '--provider-network-type': (
            provider_net_type, {'provider:network_type': provider_net_type}),
        '--provider-physical-network': (
            provider_phy_net, {'provider:physical_network': provider_phy_net}),
        '--provider-segment': (
            provider_segment, {'provider:segmentation_id': provider_segment}),
    }
    checks = {}
    args_str = ''
    for arg in args_dict:
        val, check = args_dict[arg]
        if val is not None:
            set_val = '' if val is True else ' {}'.format(val)
            args_str += ' {}{}'.format(arg, set_val)
            if check:
                checks.update(**check)
            else:
                LOG.info("Unknown check field in 'openstack network show' "
                         "for arg {}".format(arg))

    for key, val_ in kwargs.items():
        val_ = ' {}'.format(val_) if val_ else ''
        field_name = key.split('--', 1)[-1]
        arg = '--{}'.format(field_name)
        args_str += ' {}{}'.format(arg, val_)
        if val_:
            checks.update(**kwargs)
        else:
            LOG.info("Unknown check field in 'openstack network show' for "
                     "arg {}".format(arg))

    if not args_str:
        raise ValueError(
            "Nothing to update. Please specify at least one None value")

    LOG.info("Updating network {} with: {}".format(net_id, args_str))
    code, out = cli.openstack('network set', '{} {}'.format(args_str, net_id),
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, out

    if checks:
        LOG.info("Check network {} is updated with: {}".format(net_id, checks))
        actual_res = get_network_values(net_id, fields=list(checks.keys()),
                                        rtn_dict=True, auth_info=auth_info)
        failed = {}
        for field in checks:
            expt_val = checks[field]
            actual_val = actual_res[field]
            if expt_val != actual_val:
                failed[field] = (expt_val, actual_val)

        # Fail directly. If a field is not allowed to be updated, the cli
        # should be rejected
        assert not failed, "Actual value is different than set value in " \
                           "following fields: {}".format(failed)

    msg = "Network {} is successfully updated".format(net_id)
    return 0, msg


def create_security_group(name, project=None, description=None,
                          project_domain=None, tag=None, no_tag=None,
                          auth_info=None, fail_ok=False, con_ssh=None,
                          cleanup='function'):
    """
    Create a security group
    Args:
        name (str):
        project
        project_domain
        tag (str|None|list|tuple)
        no_tag (bool|None)
        description (str):
        auth_info (dict):
            create under this project
        fail_ok (bool):
        con_ssh
        cleanup (str):

    Returns (str|tuple):
        str identifier for the newly created security group
        or if fail_ok=True, return tuple:
        (0, identifier) succeeded
        (1, msg) failed
    """
    args_dict = {
        '--project': project,
        '--project-domain': project_domain,
        '--description': description,
        '--tag': tag,
        '--no-tag': no_tag,
    }
    args = '{} {}'.format(common.parse_args(args_dict, repeat_arg=True), name)

    code, output = cli.openstack("security group create", args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    table_ = table_parser.table(output)
    group_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup:
        ResourceCleanup.add('security_group', group_id, scope=cleanup)

    LOG.info("Security group created: name={} id={}".format(name, group_id))
    return 0, group_id


def delete_security_group(group_id, fail_ok=False,
                          auth_info=Tenant.get('admin')):
    """
    Delete a security group
    Args:
        group_id (str): security group to be deleted
        fail_ok
        auth_info (dict):

    Returns (tuple): (code, msg)
        (0, msg): succeeded
        (1, err_msg): failed
    """
    LOG.info("Deleting security group {}".format(group_id))
    return cli.openstack("security group delete", group_id, fail_ok=fail_ok,
                         auth_info=auth_info)


def create_security_group_rule(group=None, remote_ip=None, remote_group=None,
                               description=None, dst_port=None,
                               icmp_type=None, icmp_code=None, protocol=None,
                               ingress=None, egress=None,
                               ethertype=None, project=None,
                               project_domain=None, fail_ok=False,
                               auth_info=None,
                               con_ssh=None, field='id', cleanup=None):
    """
    Create security group rule for given security group
    Args:
        group:
        remote_ip:
        remote_group:
        description:
        dst_port:
        icmp_type:
        icmp_code:
        protocol:
        ingress:
        egress:
        ethertype:
        project:
        project_domain:
        fail_ok:
        auth_info:
        con_ssh:
        field (str)
        cleanup

    Returns:

    """
    if not group:
        groups = get_security_groups(name='default', project=project,
                                     project_domain=project_domain,
                                     auth_info=auth_info, con_ssh=con_ssh)
        if len(groups) != 1:
            return ValueError(
                'group has to be specified when multiple default groups exist')
        group = groups[0]

    args_dict = {
        'remote-ip': remote_ip,
        'remote-group': remote_group,
        'description': description,
        'dst-port': dst_port,
        'icmp-type': icmp_type,
        'icmp-code': icmp_code,
        'protocol': protocol,
        'ingress': ingress,
        'egress': egress,
        'ethertype': ethertype,
        'project': project,
        'project-domain': project_domain
    }
    args = ' '.join((common.parse_args(args_dict), group))

    LOG.info(
        "Creating security group rule for group {} with args: {}".format(group,
                                                                         args))
    code, output = cli.openstack('security group rule create', args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    table_ = table_parser.table(output)
    value = table_parser.get_value_two_col_table(table_, field)
    if cleanup:
        ResourceCleanup.add('security_group_rule',
                            table_parser.get_value_two_col_table(table_, 'id'))

    LOG.info(
        "Security group rule created successfully for group {} with "
        "{}={}".format(group, field, value))
    return 0, value


def delete_security_group_rules(sec_rules, check_first=True, fail_ok=False,
                                con_ssh=None,
                                auth_info=Tenant.get('admin')):
    """
    Delete given security group rules
    Args:
        sec_rules:
        check_first:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):

    """
    if isinstance(sec_rules, str):
        sec_rules = (sec_rules,)

    if check_first:
        existing_sec_rules = get_security_group_rules(long=False,
                                                      auth_info=auth_info,
                                                      con_ssh=con_ssh)
        sec_rules = list(set(sec_rules) & set(existing_sec_rules))

    code, output = cli.openstack('security group rule delete',
                                 ' '.join(sec_rules), ssh_client=con_ssh,
                                 fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    post_sec_rules = get_security_group_rules(long=False, auth_info=auth_info,
                                              con_ssh=con_ssh)
    undeleted_rules = sec_rules = list(set(sec_rules) & set(post_sec_rules))
    if undeleted_rules:
        msg = 'Security group rule(s) still exist after deletion: {}'.format(
            undeleted_rules)
        LOG.warning(msg)
        if fail_ok:
            return 2, msg

    msg = "Security group rule(s) deleted successfully: {}".format(sec_rules)
    LOG.info(msg)
    return 0, msg


def get_security_group_rules(field='ID', long=True, protocol=None, ingress=None,
                             egress=None, group=None,
                             auth_info=None, con_ssh=None, **filters):
    """
    Get security group rules
    Args:
        field (str|list|tuple)
        long (bool)
        protocol:
        ingress:
        egress:
        group (str): security group id
        auth_info:
        con_ssh:
        **filters: header value pairs for security group rules table

    Returns (list):

    """
    args_dict = {
        'protocol': protocol,
        'ingress': ingress,
        'egress': egress,
        'long': long,
    }
    args = common.parse_args(args_dict)
    if group:
        args += ' {}'.format(group)
    output = cli.openstack('security group rule list', args, ssh_client=con_ssh,
                           auth_info=auth_info)[1]
    table_ = table_parser.table(output)
    return table_parser.get_multi_values(table_, field, **filters)


def add_icmp_and_tcp_rules(security_group, auth_info=Tenant.get('admin'),
                           con_ssh=None, cleanup=None):
    """
    Add icmp and tcp security group rules to given security group to allow
    ping and ssh
    Args:
        security_group (str):
        auth_info:
        con_ssh:
        cleanup

    """
    security_rules = get_security_group_rules(
        con_ssh=con_ssh, auth_info=auth_info, group=security_group,
        protocol='ingress', **{'IP Protocol': ('tcp', 'icmp')})
    if len(security_rules) >= 2:
        LOG.info("Security group rules for {} already exist to allow ping and "
                 "ssh".format(security_group))
        return

    LOG.info("Create icmp and ssh security group rules for {} with best "
             "effort".format(security_group))
    for rules in (('icmp', None), ('tcp', 22)):
        protocol, dst_port = rules
        create_security_group_rule(group=security_group, protocol=protocol,
                                   dst_port=dst_port, fail_ok=True,
                                   auth_info=auth_info, cleanup=cleanup)


def get_net_name_from_id(net_id, con_ssh=None, auth_info=None):
    """
    Get network name from id

    Args:
        net_id (str):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (str): name of a network

    """
    return get_networks(auth_info=auth_info, con_ssh=con_ssh, net_id=net_id,
                        field='Name')[0]


def get_net_id_from_name(net_name, con_ssh=None, auth_info=None):
    """
    Get network id from full name

    Args:
        net_name (str):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (str): id of a network

    """
    return get_networks(auth_info=auth_info, con_ssh=con_ssh,
                        full_name=net_name, field='ID')[0]


def create_floating_ip(external_net=None, subnet=None, port=None,
                       fixed_ip_addr=None, floating_ip_addr=None,
                       qos_policy=None, description=None, dns_domain=None,
                       dns_name=None, tags=None, no_tag=None,
                       project=None, project_domain=None, fail_ok=False,
                       con_ssh=None, auth_info=None, cleanup=None):
    """
    Create a floating ip for given tenant

    Args:
        external_net (str|None): external network to allocate the floating
            ip from
        subnet (str|None):
        qos_policy (str|None):
        description (str|None):
        dns_name (str|None):
        dns_domain (str|None):
        tags (tuple|list|str|None)
        no_tag (bool|None)
        project_domain (str|None):
        project (str|None): name of the tenant to create floating ip for.
            e.g., 'tenant1', 'tenant2'
        port (str|None): id of the port
        fixed_ip_addr (str): fixed ip address. such as 192.168.x.x
        floating_ip_addr (str): specific floating ip to create
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):
        cleanup (None|str): valid scopes: function, class, module, session

    Returns (str): floating IP. such as 192.168.x.x

    """
    if not external_net:
        external_net = get_networks(con_ssh=con_ssh, external=True,
                                    auth_info=auth_info)[0]

    args_dict = {
        '--subnet': subnet,
        '--port': port,
        '--floating-ip-address': floating_ip_addr,
        '--fixed-ip-address': fixed_ip_addr,
        '--qos-policy': qos_policy,
        '--dns-domain': dns_domain,
        '--dns-name': dns_name,
        '--description': description,
        '--project': project,
        '--project-domain': project_domain,
        '--tag': tags,
        '--no-tag': no_tag
    }

    args = '{} {}'.format(common.parse_args(args_dict, repeat_arg=True),
                          external_net)
    code, output = cli.openstack('floating ip create', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    table_ = table_parser.table(output)
    actual_fip_addr = table_parser.get_value_two_col_table(
        table_, "floating_ip_address")
    if actual_fip_addr and cleanup:
        ResourceCleanup.add('floating_ip', actual_fip_addr, scope=cleanup)

    if code > 0:
        return 1, output

    if not actual_fip_addr:
        msg = "Floating IP is not found in the list"
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.NeutronError(msg)

    succ_msg = "Floating IP created successfully: {}".format(actual_fip_addr)
    LOG.info(succ_msg)
    return 0, actual_fip_addr


def delete_floating_ips(floating_ips, auth_info=Tenant.get('admin'),
                        con_ssh=None, fail_ok=False):
    """
    Delete a floating ip

    Args:
        floating_ips (str|tuple|list): floating ip to delete.
        auth_info (dict):
        con_ssh (SSHClient):
        fail_ok (bool): whether to raise exception if fail to delete floating ip

    Returns (tuple): (rtn_code(int), msg(str))
        - (0, Floating ip <ip> is successfully deleted.)
        - (1, <stderr>)
        - (2, Floating ip <ip> still exists in floatingip-list.)

    """
    if isinstance(floating_ips, str):
        floating_ips = (floating_ips,)

    args = ' '.join(floating_ips)
    code, output = cli.openstack('floating ip delete', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, output

    post_deletion_fips = get_floating_ips(field='ID', con_ssh=con_ssh,
                                          auth_info=Tenant.get('admin'))
    undeleted_fips = list(set(floating_ips) & set(post_deletion_fips))

    if undeleted_fips:
        msg = "Floating ip {} still exists in floating ip list.".format(
            undeleted_fips)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.NeutronError(msg)

    succ_msg = "Floating ip deleted successfully: {}".format(floating_ips)
    LOG.info(succ_msg)
    return 0, succ_msg


def get_floating_ips(field='Floating IP Address', long=False, network=None,
                     port=None, router=None,
                     floating_ip=None, fixed_ip=None, status=None, project=None,
                     project_domain=None,
                     tags=None, any_tags=None, not_tags=None, not_any_tags=None,
                     floating_ips=None,
                     auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get floating ips values with given parameters.

    Args:
        field (str|tuple|list): header of floating ip list table, such as
        'Floating IP Address' or 'Fixed IP Address'
        long (bool)
        network (str|None)
        router (str|None)
        fixed_ip (str|None): fixed ip address
        floating_ip (str|None):
        port (str|None): port id
        status (str|None):
        project (str|None):
        project_domain (str|None):
        tags (str|tuple|listNone):
        any_tags (str|tuple|listNone):
        not_tags (str|tuple|listNone):
        not_any_tags (str|tuple|listNone):
        floating_ips (str|list|tuple): post execution table filters
        auth_info (dict): if tenant auth_info is given instead of admin,
        only floating ips for this tenant will be
            returned.
        con_ssh (SSHClient):

    Returns (list): list of floating ips values

    """
    args_dict = {
        '--long': long,
        '--network': network,
        '--port': port,
        '--fixed-ip-address': fixed_ip,
        '--floating-ip-address': floating_ip,
        '--status': status,
        '--router': router,
        '--project': project,
        '--project-domain': project_domain,
        '--tags': tags,
        '--any-tags': any_tags,
        '--not-tags': not_tags,
        '--not-any-tags': not_any_tags
    }
    args = common.parse_args(args_dict, repeat_arg=False, vals_sep=',')
    table_ = table_parser.table(
        cli.openstack('floating ip list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if floating_ips:
        table_ = table_parser.filter_table(table_, **{
            'Floating IP Address': floating_ips})

    return table_parser.get_multi_values(table_, field)


def get_floating_ip_values(fip, fields='fixed_ip_address',
                           auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get floating ip info for given field.
    Args:
        fip (str): ip or id of a floating ip
        fields (str|list|tuple): field(s) in floating ip show table.
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): values of given fields for specified floating ip

    """
    table_ = table_parser.table(
        cli.openstack('floating ip show', fip, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    return table_parser.get_multi_values_two_col_table(table_, fields=fields,
                                                       evaluate=True)


def unset_floating_ip(floating_ip, port=None, qos_policy=None, tags=None,
                      all_tag=None, auth_info=Tenant.get('admin'),
                      con_ssh=None, fail_ok=False):
    """
    Disassociate a floating ip

    Args:
        floating_ip (str): ip or id of the floating ip
        port (bool)
        qos_policy (bool)
        tags (str|None|list|tuple)
        all_tag (bool)
        auth_info (dict):
        con_ssh (SSHClient):
        fail_ok (bool):

    Returns (tuple): (rtn_code(int), msg(str))
        (0, "Floating ip <ip> is successfully disassociated with fixed ip")
        (1, <stderr>)

    """

    args_dict = {
        '--port': port,
        '--qos-policy': qos_policy,
        '--tag': tags,
        '--all-tag': all_tag,
    }

    args = common.parse_args(args_dict, repeat_arg=True)
    if not args:
        raise ValueError("Nothing is specified to unset")

    args = '{} {}'.format(args, floating_ip)
    code, output = cli.openstack('floating ip unset', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code == 1:
        return 1, output

    fixed_ip = get_floating_ip_values(floating_ip, fields='fixed_ip_address',
                                      auth_info=auth_info, con_ssh=con_ssh)[0]
    if fixed_ip is not None:
        err_msg = "Fixed ip address is {} instead of None for floating ip " \
                  "{}".format(fixed_ip, floating_ip)
        if fail_ok:
            return 2, err_msg
        else:
            raise exceptions.NeutronError(err_msg)

    succ_msg = "Floating ip {} is successfully disassociated with fixed " \
               "ip".format(floating_ip)
    LOG.info(succ_msg)
    return 0, succ_msg


def associate_floating_ip_to_vm(floating_ip, vm_id, vm_ip=None,
                                auth_info=Tenant.get('admin'),
                                con_ssh=None, fail_ok=False):
    """
    Associate a floating ip to management net ip of given vm.

    Args:
        floating_ip (str): ip or id of the floating ip
        vm_id (str): vm id
        vm_ip (str): management ip of a vm used to find the matching port to
        attach floating ip to
        auth_info (dict):
        con_ssh (SSHClient):
        fail_ok (bool):

    Returns (tuple): (rtn_code(int), msg(str))
        (0, <floating ip address>)
        (1, <stderr>)

    """
    if not vm_ip:
        # get a vm management ip if not given
        vm_ip = get_mgmt_ips_for_vms(vm_id, con_ssh=con_ssh)[0]

    port = get_ports(server=vm_id, fixed_ips={'ip-address': vm_ip},
                     con_ssh=con_ssh)[0]

    code, output = set_floating_ip(floating_ip=floating_ip, port=port,
                                   fixed_ip_addr=vm_ip, auth_info=auth_info,
                                   con_ssh=con_ssh, fail_ok=fail_ok)
    if code > 0:
        return 1, output

    if re.match(floating_ip, UUID):
        floating_ip = \
            get_floating_ip_values(floating_ip, fields='floating_ip_address',
                                   con_ssh=con_ssh)[0]

    _wait_for_ip_in_nova_list(vm_id, ip_addr=floating_ip, fail_ok=False,
                              con_ssh=con_ssh)
    return 0, floating_ip


def set_floating_ip(floating_ip, port=None, fixed_ip_addr=None, qos_policy=None,
                    tags=None, no_tag=None,
                    auth_info=Tenant.get('admin'), con_ssh=None, fail_ok=False):
    """
    Set floating ip properties
    Args:
        floating_ip:
        port:
        fixed_ip_addr:
        qos_policy:
        tags:
        no_tag:
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):

    """
    args_dict = {
        '--port': port,
        '--fixed-ip-address': fixed_ip_addr,
        '--qos-policy': qos_policy,
        '--tag': tags,
        '--no-tag': no_tag,
    }

    args = common.parse_args(args_dict, repeat_arg=True)
    if not args:
        raise ValueError("Nothing is specified to set")

    args = '{} {}'.format(args, floating_ip)

    code, output = cli.openstack('floating ip set', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    succ_msg = "port {} is successfully associated with floating ip {}".format(
        port, floating_ip)
    LOG.info(succ_msg)
    return 0, floating_ip


def _wait_for_ip_in_nova_list(vm_id, ip_addr, timeout=300, fail_ok=False,
                              con_ssh=None, auth_info=Tenant.get('admin')):
    end_time = time.time() + timeout
    while time.time() < end_time:
        vm_ips = _get_net_ips_for_vms(vms=vm_id, rtn_dict=False,
                                      con_ssh=con_ssh, auth_info=auth_info)
        if ip_addr in vm_ips:
            return True
    else:
        msg = "IP address {} is not found in openstack server list for vm {} " \
              "within {} seconds".format(ip_addr, vm_id, timeout)
        if fail_ok:
            return False
        raise exceptions.TimeoutException(msg)


def get_providernet_ranges(field='name', range_name=None, providernet_name=None,
                           providernet_type=None, strict=False,
                           auth_info=Tenant.get('admin'), con_ssh=None):
    """

    Args:
        field (str): 'name' or 'id'
        range_name (str):
        providernet_name (str):
        providernet_type (str):
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): list of range names or ids

    """

    table_ = table_parser.table(
        cli.neutron('providernet-range-list', ssh_client=con_ssh,
                    auth_info=auth_info)[1])

    kwargs = {}
    if providernet_name is not None:
        kwargs['providernet'] = providernet_name

    if range_name is not None:
        kwargs['name'] = range_name

    if providernet_type is not None:
        kwargs['type'] = providernet_type

    return table_parser.get_values(table_, field, strict=strict, **kwargs)


def get_security_groups(field='id', project=None, project_domain=None,
                        tags=None, any_tags=None,
                        not_tags=None, not_any_tags=None, name=None,
                        strict=False, con_ssh=None, auth_info=None):
    """
        Get the neutron security group list based on name if given for given
        user.

        Args:
            field (str|list|tuple)
            project
            project_domain
            tags (list|tuple|str|None)
            any_tags (list|tuple|str|None)
            not_tags (list|tuple|str|None)
            not_any_tags (list|tuple|str|None)
            con_ssh (SSHClient): If None, active controller ssh will be used.
            auth_info (dict): Tenant dict. If None, primary tenant will be used.
            name (str): Given name for the security group to filter
            strict (bool): strict match for name

        Returns (list): Neutron security group id.

    """
    args_dict = {
        'project': project,
        'project_domain': project_domain,
        'tags': tags,
        'any-tags': any_tags,
        'not-tags': not_tags,
        'not-any-tags': not_any_tags,
    }
    args = common.parse_args(args_dict, vals_sep=',')
    table_ = table_parser.table(
        cli.openstack('security group list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if name:
        table_ = table_parser.filter_table(table_, strict=strict, name=name)

    return table_parser.get_multi_values(table_, field)


def get_internal_net_id(net_name=None, strict=False, con_ssh=None,
                        auth_info=None):
    """
    Get internal network id that matches the given net_name of a specific
    tenant.

    Args:
        net_name (str): name of the internal network. This can be a substring
        of the tenant net name, such as 'net1',
            and it will return id for internal0-net1
        strict (bool): Whether to perform strict search on given net_name
        con_ssh (SSHClient):
        auth_info (dict): If None, primary tenant will be used.

    Returns (str): A tenant network id for given tenant network name.
        If multiple ids matches the given name, only the first will return

    """
    net_ids = get_internal_net_ids(net_names=net_name, strict=strict,
                                   con_ssh=con_ssh, auth_info=auth_info)
    if not net_ids:
        raise exceptions.TiSError(
            "No network name contains {} in 'openstack network list'".format(
                net_name))

    return net_ids[0]


def get_mgmt_net_id(con_ssh=None, auth_info=None):
    """
    Get the management net id of given tenant.

    Args:
        con_ssh (SSHClient): If None, active controller ssh will be used.
        auth_info (dict): Tenant dict. If None, primary tenant will be used.

    Returns (str): Management network id of a specific tenant.

    """
    mgmt_net_name = Networks.get_nenutron_net_patterns(net_type='mgmt')[0]
    mgmt_ids = get_networks(name=mgmt_net_name, con_ssh=con_ssh,
                            auth_info=auth_info, strict=False, regex=True)
    if not mgmt_ids:
        raise exceptions.TiSError(
            "No network name contains {} in 'openstack network list'".format(
                mgmt_net_name))
    return mgmt_ids[0]


def get_tenant_net_id(net_name=None, con_ssh=None, auth_info=None):
    """
    Get tenant network id that matches the given net_name of a specific tenant.

    Args:
        net_name (str): name of the tenant network. This can be a substring
        of the tenant net name, such as 'net1',
            and it will return id for <tenant>-net1
        con_ssh (SSHClient):
        auth_info (dict): If None, primary tenant will be used.

    Returns (str): A tenant network id for given tenant network name.
        If multiple ids matches the given name, only the first will return

    """
    net_ids = get_tenant_net_ids(net_names=net_name, con_ssh=con_ssh,
                                 auth_info=auth_info)
    if not net_ids:
        raise exceptions.TiSError(
            "No network name contains {} in 'openstack network list'".format(
                net_name))

    return net_ids[0]


def get_tenant_net_ids(net_names=None, strict=False, regex=True, con_ssh=None,
                       auth_info=None, field='id'):
    """
    Get a list of tenant network ids that match the given net_names for a
    specific tenant.

    Args:
        net_names (str or list): list of tenant network name(s) to get id(s) for
        strict (bool): whether to perform a strict search on  given name
        regex (bool): whether to search using regular expression
        con_ssh (SSHClient):
        auth_info (dict): If None, primary tenant will be used
        field (str): id or name

    Returns (list): list of tenant nets. such as (<id for tenant2-net1>,
    <id for tenant2-net8>)

    """
    if net_names is None:
        net_names = Networks.get_nenutron_net_patterns('data')[0]
        regex = True
        strict = False

    return get_networks(field=field, con_ssh=con_ssh, auth_info=auth_info,
                        strict=strict, regex=regex, name=net_names)


def get_internal_net_ids(net_names=None, strict=False, regex=True, con_ssh=None,
                         auth_info=None):
    """
    Get a list of internal network ids that match the given net_names for a
    specific tenant.

    Args:
        net_names (str or list): list of internal network name(s) to get id(
        s) for
        strict (bool): whether to perform a strict search on  given name
        regex (bool): whether to search using regular expression
        con_ssh (SSHClient):
        auth_info (dict): If None, primary tenant will be used

    Returns (list): list of tenant nets. such as (<id for tenant2-net1>,
    <id for tenant2-net8>)

    """
    if net_names is None:
        net_names = Networks.get_nenutron_net_patterns('internal')[0]
        strict = False
        regex = True
    else:
        if isinstance(net_names, str):
            net_names = [net_names]

        for i in range(len(net_names)):
            net_name = net_names[i]
            if 'internal' not in net_name:
                net_names[i] = 'internal.*{}'.format(net_name)

    return get_networks(field='ID', con_ssh=con_ssh, auth_info=auth_info,
                        strict=strict, regex=regex, name=net_names)


def get_tenant_ips_for_vms(vms=None, con_ssh=None,
                           auth_info=Tenant.get('admin'), rtn_dict=False,
                           exclude_nets=None):
    """
    This function returns the management IPs for all VMs on the system.
    We make the assumption that the management IPs start with "192".
    Args:
        vms (str|list|None): vm ids list. If None, management ips for ALL vms
        with given Tenant(via auth_info) will be
            returned.
        con_ssh (SSHClient): active controller SSHClient object
        auth_info (dict): use admin by default unless specified
        rtn_dict (bool): return list if False, return dict if True
        exclude_nets (list|str) network name(s) - exclude ips from given
        network name(s)

    Returns (list|dict):
        a list of all VM management IPs   # rtn_dict=False
        dictionary with vm IDs as the keys, and mgmt ips as values    #
        rtn_dict=True
    """
    net_name_pattern, net_ip_pattern = Networks.get_nenutron_net_patterns(
        'data')
    return _get_net_ips_for_vms(netname_pattern=net_name_pattern,
                                ip_pattern=net_ip_pattern, vms=vms,
                                con_ssh=con_ssh, auth_info=auth_info,
                                rtn_dict=rtn_dict,
                                exclude_nets=exclude_nets)


def get_internal_ips_for_vms(vms=None, con_ssh=None,
                             auth_info=Tenant.get('admin'), rtn_dict=False,
                             exclude_nets=None):
    """
    This function returns the management IPs for all VMs on the system.
    We make the assumption that the management IPs start with "192".
    Args:
        vms (str|list|None): vm ids list. If None, management ips for ALL vms
        with given Tenant(via auth_info) will be
            returned.
        con_ssh (SSHClient): active controller SSHClient object
        auth_info (dict): use admin by default unless specified
        rtn_dict (bool): return list if False, return dict if True
        exclude_nets (list|str) network name(s) - exclude ips from given
        network name(s)

    Returns (list|dict):
        a list of all VM management IPs   # rtn_dict=False
        dictionary with vm IDs as the keys, and mgmt ips as values    #
        rtn_dict=True
    """
    net_name_pattern, net_ip_pattern = Networks.get_nenutron_net_patterns(
        'internal')
    return _get_net_ips_for_vms(netname_pattern=net_name_pattern,
                                ip_pattern=net_ip_pattern, vms=vms,
                                con_ssh=con_ssh, auth_info=auth_info,
                                rtn_dict=rtn_dict,
                                exclude_nets=exclude_nets)


def get_external_ips_for_vms(vms=None, con_ssh=None,
                             auth_info=Tenant.get('admin'), rtn_dict=False,
                             exclude_nets=None):
    net_name_pattern, net_ip_pattern = Networks.get_nenutron_net_patterns(
        'external')
    return _get_net_ips_for_vms(netname_pattern=net_name_pattern,
                                ip_pattern=net_ip_pattern, vms=vms,
                                con_ssh=con_ssh, auth_info=auth_info,
                                rtn_dict=rtn_dict,
                                exclude_nets=exclude_nets)


def get_mgmt_ips_for_vms(vms=None, con_ssh=None, auth_info=Tenant.get('admin'),
                         rtn_dict=False, exclude_nets=None):
    """
    This function returns the management IPs for all VMs on the system.
    We make the assumption that the management IP pattern is "192.168.xxx.x(
    xx)".
    Args:
        vms (str|list|None): vm ids list. If None, management ips for ALL vms
        with given Tenant(via auth_info) will be
            returned.
        con_ssh (SSHClient): active controller SSHClient object
        auth_info (dict): use admin by default unless specified
        rtn_dict (bool): return list if False, return dict if True
        exclude_nets (list|str) network name(s) - exclude ips from given
        network name(s)

    Returns (list|dict):
        a list of all VM management IPs   # rtn_dict=False
        dictionary with vm IDs as the keys, and mgmt ips as values    #
        rtn_dict=True
    """
    net_name_pattern, net_ip_pattern = Networks.get_nenutron_net_patterns(
        'mgmt')
    return _get_net_ips_for_vms(netname_pattern=net_name_pattern,
                                ip_pattern=net_ip_pattern, vms=vms,
                                con_ssh=con_ssh, auth_info=auth_info,
                                rtn_dict=rtn_dict,
                                exclude_nets=exclude_nets)


def _get_net_ips_for_vms(netname_pattern=None, ip_pattern=None, vms=None,
                         con_ssh=None, auth_info=Tenant.get('admin'),
                         rtn_dict=False, exclude_nets=None, fail_ok=False):
    if not vms and vms is not None:
        raise ValueError("Invalid value for vms: {}".format(vms))

    args = '--a' if auth_info and auth_info.get('user') == 'admin' else ''
    table_ = table_parser.table(
        cli.openstack('server list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if vms:
        table_ = table_parser.filter_table(table_, ID=vms)

    vm_ids = table_parser.get_column(table_, 'ID')
    if not vm_ids:
        raise ValueError("No VM found.")

    all_ips = []
    all_ips_dict = {}
    vms_nets = table_parser.get_column(table_, 'Networks')

    if exclude_nets and isinstance(exclude_nets, str):
        exclude_nets = [exclude_nets]

    for i in range(len(vm_ids)):
        vm_id = vm_ids[i]
        vm_nets = vms_nets[i].split(sep=';')
        ips_for_vm = []
        for vm_net in vm_nets:
            net_name, net_ips = vm_net.strip().split('=')
            if exclude_nets:
                for net_to_exclude in exclude_nets:
                    if net_to_exclude in net_name:
                        LOG.info("Excluding IPs from {}".format(net_to_exclude))
                        continue
            # find ips for given netname_pattern
            if not netname_pattern or re.search(netname_pattern, net_name):
                net_ips = [net_ip.strip() for net_ip in net_ips.split(',')]
                ips_for_vm += net_ips

        if not ips_for_vm:
            LOG.warning(
                "No network found for vm {} with net name pattern: {}".format(
                    vm_id, netname_pattern))
            continue

        # Filter further if IP pattern is given
        if ip_pattern:
            ips_for_vm = re.findall(ip_pattern, ','.join(ips_for_vm))
            if not ips_for_vm:
                LOG.warning(
                    "No ip found for vm {} with pattern {}".format(vm_id,
                                                                   ip_pattern))
                continue

        LOG.debug('targeted ips for vm: {}'.format(ips_for_vm))
        all_ips_dict[vm_id] = ips_for_vm
        all_ips += ips_for_vm

    if not all_ips:
        if fail_ok:
            return all_ips_dict if rtn_dict else all_ips
        raise ValueError(
            "No ip found for VM(s) {} with net name pattern: {}{}".format(
                vm_ids, netname_pattern, ', and ip pattern: {}'.format(
                    ip_pattern) if ip_pattern else ''))

    LOG.info("IPs dict: {}".format(all_ips_dict))
    if rtn_dict:
        return all_ips_dict
    else:
        return all_ips


def get_routers(field='ID', name=None, distributed=None, ha=None,
                gateway_ip=None, strict=True, regex=False,
                auth_info=None, con_ssh=None):
    """
    Get router id(s) based on given criteria.
    Args:
        field (str|tuple|list): header(s) of the router list table
        name (str): router name
        distributed (bool): filter out dvr or non-dvr router
        ha (bool): filter out HA router
        gateway_ip (str): ip of the external router gateway such as
        "192.168.13.3"
        strict (bool): whether to perform strict search on router name
        regex
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): list of routers

    """
    param_dict = {
        'Distributed': distributed,
        'HA': ha,
        'External_gateway_info': gateway_ip,
    }
    params = {k: str(v) for k, v in param_dict.items() if v is not None}
    args = '--long' if 'External_gateway_info' in params else ''

    table_ = table_parser.table(
        cli.openstack('router list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1],
        combine_multiline_entry=True)
    if name is not None:
        table_ = table_parser.filter_table(table_, strict=strict, regex=regex,
                                           name=name)
    if params:
        table_ = table_parser.filter_table(table_, **params)

    convert = False
    if isinstance(field, str):
        field = [field]
        convert = True

    values_all_fields = []
    for header in field:
        values = table_parser.get_values(table_, header)
        if header.lower() == 'external gateway info':
            values = [
                eval(value.replace('true', 'True').replace('false', 'False'))
                for value in values]
        values_all_fields.append(values)

    if convert:
        return values_all_fields[0]

    return values_all_fields


def get_tenant_router(router_name=None, auth_info=None, con_ssh=None):
    """
    Get id of tenant router with specified name.

    Args:
        router_name (str): name of the router
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (str): router id

    """
    if router_name is None:
        tenant_name = common.get_tenant_name(auth_info=auth_info)
        router_name = tenant_name + '-router'

    routers = get_routers(auth_info=auth_info, con_ssh=con_ssh,
                          name=router_name)
    if not routers:
        LOG.warning("No router with name {} found".format(router_name))
        return None
    return routers[0]


def get_router_values(router_id=None, fields='status', strict=True,
                      auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get values of specified fields for given router via openstack router show

    Args:
        router_id (str):
        fields (str|list|tuple):
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): values for given fields in openstack router show

    """
    if router_id is None:
        router_id = get_tenant_router(con_ssh=con_ssh)

    table_ = table_parser.table(
        cli.openstack('router show', router_id, ssh_client=con_ssh,
                      auth_info=auth_info)[1],
        combine_multiline_entry=True)

    if isinstance(fields, str):
        fields = (fields,)
    values = []
    for field in fields:
        value = table_parser.get_value_two_col_table(table_, field,
                                                     strict=strict)
        if field in ('interfaces_info', 'external_gateway_info',
                     'distributed') or value in ('None', 'False', 'True'):
            value = eval(
                value.replace('true', 'True').replace('false', 'False'))
        values.append(value)
    return values


def create_router(name=None, project=None, distributed=None, ha=None,
                  disable=None, description=None, tags=None,
                  no_tag=None, avail_zone_hint=None, project_domain=None,
                  rtn_name=False,
                  fail_ok=False, auth_info=Tenant.get('admin'), con_ssh=None,
                  cleanup=None):
    """
    Create a neutron router with given parameters
    Args:
        name (str|None):
        project (str|None):
        distributed (bool|None):
        ha (bool|None):
        disable (bool|None):
        description (str|None):
        tags (str|list|tuple|None):
        no_tag (bool|None):
        avail_zone_hint (str|None):
        project_domain (str|None):
        rtn_name (bool): return router name if True else return router id
        fail_ok (bool):
        auth_info:
        con_ssh:
        cleanup (str|None): Valid cleanup scopes: function, class, module,
            session

    Returns (tuple):
        (0, <router>)   # router created successfully
        (1, <std_err>)  # CLI rejected

    """
    if name is None:
        name = 'router'
        name = '-'.join([project, name, str(common.Count.get_router_count())])

    if not project and auth_info and auth_info['tenant'] == 'admin':
        project = Tenant.get_primary()['tenant']

    args_dict = {
        '--project': project,
        '--distributed': True if distributed else None,
        '--centralized': True if distributed is False else None,
        '--ha': True if ha else None,
        '--no-ha': True if ha is False else None,
        '--enable': True if disable is False else None,
        '--disable': True if disable else None,
        '--description': description,
        '--tag': tags,
        '--no-tag': no_tag,
        '--availability-zone-hint': avail_zone_hint,
        '--project-domain': project_domain,
    }
    args = '{} {}'.format(common.parse_args(args_dict, repeat_arg=True), name)

    LOG.info("Creating router with args: {}".format(args))
    code, output = cli.openstack('router create', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    table_ = table_parser.table(output)
    router_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup and router_id:
        ResourceCleanup.add('router', router_id, scope=cleanup)

    # process result
    if code > 0:
        return 1, output

    succ_msg = "Router {} is created successfully.".format(name)
    LOG.info(succ_msg)
    return 0, name if rtn_name else router_id


def get_router_subnets(router, field='subnet_id', router_interface_only=True,
                       auth_info=Tenant.get('admin'),
                       con_ssh=None):
    """
    Get router subnets' ids or ips via openstack port list
    Args:
        router (str): router name or id
        field (str): 'subnet_id' or 'ip_address'
        router_interface_only
        auth_info:
        con_ssh:

    Returns (list):

    """
    fixed_ips, device_owners = get_ports(
        field=('Fixed IP Addresses', 'Device Owner'), router=router, long=True,
        auth_info=auth_info, con_ssh=con_ssh)

    subnets = []
    for i in range(len(device_owners)):
        device_owner = device_owners[i]
        # Assume router can have only 1 fixed ip on same port
        fixed_ip_info = fixed_ips[i][0]
        if router_interface_only and 'router_interface' not in device_owner:
            continue
        subnets.append(fixed_ip_info.get(field, None))

    return subnets


def get_next_subnet_cidr(net_id, ip_pattern=Networks.IPV4_IP, con_ssh=None,
                         auth_info=Tenant.get('admin')):
    """
    Get next unused cider for given network
    Args:
        net_id:
        ip_pattern:
        con_ssh:
        auth_info:

    Returns:

    """
    existing_subnets = get_subnets(field='Subnet', network=net_id,
                                   con_ssh=con_ssh, auth_info=auth_info)
    existing_subnets_str = ','.join(existing_subnets)
    # TODO: add ipv6 support
    mask = re.findall(ip_pattern + r'/(\d{1,3})', existing_subnets_str)[0]
    increment = int(math.pow(2, math.ceil(math.log2(int(mask)))))

    ips = re.findall(ip_pattern, existing_subnets_str)
    ips = [ipaddress.ip_address(item) for item in ips]
    max_ip = ipaddress.ip_address(max(ips))

    cidr = "{}/{}".format(str(ipaddress.ip_address(int(max_ip) + increment)),
                          mask)
    LOG.info("Next unused CIDR for network {}: {}".format(net_id, cidr))

    return cidr


def delete_router(router, remove_ports=True, auth_info=Tenant.get('admin'),
                  con_ssh=None, fail_ok=False):
    """
    Delete given router
    Args:
        router (str):
        remove_ports (bool):
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):

    """

    if remove_ports:
        LOG.info("Clear router gateway and remove attached ports for router "
                 "{}".format(router))
        clear_router_gateway(router, auth_info=auth_info, con_ssh=con_ssh)
        router_ports = get_ports(router=router, con_ssh=con_ssh,
                                 auth_info=auth_info)
        for port in router_ports:
            remove_router_interface(router, port=port, auth_info=auth_info,
                                    con_ssh=con_ssh)

    LOG.info("Deleting router {}...".format(router))
    code, output = cli.openstack('router delete', router, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    rtn_val = 'ID' if re.match(UUID, router) else 'Name'
    post_routers = get_routers(auth_info=auth_info, con_ssh=con_ssh,
                               field=rtn_val)
    if router in post_routers:
        msg = "Router {} is still showing in neutron router-list".format(router)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg

    succ_msg = "Router {} deleted successfully".format(router)
    LOG.info(succ_msg)
    return 0, succ_msg


def add_router_interface(router=None, subnet=None, port=None, auth_info=None,
                         con_ssh=None, fail_ok=False):
    """
    Add port or subnet to router
    Args:
        router (str|None):
        subnet (str|None):
        port (str|None):
        auth_info (dict):
        con_ssh:
        fail_ok (bool):

    Returns (tuple):
    """

    return __add_remove_router_interface(router=router, port=port,
                                         subnet=subnet, action='add',
                                         auth_info=auth_info, con_ssh=con_ssh,
                                         fail_ok=fail_ok)


def remove_router_interface(router=None, subnet=None, port=None, auth_info=None,
                            con_ssh=None, fail_ok=False):
    """
    Remove port or subnet from router
    Args:
        router (str|None):
        subnet (str|None):
        port (str|None):
        auth_info (dict):
        con_ssh:
        fail_ok (bool):

    Returns (tuple):
    """
    return __add_remove_router_interface(router=router, port=port,
                                         subnet=subnet, action='remove',
                                         auth_info=auth_info, con_ssh=con_ssh,
                                         fail_ok=fail_ok)


def __add_remove_router_interface(router=None, subnet=None, port=None,
                                  action='add', auth_info=None,
                                  con_ssh=None, fail_ok=False):
    """
    Remove router port or subnet
    Args:
        router (str):
        subnet
        port
        action (str): add or remove
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):

    """
    if subnet is None and port is None:
        raise ValueError("subnet or port has to be provided")

    if not router:
        router = get_tenant_router(con_ssh=con_ssh, auth_info=auth_info)

    if subnet:
        interface = subnet
        interface_type = 'subnet'
    else:
        interface = port
        interface_type = 'port'

    cmd = 'router {} {}'.format(action, interface_type)

    args = '{} {}'.format(router, interface)
    LOG.info("Removing router interface: {}".format(args))
    code, output = cli.openstack(cmd, args, ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code == 1:
        return 1, output

    succ_msg = "{} ran successfully for router {}.".format(cmd, router)
    LOG.info(succ_msg)
    return 0, interface


def set_router(router=None, enable=None, external_gateway=None,
               enable_snat=None, routes=None, no_route=None,
               fixed_ips=None, tags=None, no_tag=None, qos_policy=None,
               no_qos_policy=None, ha=None, distributed=None,
               name=None, description=None, fail_ok=False, con_ssh=None,
               auth_info=Tenant.get('admin')):
    """
    Set router with given parameters
    Args:
        router (str):
        enable (bool):
        external_gateway (str):
        enable_snat (bool):
        routes (list): list of dict or strings
            list of dict:
                [{'destination': <subnet1>, 'gateway': <ip1>},
                {'destination': <subnet2>, 'gateway': <ip2>}]
            list of strings:
                ['destination=<subnet1>,gateway=<ip1>',
                'destination=<subnet2>,gateway=<ip2>']
        no_route (bool):
        fixed_ips (list|tuple|str|dict): If list, it could be a list of dict
        or strings
            list of dict:
                [{'subnet': <subnet1>, 'ip-address': <ip1>}, {'subnet':
                <subnet2>, 'ip-address': <ip2>}]
            list of strings:
                ['subnet=<subnet1>,ip-address=<ip1>', 'subnet=<subnet2>,
                ip-address=<ip2>']
        tags (list\tuple): list of strings
        no_tag (bool):
        qos_policy (str):
        no_qos_policy (bool):
        ha (bool):
        distributed (bool):
        name (str):
        description (str):
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns:

    """
    args_dict = {
        '--name': name,
        '--description': description,
        '--enable': True if enable else None,
        '--disable': True if enable is False else None,
        '--distributed': True if distributed else None,
        '--centralized': True if distributed is False else None,
        '--route': routes,
        '--no-route': True if no_route else None,
        '--ha': True if ha else None,
        '--no-ha': True if ha is False else None,
        '--external-gateway': external_gateway,
        '--fixed-ip': fixed_ips,
        '--enable-snat': True if enable_snat else None,
        '--disable-snat': True if enable_snat is False else None,
        '--qos-policy': qos_policy,
        '--no-qos-policy': True if no_qos_policy else None,
        '--tag': tags,
        '--no-tag': True if no_tag else None,
    }
    args = common.parse_args(args_dict, repeat_arg=True)
    if not args:
        raise ValueError("No parameters provided to set router")

    if not router:
        router = get_tenant_router(con_ssh=con_ssh)

    LOG.info("Setting router {} with args: {}".format(router, args))
    args = '{} {}'.format(args, router)
    code, out = cli.openstack('router set', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, out

    LOG.info("Router {} set successfully".format(router))
    return 0, router


def unset_router(router_id=None, external_gateway=None, routes=None,
                 qos_policy=None, tag=None, all_tag=None,
                 fail_ok=False, con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Unset router with given parameters
    Args:
        router_id (str|None):
        external_gateway (bool):
        qos_policy (bool):
        tag (str):
        all_tag (bool):
        fail_ok:
        con_ssh:
        auth_info:
        routes (list): list of dict or string.
            list of dict:
                [{'destination': <subnet1>, 'gateway': <ip1>},
                {'destination': <subnet2>, 'gateway': <ip2>}]
            list of strings:
                ['destination=<subnet1>,gateway=<ip1>',
                'destination=<subnet2>,gateway=<ip2>']
    Returns:

    """
    args_dict = {
        '--route': routes,
        '--external-gateway': external_gateway,
        '--qos-polity': qos_policy,
        '--tag': tag,
        '--all-tag': all_tag
    }
    args = common.parse_args(args_dict, repeat_arg=True)
    if not args:
        raise ValueError("No parameter specified to unset")

    if not router_id:
        router_id = get_tenant_router(con_ssh=con_ssh)

    LOG.info("Unsetting router {} with args: {}".format(router_id, args))
    args = '{} {}'.format(args, router_id)
    code, output = cli.openstack('router unset', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "Router {} unset successfully".format(router_id)
    LOG.info(msg)
    return 0, msg


def get_router_ext_gateway_info(router_id=None, auth_info=None, con_ssh=None):
    """
    Get router's external gateway info as a dictionary

    Args:
        router_id (str):
        auth_info (dict|None):
        con_ssh (SSHClient):

    Returns (dict): external gateway info as a dict.
        Examples:  {"network_id": "55e5967a-2138-4f27-a17c-d700af1c2429",
                    "enable_snat": True,
                    "external_fixed_ips": [{"subnet_id":
                    "892d3ad8-9cbc-46db-88f3-84e151bbc116",
                                            "ip_address": "192.168.9.3"}]
                    }
    """
    return get_router_values(router_id=router_id,
                             fields='external_gateway_info',
                             con_ssh=con_ssh,
                             auth_info=auth_info)[0]


def set_router_gateway(router_id=None, external_net=None, enable_snat=False,
                       fixed_ips=None, fail_ok=False,
                       auth_info=Tenant.get('admin'), con_ssh=None,
                       clear_first=False):
    """
    Set router gateway with given snat, ip settings.

    Args:
        router_id (str): id of the router to set gateway for. If None,
        tenant router for Primary tenant will be used.
        external_net (str): id of the external network for getting the gateway
        enable_snat (bool): whether to enable SNAT.
        fixed_ips (str|None|list|tuple): ip address(es) on external gateway
        fail_ok (bool):
        auth_info (dict): auth info for running the router-gateway-set cli
        con_ssh (SSHClient):
        clear_first (bool): Whether to clear the router gateway first if
        router already has a gateway set

    Returns (tuple): (rtn_code (int), message (str))    scenario 1,2,3,
    4 only returns if fail_ok=True
        - (0, "Router gateway is successfully set.")
        - (1, <stderr>)     -- cli is rejected

    """
    # Process args
    if fixed_ips:
        if isinstance(fixed_ips, str):
            fixed_ips = (fixed_ips,)
        fixed_ips = [{'ip-address': fixed_ip} for fixed_ip in fixed_ips]
    if not router_id:
        router_id = get_tenant_router(con_ssh=con_ssh)
    if not external_net:
        external_net = \
            get_networks(con_ssh=con_ssh, external=True, auth_info=auth_info)[0]

    # Clear first if gateway already set
    if clear_first and get_router_ext_gateway_info(router_id,
                                                   auth_info=auth_info,
                                                   con_ssh=con_ssh):
        clear_router_gateway(router_id=router_id, check_first=False,
                             auth_info=auth_info, con_ssh=con_ssh)

    return set_router(router_id, external_gateway=external_net,
                      enable_snat=enable_snat, fixed_ips=fixed_ips,
                      con_ssh=con_ssh, auth_info=auth_info, fail_ok=fail_ok)


def clear_router_gateway(router_id=None, fail_ok=False,
                         auth_info=Tenant.get('admin'), con_ssh=None,
                         check_first=True):
    """
    Clear router gateway

    Args:
        router_id (str): id of router to clear gateway for. If None, tenant
        router for primary tenant will be used.
        fail_ok (bool):
        auth_info (dict): auth info for running the router-gateway-clear cli
        con_ssh (SSHClient):
        check_first (bool): whether to check if gateway is set for given
        router before clearing

    Returns (tuple): (rtn_code (int), message (str))
        - (0, "Router gateway is successfully cleared.")
        - (1, <stderr>)    -- cli is rejected
        - (2, "Failed to clear gateway for router <router_id>")

    """
    if router_id is None:
        router_id = get_tenant_router(con_ssh=con_ssh, auth_info=auth_info)

    if check_first and not get_router_ext_gateway_info(router_id,
                                                       con_ssh=con_ssh,
                                                       auth_info=auth_info):
        msg = "No gateway found for router. Do nothing."
        LOG.info(msg)
        return -1, msg

    return unset_router(router_id=router_id, external_gateway=True,
                        fail_ok=fail_ok, con_ssh=con_ssh,
                        auth_info=auth_info)


def get_router_external_gateway_ips(router_id, auth_info=None, con_ssh=None):
    """
    Get router external gateway fixed ips
    Args:
        router_id:
        auth_info:
        con_ssh:

    Returns (list): list of ip addresses

    """
    ext_gateway_info = get_router_ext_gateway_info(router_id,
                                                   auth_info=auth_info,
                                                   con_ssh=con_ssh)
    fixed_ips = []
    if ext_gateway_info:
        fixed_ips = ext_gateway_info['external_fixed_ips']
        fixed_ips = [fixed_ip['ip_address'] for fixed_ip in fixed_ips if
                     fixed_ip.get('ip_address', '')]

    return fixed_ips


def get_router_host(router=None, auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get router host
    Args:
        router (str|None):
        auth_info:
        con_ssh:

    Returns (str):

    """
    if not router:
        router = get_tenant_router(con_ssh=con_ssh, auth_info=auth_info)

    return get_network_agents(router=router, field='Host', con_ssh=con_ssh,
                              auth_info=auth_info)[0]


def set_router_mode(router_id=None, distributed=None, ha=None,
                    enable_on_failure=True, fail_ok=False,
                    auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Update router to distributed or centralized

    Args:
        router_id (str): id of the router to update
        distributed (bool|None): True if set to distributed, False if set to
            centralized
        ha (bool|None)
        enable_on_failure (bool): whether to set admin state up if updating
        router failed
        fail_ok (bool): whether to throw exception if cli got rejected
        auth_info (dict):
        con_ssh (SSHClient):

    Returns:

    """
    router_mode = []
    if distributed is not None:
        router_mode.append('distributed' if distributed else 'centralized')
    if ha is not None:
        router_mode.append('ha' if ha else 'no-ha')

    if not router_mode:
        raise ValueError("Distributed or ha has to be specified")

    router_mode = ' and '.join(router_mode)
    LOG.info("Disable router {} and set it to {} mode".format(router_id,
                                                              router_mode))
    try:
        code, output = set_router(router=router_id, distributed=distributed,
                                  ha=ha, enable=False, fail_ok=fail_ok,
                                  con_ssh=con_ssh, auth_info=auth_info)
    except (exceptions.TiSError, pexpect.ExceptionPexpect):
        if enable_on_failure:
            set_router(router=router_id, enable=True, con_ssh=con_ssh,
                       auth_info=auth_info)
        raise

    LOG.info("Re-enable router after set to {}".format(router_mode))
    set_router(router=router_id, enable=True, con_ssh=con_ssh,
               auth_info=auth_info)

    if code > 0:
        return 1, output

    fields = ('distributed', 'ha')
    expt_values = (distributed, ha)
    post_values = get_router_values(router_id, fields, auth_info=auth_info,
                                    con_ssh=con_ssh)

    for i in range(len(fields)):
        field = fields[i]
        post_value = post_values[i]
        expt_value = expt_values[i]
        if expt_value and post_value != expt_value:
            msg = "Router {} {} is {} instead of {}".format(router_id, field,
                                                            post_value,
                                                            expt_value)
            raise exceptions.NeutronError(msg)

    succ_msg = "Router is successfully updated to distributed={}".format(
        distributed)
    LOG.info(succ_msg)
    return 0, succ_msg


def get_networks_on_providernet(providernet, segment=None, external=None,
                                field='id',
                                con_ssh=None, auth_info=Tenant.get('admin'),
                                name=None, net_id=None,
                                strict=True, regex=False, exclude=False):
    """

    Args:
        providernet(str):
        segment (int|None)
        external (bool|None)
        field(str): 'id' or 'name'
        con_ssh (SSHClient):
        auth_info (dict):
        name
        net_id
        strict (bool)
        regex (bool)
        exclude (bool): whether to return networks that are NOT on given
        providernet

    Returns (list): list of networks
    """
    if not providernet:
        raise ValueError("No providernet_id provided.")

    return get_networks(field=field, provider_physical_network=providernet,
                        provider_setment=segment,
                        external=external, name=name, net_id=net_id,
                        strict=strict, regex=regex, exclude=exclude,
                        con_ssh=con_ssh, auth_info=auth_info)


def get_eth_for_mac(ssh_client, mac_addr, timeout=VMTimeout.IF_ADD,
                    vshell=False):
    """
    Get the eth name for given mac address on the ssh client provided
    Args:
        ssh_client (SSHClient): usually a vm_ssh
        mac_addr (str): such as "fa:16:3e:45:0d:ec"
        timeout (int): max time to wait for the given mac address appear in
        ip addr
        vshell (bool): if True, get eth name from "vshell port-list"

    Returns (str): The first matching eth name for given mac. such as "eth3"

    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not vshell:
            if mac_addr in ssh_client.exec_cmd('ip addr'.format(mac_addr))[1]:
                code, output = ssh_client.exec_cmd(
                    'ip addr | grep --color=never -B 1 "{}"'.format(mac_addr))
                # sample output:
                # 7: eth4: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state
                # DOWN qlen 1000
                # link/ether 90:e2:ba:60:c8:08 brd ff:ff:ff:ff:ff:ff

                return output.split(sep=':')[1].strip()
        else:
            code, output = ssh_client.exec_cmd(
                'vshell port-list | grep {}'.format(mac_addr))
            # |uuid|id|type|name|socket|admin|oper|mtu|mac-address|pci
            # -address|network-uuid|network-name
            return output.split(sep='|')[4].strip()
        time.sleep(1)
    else:
        LOG.warning(
            "Cannot find provided mac address {} in 'ip addr'".format(mac_addr))
        return ''


def _get_interfaces_via_vshell(ssh_client, net_type='internal'):
    """
    Get interface uuids for given network type
    Args:
        ssh_client (SSHClient):
        net_type: 'data', 'mgmt', or 'internal'

    Returns (list): interface uuids

    """
    LOG.info(
        "Getting {} interface-uuid via vshell address-list".format(net_type))
    table_ = table_parser.table(
        ssh_client.exec_cmd('vshell address-list', fail_ok=False)[1])
    interfaces = table_parser.get_values(
        table_, 'interface-uuid', regex=True,
        address=Networks.get_nenutron_net_patterns(net_type=net_type)[1])

    return interfaces


__PING_LOSS_MATCH = re.compile(PING_LOSS_RATE)


def ping_server(server, ssh_client, num_pings=5, timeout=60, check_interval=5,
                fail_ok=False, vshell=False, interface=None, retry=0,
                net_type='internal'):
    """

    Args:
        server (str): server ip to ping
        ssh_client (SSHClient): ping from this ssh client
        num_pings (int):
        timeout (int): max time to wait for ping response in seconds
        check_interval (int): seconds in between retries
        fail_ok (bool): whether to raise exception if packet loss rate is 100%
        vshell (bool): whether to ping via 'vshell ping' cmd
        interface (str): interface uuid. vm's internal interface-uuid will be
        used when unset
        retry (int):
        net_type (str): 'mgmt', 'data', 'internal', or 'external', only used
        for vshell=True and interface=None

    Returns (tuple): (<packet_loss_rate (0-100)> (int),
    <transmitted_packet_count>(int))

    """
    LOG.info('Ping {} from host {}'.format(server, ssh_client.host))
    output = packet_loss_rate = None
    for i in range(max(retry + 1, 0)):
        if not vshell:
            cmd = 'ping -c {} {}'.format(num_pings, server)
            code, output = ssh_client.exec_cmd(cmd=cmd, expect_timeout=timeout,
                                               fail_ok=True)
            if code != 0:
                packet_loss_rate = 100
            else:
                packet_loss_rate = __PING_LOSS_MATCH.findall(output)[-1]
        else:
            if not interface:
                interface = _get_interfaces_via_vshell(ssh_client,
                                                       net_type=net_type)[0]
            cmd = 'vshell ping --count {} {} {}'.format(num_pings, server,
                                                        interface)
            code, output = ssh_client.exec_cmd(cmd=cmd, expect_timeout=timeout)
            if code != 0:
                packet_loss_rate = 100
            else:
                if "ERROR" in output:
                    # usually due to incorrectly selected interface (no route
                    # to destination)
                    raise exceptions.NeutronError(
                        "vshell ping rejected, output={}".format(output))
                packet_loss_rate = re.findall(VSHELL_PING_LOSS_RATE, output)[-1]

        packet_loss_rate = int(packet_loss_rate)
        if packet_loss_rate < 100:
            if packet_loss_rate > 0:
                LOG.warning("Some packets dropped when ping from {} ssh "
                            "session to {}. Packet loss rate: {}%".
                            format(ssh_client.host, server, packet_loss_rate))
            else:
                LOG.info("All packets received by {}".format(server))
            break

        LOG.info("retry in 3 seconds")
        time.sleep(3)
    else:
        msg = "Ping from {} to {} failed.".format(ssh_client.host, server)
        LOG.warning(msg)
        if not fail_ok:
            raise exceptions.VMNetworkError(msg)

    untransmitted_packets = re.findall(r"(\d+) packets transmitted,", output)
    if untransmitted_packets:
        untransmitted_packets = int(num_pings) - int(untransmitted_packets[0])
    else:
        untransmitted_packets = num_pings

    return packet_loss_rate, untransmitted_packets


def get_pci_vm_network(pci_type='pci-sriov', net_name=None, strict=False,
                       con_ssh=None, auth_info=Tenant.get('admin'),
                       rtn_all=False):
    """

    Args:
        pci_type (str|tuple|list):
        net_name:
        strict:
        con_ssh:
        auth_info:
        rtn_all

    Returns (tuple|list): None if no network for given pci type; 2 nets(list)
    if CX nics; 1 net otherwise.

    """
    if isinstance(pci_type, str):
        pci_type = [pci_type]

    hosts_and_pnets = host_helper.get_hosts_and_pnets_with_pci_devs(
        pci_type=pci_type, up_hosts_only=True,
        con_ssh=con_ssh, auth_info=auth_info)
    if not hosts_and_pnets:
        if rtn_all:
            return [], None
        return []

    # print("hosts and pnets: {}".format(hosts_and_pnets))

    host = list(hosts_and_pnets.keys())[0]
    pnet_name = hosts_and_pnets[host][0]
    nets = list(set(get_networks_on_providernet(pnet_name, field='name')))

    nets_list_all_types = []
    for pci_type_ in pci_type:
        if pci_type_ == 'pci-sriov':
            # Exclude network on first segment
            # The switch is setup with untagged frames for the first segment
            # within the range.
            # This is suitable for PCI passthrough, but would not work for SRIOV
            first_segs = get_first_segments_of_pnet_ranges(pnet_name,
                                                           con_ssh=con_ssh)
            first_segs = [seg for seg in first_segs if seg > 20]
            for seg in first_segs:
                untagged_net = get_net_on_segment(pnet_name, seg_id=seg,
                                                  field='name', con_ssh=con_ssh)
                if untagged_net in nets:
                    LOG.info(
                        "{} is on first segment of {} range with untagged "
                        "frames. Remove for sriov.".
                        format(untagged_net, pnet_name))
                    nets.remove(untagged_net)

        # print("pnet: {}; Nets: {}".format(pnet_name, nets))
        nets_for_type = _get_preferred_nets(nets=nets, net_name=net_name,
                                            strict=strict)
        if not nets_for_type:
            nets_list_all_types = []
            break

        nets_list_all_types.append(nets_for_type)

    final_nets = []
    cx_for_pcipt = False
    if nets_list_all_types:
        final_nets = set(nets_list_all_types[0])
        for nets_ in nets_list_all_types[1:]:
            final_nets.intersection_update(set(nets_))
        final_nets = list(final_nets)
        if final_nets:
            if 'pci-passthrough' in pci_type:

                port = host_helper.get_host_interfaces(host, field='ports',
                                                       net_type=pci_type)[0]
                host_nic = host_helper.get_host_ports(host, field='device type',
                                                      **{'name': port})[0]
                if re.match(MELLANOX4, host_nic):
                    cx_for_pcipt = True

            if not rtn_all:
                final_nets = final_nets[0:2] if cx_for_pcipt else final_nets[-1]

    if rtn_all:
        final_nets = final_nets, cx_for_pcipt

    return final_nets


def get_network_segment_ranges(field=('Minimum ID', 'Maximum ID'), long=False,
                               shared=None, physical_network=None,
                               network_type=None, project_id=None,
                               auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get network segment ranges info
    Args:
        field (str|tuple|list):
        long (bool|None): cli parameter --long
        shared (bool|None): return value filter
        physical_network (str|None): return value filter
        network_type (str|None): return value filter
        project_id (str|None): return value filter
        auth_info:
        con_ssh:

    Returns (list of str|tuple): return list of str if rtn_val is str,
    otherwise rtn list of tuples

    """

    table_ = table_parser.table(
        cli.openstack('network segment range list', '--long' if long else '',
                      ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    kwargs = {
        'Shared': shared,
        'Physical Network': physical_network,
        'Network Type': network_type,
        'Project ID': project_id,
    }
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    vals = table_parser.get_multi_values(table_, field, evaluate=True, **kwargs)
    if not isinstance(field, str):
        vals = zip(*vals)

    return vals


def get_first_segments_of_pnet_ranges(providernet, con_ssh=None,
                                      auth_info=Tenant.get('admin')):
    """
    Get first segment id within the range of given providernet
    Args:
        providernet (str): physical network name
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (list of int): list of min segment for each range of the physical
    network

    """
    min_segments = get_network_segment_ranges(field='Minimum ID',
                                              physical_network=providernet,
                                              auth_info=auth_info,
                                              con_ssh=con_ssh)

    return min_segments


def get_net_on_segment(providernet, seg_id, field='name', con_ssh=None,
                       auth_info=Tenant.get('admin')):
    """
    Get network name on given prvidernet with specified segment id
    Args:
        providernet (str): pnet name or id
        seg_id (int|list|tuple): segment id(s)
        field (str): 'name' or 'id'
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (str|None): network id/name or None if no network on given seg id

    """
    nets = get_networks_on_providernet(providernet=providernet, field=field,
                                       con_ssh=con_ssh, segment=seg_id,
                                       auth_info=auth_info)

    net = nets[0] if nets else None
    return net


def _get_preferred_nets(nets, net_name=None, strict=False):
    specified_nets = []
    nets_dict = {
        'internal': [],
        'mgmt': [],
        'data': []
    }

    for net in nets:
        if net_name:
            if strict:
                if re.match(net_name, net):
                    specified_nets.append(net)
            else:
                if re.search(net_name, net):
                    specified_nets.append(net)
        else:
            # If net_name unspecified:
            for net_type, nets_found in nets_dict.items():
                net_name_pattern = Networks.get_nenutron_net_patterns(net_type)[
                    0]
                if net_name_pattern and re.search(net_name_pattern, net):
                    nets_found.append(net)
                    break
            else:
                LOG.warning("Unknown network: {}. Ignore.".format(net))

    for nets_ in (specified_nets, nets_dict['internal'], nets_dict['data'],
                  nets_dict['mgmt']):
        if nets_:
            nets_counts = Counter(nets_)
            nets_ = sorted(nets_counts.keys(), key=nets_counts.get,
                           reverse=True)
            LOG.info("Preferred networks selected: {}".format(nets_))
            return nets_


def create_port(net_id, name, project=None, fixed_ips=None, device_id=None,
                device_owner=None, port_security=None,
                enable_port=None, mac_addr=None, vnic_type=None,
                security_groups=None, no_security_groups=None,
                qos_pol=None, allowed_addr_pairs=None, dns_name=None, tag=None,
                no_tag=None,
                host_id=None, wrs_vif=None, fail_ok=False, auth_info=None,
                con_ssh=None, cleanup=None):
    """
    Create a port on given network

    Args:
        net_id (str): network id to create port for
        name (str): name of the new port
        project (str): tenant name. such as tenant1, tenant2
        fixed_ips (list|tuple|dict|None): e.g., [{"subnet_id": <SUBNET_1>,
        "ip-address"=<IP_1>}, {"ip-address": <IP_2>}
        device_id (str): device id of this port
        device_owner (str): Device owner of this port
        port_security (None|bool):
        enable_port (bool|None):
        mac_addr (str):  MAC address of this port
        vnic_type: one of the: <direct | direct-physical | macvtap | normal |
        baremetal>
        security_groups (str|list): Security group(s) associated with the port
        no_security_groups (bool): Associate no security groups with the port
        qos_pol (str):  Attach QoS policy ID or name to the resource
        allowed_addr_pairs (str|list):  Allowed address pair associated with
        the port.
                e.g., "ip_address=IP_ADDR[,mac_address=MAC_ADDR]"
        dns_name (str):  Assign DNS name to the port (requires DNS
        integration extension)
        host_id (str)
        tag (str|None)
        no_tag (str|None)
        wrs_vif
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):
        cleanup (None|str)

    Returns (tuple): (<rtn_code>, <err_msg|port_id>)
        (0, <port_id>)  - port created successfully
        (1, <std_err>)  - CLI rejected
        (2, "Network ID for created port is not as specified.")     - post
        create check fail

    """
    LOG.info("Creating port on network {}".format(net_id))
    if not net_id:
        raise ValueError("network id is required")
    tenant_id = \
        keystone_helper.get_projects(field='ID', name=project,
                                     con_ssh=con_ssh)[0] if project else None

    args_dict = {
        '--no-security-groups': no_security_groups,
        '--enable-port-security': True if port_security else None,
        '--disable-port-security': True if port_security is False else None,
        '--tenant-id': tenant_id,
        '--device-id': device_id,
        '--device-owner': device_owner,
        '--mac-address': mac_addr,
        '--vnic-type': vnic_type,
        '--host': host_id,
        # '--binding-profile':
        '--enable': True if port_security else None,
        '--disable': True if enable_port is False else None,
        '--qos-policy': qos_pol,
        '--dns-name': dns_name,
        '--binding-profile vif_model': wrs_vif,
        '--fixed-ip': fixed_ips,
        '--allowed-address-pair': allowed_addr_pairs,
        '--security-group': security_groups,
        '--tag': tag,
        '--no-tag': no_tag
    }

    args = common.parse_args(args_dict=args_dict, repeat_arg=True, vals_sep=',')
    args = '--network={} {} {}'.format(net_id, args, name)

    code, output = cli.openstack('port create', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    port_tab = table_parser.table(output)
    port_net_id = table_parser.get_value_two_col_table(port_tab, 'network_id')
    port_id = table_parser.get_value_two_col_table(port_tab, 'id')
    if port_id and cleanup:
        ResourceCleanup.add('port', port_id)

    if code == 1:
        return code, output

    if not net_id == port_net_id:
        err_msg = "Network ID for created port is not as specified. Expt:{}; " \
                  "Actual: {}".format(net_id, port_net_id)
        if fail_ok:
            LOG.warning(err_msg)
            return 2, port_id

    succ_msg = "Port {} is successfully created on network {}".format(port_id,
                                                                      net_id)
    LOG.info(succ_msg)
    return 0, port_id


def delete_port(port_id, fail_ok=False, auth_info=Tenant.get('admin'),
                con_ssh=None):
    """
    Delete given port
    Args:
        port_id (str):
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple): (<rtn_code>, <msg>)
        (0, "Port <port_id> is successfully deleted")
        (1, <std_err>)  - delete port cli rejected
        (2, "Port <port_id> still exists after deleting")   - post deletion
        check failed

    """
    LOG.info("Deleting port: {}".format(port_id))
    if not port_id:
        msg = "No port specified"
        LOG.warning(msg)
        return -1, msg

    code, output = cli.openstack('port delete', port_id, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    existing_ports = get_ports(field='id', auth_info=auth_info, con_ssh=con_ssh)
    if port_id in existing_ports:
        err_msg = "Port {} still exists after deleting".format(port_id)
        if fail_ok:
            LOG.warning(err_msg)
            return 2, err_msg
        raise exceptions.NeutronError(err_msg)

    succ_msg = "Port {} is successfully deleted".format(port_id)
    LOG.info(succ_msg)
    return 0, succ_msg


def set_port(port_id, name=None, fixed_ips=None, no_fixed_ip=None,
             device_id=None, device_owner=None,
             port_security=None, enable_port=None, mac_addr=None,
             vnic_type=None, wrs_vif=None,
             security_groups=None, no_security_groups=None, qos_pol=None,
             host_id=None,
             allowed_addr_pairs=None, no_allowed_addr_pairs=None, dns_name=None,
             description=None,
             tag=None, no_tag=None, fail_ok=False, auth_info=None,
             con_ssh=None):
    args_dict = {
        '--description': description,
        '--device': device_id,
        '--mac-address': mac_addr,
        '--device-owner': device_owner,
        '--vnic-type': vnic_type,
        '--host': host_id,
        '--dns-name': dns_name,
        '--enable': enable_port,
        '--disable': True if enable_port is False else None,
        '--enable-port-security': port_security,
        '--disable-port-security': True if port_security is False else None,
        '--name': name,
        '--fixed-ip': fixed_ips,
        '--no-fixed-ip': no_fixed_ip,
        '--qos-policy': qos_pol,
        '--security-group': security_groups,
        '--no-security-group': no_security_groups,
        '--allowed-address': allowed_addr_pairs,
        '--no-allowed-address': no_allowed_addr_pairs,
        '--tag': tag,
        '--no-tag': no_tag,
        '--binding-profile vif_model': wrs_vif,
    }
    args = '{} {}'.format(
        common.parse_args(args_dict, repeat_arg=True, vals_sep=','), port_id)
    code, out = cli.openstack('port set', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code != 0:
        return code, out

    msg = "Port {} is updated.".format(port_id)
    LOG.info(msg)
    return code, msg


def __convert_ip_subnet(line):
    ip_addr = subnet = ''
    if 'ip_address' in line:
        ip_addrs = re.findall("ip_address=\'(.*)\',", line)
        if ip_addrs:
            ip_addr = ip_addrs[0]
        subnets = re.findall("subnet_id=\'(.*)\'", line)
        if subnets:
            subnet = subnets[0]

    return {'ip_address': ip_addr, 'subnet_id': subnet}


def get_ports(field='id', network=None, router=None, server=None, project=None,
              fixed_ips=None, long=False, mac=None,
              port_id=None, port_name=None, auth_info=Tenant.get('admin'),
              con_ssh=None, strict=False):
    """
    Get a list of ports with given arguments
    Args:
        field (str|list|tuple): openstack port list table header(s). 'ID',
        'NAME', 'MAC Address', 'Fixed IP Addresses'
        network (str|None)
        router (str|None)
        server (str|None)
        project (str|None)
        mac (str|None)
        fixed_ips (list|tuple|dict|None) e.g., ({'subnet': <subnet1>,
        'ip-address': <ip1>}, {'ip-address': <ip2>})
        long (bool):
        port_id (str): id of the port
        port_name (str): name of the port
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list):

    """
    optional_args = {
        '--fixed-ip': fixed_ips,
        '--project': project,
        '--network': network,
        '--router': router,
        '--server': server,
        '--mac-address': mac,
        '--long': long,
    }
    args_str = common.parse_args(args_dict=optional_args, repeat_arg=True,
                                 vals_sep=',')
    table_ = table_parser.table(
        cli.openstack('port list', args_str, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    filters = {}
    if port_id:
        filters['id'] = port_id
    elif port_name:
        filters['name'] = port_name

    convert = False
    if isinstance(field, str):
        convert = True
        field = (field,)

    res = []
    for header in field:
        ports_info = table_parser.get_values(table_, header, strict=strict,
                                             merge_lines=False, **filters)
        if header.lower() == 'fixed ip addresses':
            values = []
            for port_info in ports_info:
                if isinstance(port_info, str):
                    port_info = [port_info]
                port_info = [__convert_ip_subnet(line=line) for line in
                             port_info]
                values.append(port_info)
            ports_info = values
        res.append(ports_info)

    if convert:
        res = res[0]
    return res


def get_port_values(port, fields=('binding_vnic_type', 'mac_address'),
                    con_ssh=None, auth_info=None):
    """
    Get port info via openstack port show
    Args:
        port (str):
        fields (str|list|tuple):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (list): return list of list if field is fixed_ips e.g.,
        fields = ('id', 'fixed_ips')
        returns: [<port_id>, [{'ip_address': <ip1>, 'subnet_id': <subnet1>},
        ..]]

    """
    if isinstance(fields, str):
        fields = (fields,)

    table_ = table_parser.table(
        cli.openstack('port show', port, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    values = []
    for field in fields:
        value = table_parser.get_value_two_col_table(table_, field)
        if field == 'fixed_ips':
            if isinstance(value, str):
                value = [value]
            value = [__convert_ip_subnet(line) for line in value]
        values.append(value)

    return values


def get_pci_devices_info(class_id, con_ssh=None, auth_info=None):
    """
    Get PCI devices with nova device-list/show.

    As in load "2017-01-17_22-01-49", the known supported devices are:
        Coleto Creek PCIe Co-processor  Device Id: 0443 Vendor Id:8086

    Args:
        class_id (str|list): Some possible values:
            0b4000 (Co-processor),
            0c0330 (USB controller),
            030000 (VGA compatible controller)
        con_ssh:
        auth_info:

    Returns (dict): nova pci devices dict.
        Format: {<pci_alias1>: {<host1>: {<nova device-show row dict for
        host>}, <host2>: {...}},
                 <pci_alias2>: {...},
                 ...}
        Examples:
            {'qat-dh895xcc-vf': {'compute-0': {'Device ID':'0443','Class
            Id':'0b4000', ...} 'compute-1': {...}}}

    """
    table_ = table_parser.table(
        cli.nova('device-list', ssh_client=con_ssh, auth_info=auth_info)[1])
    table_ = table_parser.filter_table(table_, **{'class_id': class_id})
    LOG.info('output of nova device-list for {}: {}'.format(class_id, table_))

    devices = table_parser.get_column(table_, 'PCI Alias')
    LOG.info('PCI Alias from device-list:{}'.format(devices))

    nova_pci_devices = {}
    for alias in devices:
        table_ = table_parser.table(cli.nova('device-show {}'.format(alias))[0])
        # LOG.debug('output from nova device-show for device-id:{}\n{
        # }'.format(alias, table_))

        table_dict = table_parser.row_dict_table(table_, key_header='Host',
                                                 unique_key=True,
                                                 lower_case=False)
        nova_pci_devices[alias] = table_dict
        # {'qat-dh895xcc-vf': {'compute-0': {'Device ID':'0443','Class
        # Id':'0b4000', ...} 'compute-1': {...}}}

    LOG.info('nova_pci_devices: {}'.format(nova_pci_devices))

    return nova_pci_devices


def get_pci_device_configured_vfs_value(device_id, con_ssh=None,
                                        auth_info=None):
    """
    Get PCI device configured vfs value for given device id

    Args:
        device_id (str):  device vf id
        con_ssh:
        auth_info:

    Returns:
        str :

    """
    _table = table_parser.table(
        cli.nova('device-list', ssh_client=con_ssh, auth_info=auth_info)[1])
    LOG.info('output of nova device-list:{}'.format(_table))
    _table = table_parser.filter_table(_table, **{'Device Id': device_id})
    return table_parser.get_column(_table, 'pci_vfs_configured')[0]


def get_pci_device_used_vfs_value(device_id, con_ssh=None, auth_info=None):
    """
    Get PCI device used number of vfs value for given device id

    Args:
        device_id (str):  device vf id
        con_ssh:
        auth_info:

    Returns:
        str :

    """
    _table = table_parser.table(
        cli.nova('device-list', ssh_client=con_ssh, auth_info=auth_info)[1])
    LOG.info('output of nova device-list:{}'.format(_table))
    _table = table_parser.filter_table(_table, **{'Device Id': device_id})
    LOG.info('output of nova device-list:{}'.format(_table))
    return table_parser.get_column(_table, 'pci_vfs_used')[0]


def get_pci_device_vfs_counts_for_host(
        host, device_id=None, fields=('pci_vfs_configured', 'pci_vfs_used'),
        con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get PCI device used number of vfs value for given device id

    Args:
        host (str): compute hostname
        device_id (str):  device vf id
        fields (tuple|str|list)
        con_ssh:
        auth_info:

    Returns:
        list

    """
    if device_id is None:
        device_id = get_pci_device_list_values(field='Device Id',
                                               con_ssh=con_ssh,
                                               auth_info=auth_info)[0]

    table_ = table_parser.table(
        cli.nova('device-show {}'.format(device_id), ssh_client=con_ssh,
                 auth_info=auth_info)[1])
    LOG.debug(
        'output from nova device-show for device-id:{}\n{}'.format(device_id,
                                                                   table_))

    table_ = table_parser.filter_table(table_, host=host)
    counts = []
    if isinstance(fields, str):
        fields = [fields]

    for field in fields:
        counts.append(int(table_parser.get_column(table_, field)[0]))

    return counts


def get_pci_device_list_values(field='pci_vfs_used', con_ssh=None,
                               auth_info=Tenant.get('admin'), **kwargs):
    table_ = table_parser.table(
        cli.nova('device-list', ssh_client=con_ssh, auth_info=auth_info)[1])

    values = table_parser.get_values(table_, field, **kwargs)
    if field in ['pci_pfs_configured', 'pci_pfs_used', 'pci_vfs_configured',
                 'pci_vfs_used']:
        values = [int(value) for value in values]

    return values


def get_pci_device_list_info(con_ssh=None, header_key='pci alias',
                             auth_info=Tenant.get('admin'), **kwargs):
    table_ = table_parser.table(
        cli.nova('device-list', ssh_client=con_ssh, auth_info=auth_info)[1])
    if kwargs:
        table_ = table_parser.filter_table(table_, **kwargs)

    return table_parser.row_dict_table(table_, key_header=header_key)


def get_tenant_routers_for_vms(vms, con_ssh=None,
                               auth_info=Tenant.get('admin')):
    """
    Get tenant routers for given vms

    Args:
        vms (str|list):
        con_ssh (SSHClient):
        auth_info

    Returns (list): list of router ids

    """
    if isinstance(vms, str):
        vms = [vms]

    router_ids, router_projects = get_routers(auth_info=auth_info,
                                              con_ssh=con_ssh,
                                              field=('ID', 'Project'))
    vms_routers = []
    from keywords import vm_helper
    for i in range(len(router_ids)):
        router_project = router_projects[i]
        vms_with_router = vm_helper.get_vms(vms=vms, project=router_project,
                                            all_projects=False,
                                            auth_info=auth_info,
                                            con_ssh=con_ssh)
        if vms_with_router:
            vms_routers.append(router_ids[i])
            vms = list(set(vms) - set(vms_with_router))

        if not vms:
            break

    return vms_routers


def collect_networking_info(time_stamp, routers=None, vms=None, sep_file=None,
                            con_ssh=None):
    LOG.info("Ping tenant(s) router's external and internal gateway IPs")

    if not routers:
        if vms:
            if isinstance(vms, str):
                vms = [vms]
            routers = get_tenant_routers_for_vms(vms=vms)
        else:
            routers = get_routers(name='tenant[12]-router', regex=True,
                                  auth_info=Tenant.get('admin'),
                                  con_ssh=con_ssh)
    elif isinstance(routers, str):
        routers = [routers]

    ips_to_ping = []
    for router_ in routers:
        router_ips = get_router_subnets(router=router_, field='ip_address',
                                        con_ssh=con_ssh)
        ips_to_ping += router_ips

    res_bool, res_dict = ping_ips_from_natbox(ips_to_ping, num_pings=3,
                                              timeout=15)
    if sep_file:
        res_str = "succeeded" if res_bool else 'failed'
        content = "#### Ping router interfaces {} ####\n{}\n".format(res_str,
                                                                     res_dict)
        common.write_to_file(sep_file, content=content)

    # if ProjVar.get_var('ALWAYS_COLLECT'):
    #     common.collect_software_logs()

    hosts = host_helper.get_up_hypervisors(con_ssh=con_ssh)
    for router in routers:
        router_host = get_network_agents(field='Host', router=router,
                                         con_ssh=con_ssh)[0]
        if router_host and router_host not in hosts:
            hosts.append(router_host)
        LOG.info("Router {} is hosted on {}".format(router, router_host))

    if hosts:
        is_avs = system_helper.is_avs(con_ssh=con_ssh)
        vswitch_type = 'avs' if is_avs else 'ovs'
        LOG.info(
            "Collect {}.info for {} router(s) on router host(s): {}".format(
                vswitch_type, routers, hosts))
        for host in hosts:
            collect_vswitch_info_on_host(host, vswitch_type,
                                         collect_extra_ovs=(not is_avs),
                                         time_stamp=time_stamp,
                                         con_ssh=con_ssh)


def get_network_agents(field='Host', agent_host=None, router=None, network=None,
                       agent_type=None, long=False,
                       con_ssh=None, auth_info=Tenant.get('admin'), **kwargs):
    """
    Get network agents values from openstack network agent list
    Args:
        field (str|list|tuple):
        agent_host:
        router:
        network:
        agent_type:
        long:
        con_ssh:
        auth_info:
        **kwargs:

    Returns (list):

    """
    args_dict = {
        '--agent-type': agent_type,
        '--host': agent_host,
        '--network': network,
        '--router': router,
        '--long': long,
    }
    args = common.parse_args(args_dict)
    table_ = table_parser.table(
        cli.openstack('network agent list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, **kwargs)


def ping_ips_from_natbox(ips, natbox_ssh=None, num_pings=5, timeout=30):
    if not natbox_ssh:
        natbox_ssh = NATBoxClient.get_natbox_client()

    res_dict = {}
    for ip_ in ips:
        packet_loss_rate = ping_server(
            server=ip_, ssh_client=natbox_ssh, num_pings=num_pings,
            timeout=timeout, fail_ok=True, vshell=False)[0]
        res_dict[ip_] = packet_loss_rate

    res_bool = not any(loss_rate == 100 for loss_rate in res_dict.values())
    # LOG.error("PING RES: {}".format(res_dict))
    if res_bool:
        LOG.info("Ping successful from NatBox: {}".format(ips))
    else:
        LOG.warning("Ping unsuccessful from NatBox: {}".format(res_dict))

    return res_bool, res_dict


def collect_vswitch_info_on_host(host, vswitch_type, time_stamp,
                                 collect_extra_ovs=False, con_ssh=None):
    """

    Args:
        host (str):
        vswitch_type (str): avs or ovs
        time_stamp (str)
        collect_extra_ovs
        con_ssh

    Returns:

    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    if not time_stamp:
        time_stamp = common.get_date_in_format(ssh_client=con_ssh,
                                               date_format='%Y%m%d_%H-%M')
    con_name = con_ssh.get_hostname()
    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        # create log file for host under home dir
        # time_stamp = common.get_date_in_format(ssh_client=host_ssh,
        # date_format='%Y%m%d_%H-%M')
        test_name = ProjVar.get_var("TEST_NAME").split(sep='[')[0]
        file_name = os.path.join(HostLinuxUser.get_home(),
                                 '{}-{}-{}-vswitch.log'.format(time_stamp,
                                                               test_name, host))
        host_ssh.exec_cmd('touch {}'.format(file_name))

        # Collect vswitch logs using collect tool
        # vswitch log will be saved to /scratch/var/extra/avs.info on the
        # compute host
        host_ssh.exec_sudo_cmd('/etc/collect.d/collect_{}'.format(vswitch_type))
        vswitch_info_path = '/scratch/var/extra/{}.info'.format(vswitch_type)
        host_ssh.exec_cmd(
            r'echo -e "##### {} {}.info collected #####\n" >> {}'.format(
                host, vswitch_type, file_name),
            get_exit_code=False)
        time.sleep(1)
        host_ssh.exec_sudo_cmd(
            'cat {} >> {}'.format(vswitch_info_path, file_name),
            get_exit_code=False)
        host_ssh.exec_sudo_cmd('rm -f {}'.format(vswitch_info_path))

        if collect_extra_ovs:
            # Run a few cmds to collect more ovs info
            host_ssh.exec_cmd(r'echo -e "\n\n#### Additional ovs '
                              r'cmds on {} ####\n >> {}"'.format(host,
                                                                 file_name),
                              get_exit_code=False)
            for cmd in ('ovs-ofctl show br-int', 'ovs-ofctl dump-flows br-int',
                        'ovs-appctl dpif/dump-flows br-int'):
                host_ssh.exec_cmd(
                    r'echo -e "\n\n\n$ sudo {}" >> {}'.format(cmd, file_name))
                cmd = '{} >> {}'.format(cmd, file_name)
                host_ssh.exec_sudo_cmd(cmd, get_exit_code=False)

        host_ssh.exec_sudo_cmd('chmod 777 {}'.format(file_name))

        if host != con_name:
            host_ssh.scp_on_source(file_name,
                                   dest_user=HostLinuxUser.get_user(),
                                   dest_ip=con_name,
                                   dest_path=file_name,
                                   dest_password=HostLinuxUser.get_password(),
                                   timeout=120)

    dest_path = os.path.join(ProjVar.get_var('PING_FAILURE_DIR'),
                             os.path.basename(file_name))
    common.scp_from_active_controller_to_localhost(file_name,
                                                   dest_path=dest_path,
                                                   timeout=120)
    return dest_path


def get_pci_device_numa_nodes(hosts):
    """
    Get processors of crypto PCI devices for given hosts

    Args:
        hosts (list): list of hosts to check

    Returns (dict): host, numa_nodes map. e.g., {'compute-0': ['0'],
    'compute-1': ['0', '1']}

    """
    hosts_numa = {}
    for host in hosts:
        numa_nodes = host_helper.get_host_devices(host, field='numa_node')
        hosts_numa[host] = numa_nodes

    LOG.info("Hosts numa_nodes map for PCI devices: {}".format(hosts_numa))
    return hosts_numa


def get_pci_procs(hosts, net_type='pci-sriov'):
    """
    Get processors of pci-sriov or pci-passthrough devices for given hosts

    Args:
        hosts (list): list of hosts to check
        net_type (str): pci-sriov or pci-passthrough

    Returns (dict): host, procs map. e.g., {'compute-0': ['0'], 'compute-1':
    ['0', '1']}

    """
    hosts_procs = {}
    for host in hosts:
        ports_list = host_helper.get_host_interfaces(host, field='ports',
                                                     net_type=net_type)

        ports = []
        for port in ports_list:
            ports += port
        ports = list(set(ports))

        procs = host_helper.get_host_ports(host, field='processor',
                                           **{'name': ports})
        hosts_procs[host] = list(set(procs))

    LOG.info("Hosts procs map for {} devices: {}".format(net_type, hosts_procs))
    return hosts_procs


def wait_for_agents_healthy(hosts=None, timeout=120, fail_ok=False,
                            con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Wait for neutron agents to be alive
    Args:
        hosts (str|list): hostname(s) to check. When None, all nova
        hypervisors will be checked
        timeout (int): max wait time in seconds
        fail_ok (bool): whether to return False or raise exception when
        non-alive agents exist
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (<res>(bool), <msg>(str))
        (True, "All agents for <hosts> are alive")
        (False, "Some agents are not alive: <non_alive_rows>")
        Applicable when fail_ok=True

    """
    if hosts is None:
        hosts = host_helper.get_hypervisors(con_ssh=con_ssh,
                                            auth_info=auth_info)
    elif isinstance(hosts, str):
        hosts = [hosts]

    unhealthy_agents = None
    LOG.info("Wait for neutron agents to be alive for {}".format(hosts))
    end_time = time.time() + timeout
    while time.time() < end_time:
        alive_vals, states, agents, agent_hosts = get_network_agents(
            field=('Alive', 'State', 'Binary', 'Host'),
            host=hosts, con_ssh=con_ssh, auth_info=auth_info)

        unhealthy_agents = [i for i in
                            list(zip(agents, agent_hosts, states, alive_vals))
                            if
                            (i[-1] != ':-)' or i[-2] != 'UP')]
        if not unhealthy_agents:
            succ_msg = "All agents for {} are alive and up".format(hosts)
            LOG.info(succ_msg)
            return True, succ_msg

    msg = "Some network agents are not healthy: {}".format(unhealthy_agents)
    LOG.warning(msg)
    if fail_ok:
        return False, msg
    raise exceptions.NeutronError(msg)


def get_trunks(field='id', trunk_id=None, trunk_name=None, parent_port=None,
               strict=False,
               auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get a list of trunks with given arguments
    Args:
        field (str): any valid header of neutron trunk list table. 'id',
        'name', 'mac_address', or 'fixed_ips'
        trunk_id (str): id of the trunk
        trunk_name (str): name of the trunk
        parent_port (str): parent port of the trunk
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('network trunk list', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    kwargs = {
        'id': trunk_id,
        'name': trunk_name,
        'parent_port': parent_port,
    }
    kwargs = {k: v for k, v in kwargs.items() if v}

    trunks = table_parser.get_values(table_, field, strict=strict, regex=True,
                                     merge_lines=True, **kwargs)
    return trunks


def create_trunk(parent_port, name=None, sub_ports=None, description=None,
                 project=None, project_domain=None,
                 enable=True, fail_ok=False, con_ssh=None,
                 auth_info=Tenant.get('admin'), cleanup=None):
    """
    Create a trunk via API.
    Args:
        parent_port (str): Parent port of trunk.
        project (str|None): tenant name to create the trunk under.
        project_domain (str|None)
        name (str|None): Name of the trunk.
        enable (bool|None): Admin state of the trunk.
        sub_ports (list|tuple|dict|str|None): List of subport dictionaries in
            format
            [[<ID of neutron port for subport>,
             segmentation_type(vlan),
             segmentation_id(<VLAN tag>)] []..]
        description (str|None)
        fail_ok
        con_ssh
        auth_info
        cleanup

    Return: List with trunk's data returned from Neutron API.

    """
    if not project and auth_info and auth_info['tenant'] == 'admin':
        project = Tenant.get_primary()['tenant']

    args_dict = {
        '--description': description,
        '--parent-port': parent_port,
        '--subport': sub_ports,
        '--enable': True if enable else None,
        '--disable': True if enable is False else None,
        '--project': project,
        '--project-domain': project_domain,
    }
    args = common.parse_args(args_dict, repeat_arg=True, vals_sep=',')
    if not name:
        name = common.get_unique_name('port_trunk')

    LOG.info("Creating trunk {} with args: {}".format(name, args))
    args = '{} {}'.format(args, name)
    code, output = cli.openstack('network trunk create', args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    table_ = table_parser.table(output)
    trunk_id = table_parser.get_value_two_col_table(table_, 'id')

    if cleanup and trunk_id:
        ResourceCleanup.add('trunk', trunk_id)

    if code > 0:
        return 1, output

    succ_msg = "Trunk {} is successfully created for port {}".format(
        name, parent_port)
    LOG.info(succ_msg)
    return 0, trunk_id


def delete_trunks(trunks, fail_ok=False, auth_info=Tenant.get('admin'),
                  con_ssh=None):
    """
    Delete given trunk
    Args:
        trunks (str):
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple): (<rtn_code>, <msg>)
        (0, "Port <trunk_id> is successfully deleted")
        (1, <std_err>)  - delete port cli rejected
        (2, "trunk <trunk_id> still exists after deleting")   - post deletion
        check failed

    """
    if not trunks:
        msg = "No trunk specified"
        LOG.info(msg)
        return -1, msg

    if isinstance(trunks, str):
        trunks = [trunks]

    rtn_val = 'id' if re.match(UUID, trunks[0]) else 'name'
    existing_trunks = get_trunks(field=rtn_val, auth_info=auth_info,
                                 con_ssh=con_ssh)
    trunks = list(set(trunks) & set(existing_trunks))
    if not trunks:
        msg = "Given trunks not found on system. Do nothing."
        LOG.info(msg)
        return -1, msg

    trunks = ' '.join(trunks)
    LOG.info("Deleting trunk: {}".format(trunks))
    code, output = cli.openstack('network trunk delete', trunks,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    existing_trunks = get_trunks(field='id', auth_info=auth_info,
                                 con_ssh=con_ssh)
    undeleted_trunks = list(set(trunks) & set(existing_trunks))
    if undeleted_trunks:
        err_msg = "Trunk {} still exists after deleting".format(
            undeleted_trunks)
        if fail_ok:
            LOG.warning(err_msg)
            return 2, err_msg
        raise exceptions.NeutronError(err_msg)

    succ_msg = "Trunk {} is successfully deleted".format(trunks)
    LOG.info(succ_msg)
    return 0, succ_msg


def set_trunk(trunk, sub_ports=None, name=None, enable=None, description=None,
              fail_ok=False,
              con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Set trunk with given parameters.
    Args:
        trunk (str): Trunk id to add the subports
        sub_ports (list|tuple|str|None):
        name (str|None)
        description (str|None)
        enable (bool|None)
        fail_ok
        con_ssh
        auth_info

    Return (tuple):

    """
    args_dict = {
        '--name': name,
        '--description': description,
        '--subport': sub_ports,
        '--enable': True if enable else None,
        '--disable': True if enable is False else None,
    }

    args = common.parse_args(args_dict, repeat_arg=True, vals_sep=',')
    if not args:
        raise ValueError("Nothing specified to set")

    LOG.info("Setting trunk {} with args: {}".format(trunk, args))
    args = '{} {}'.format(args, trunk)
    code, output = cli.openstack('network trunk set', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, output

    msg = 'Trunk {} is set successfully'.format(trunk)
    LOG.info(msg)
    return 0, msg


def unset_trunk(trunk, sub_ports, fail_ok=False, con_ssh=None,
                auth_info=Tenant.get('admin')):
    """
    Remove subports from a trunk via API.
    Args:
        trunk: Trunk id to remove the subports from
        sub_ports (list|str|tuple)
        fail_ok
        con_ssh
        auth_info

    Return: list with return code and msg

    """
    args = {'--subport': sub_ports}
    args = '{} {}'.format(common.parse_args(args, repeat_arg=True), trunk)

    LOG.info("Unsetting trunk: {}".format(args))
    code, output = cli.openstack('network trunk unset', args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = 'Subport(s) removed from trunk {} successfully: {}'.format(trunk,
                                                                     sub_ports)
    LOG.info(msg)
    return 0, msg


def get_networks(field='ID', long=False, full_name=None, external=None,
                 enabled=None, project=None,
                 project_domain=None, shared=None, status=None,
                 providernet_type=None, provider_physical_network=None,
                 provider_setment=None, agent=None, tags=None, any_tags=None,
                 not_tags=None, not_any_tags=None,
                 name=None, subnets=None, net_id=None, strict=False,
                 regex=False, exclude=False, auth_info=None,
                 con_ssh=None):
    """
    Get networks based on given criteria.

    Args:
        field (str|tuple|list)
        long (bool|None):
        full_name (str|None):
        external (bool|None):
        enabled (bool|None):
        project (str|None):
        project_domain (str|None):
        shared (bool|None):
        status (str|None):
        providernet_type (str|None):
        provider_physical_network (str|None):
        provider_setment (str|None):
        agent (str|None):
        tags (list|tuple|str|None):
        any_tags (list|tuple|str|None):
        not_tags (list|tuple|str|None):
        not_any_tags (list|tuple|str|None):
        name (str): partial/full name of network, can be regex. This will be
        used to filter networks after cmd executed
        subnets (str|list\tuple): post filter
        net_id (str|None): post filter
        strict (bool): whether to perform strict search on given name and
        subnets
        regex (bool): whether to use regex to search
        exclude (bool)
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): list of networks

    """
    args_dict = {
        '--long': long,
        '--name': full_name,
        '--project': project,
        '--project-domain': project_domain,
        '--external': True if external else None,
        '--internal': True if external is False else None,
        '--enable': True if enabled else None,
        '--disable': True if enabled is False else None,
        '--share': True if shared else None,
        '--no-share': True if shared is False else None,
        '--status': status,
        '--provider-network-type': providernet_type,
        '--provider-physical-network': provider_physical_network,
        '--provider-segment': provider_setment,
        '--agent': agent,
        '--tags': tags,
        '--any-tags': any_tags,
        '--not-tags': not_tags,
        '--not-any-tags': not_any_tags,
    }
    args = common.parse_args(args_dict, repeat_arg=False, vals_sep=',')
    table_ = table_parser.table(
        cli.openstack('network list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    filters = {'name': name, 'subnets': subnets, 'id': net_id}
    filters = {k: v for k, v in filters.items() if str(v)}
    if filters:
        table_ = table_parser.filter_table(table_, strict=strict, regex=regex,
                                           exclude=exclude, **filters)

    convert = False
    if isinstance(field, str):
        field = (field,)
        convert = True

    res = []
    for header in field:
        vals = table_parser.get_column(table_, header)
        if header.lower() == 'subnets':
            vals = [val.split(sep=', ') for val in vals]
        res.append(vals)
    if convert:
        res = res[0]

    return res


def delete_network(network_id, auth_info=Tenant.get('admin'), con_ssh=None,
                   fail_ok=False):
    """
     Delete given network
     Args:
         network_id: network id to be deleted.
        con_ssh (SSHClient):
        auth_info (dict):
        fail_ok (bool): whether to return False or raise exception when
        non-alive agents exist

     Returns (list):

     """
    LOG.info("Deleting network {}".format(network_id))
    code, output = cli.openstack('network delete', network_id,
                                 ssh_client=con_ssh, fail_ok=True,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    if network_id in get_networks(auth_info=auth_info, con_ssh=con_ssh):
        msg = "Network {} is still listed in neutron net-list".format(
            network_id)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.NeutronError(msg)

    succ_msg = "Network {} is successfully deleted.".format(network_id)
    return 0, succ_msg


def create_sfc_port_pair(ingress_port, egress_port, name=None, description=None,
                         service_func_param=None, fail_ok=False,
                         con_ssh=None, auth_info=None, cleanup=None):
    """
    Create port pair

    Args:
        ingress_port (str):
        egress_port (str):
        name (str|None):
        description (str|None):
        service_func_param (str|None):
        fail_ok (bool):
        con_ssh:
        auth_info:
        cleanup (str|None)

    Returns (tuple):
        (0, <port_pair_id>)     # successfully created
        (1, <std_err>)          # create CLI rejected

    """
    if not name:
        name = 'port_pair'
        name = common.get_unique_name(name_str=name)

    args_dict = {
        '--ingress': ingress_port,
        '--egress': egress_port,
        '--description': description,
        '--service-function-parameters': service_func_param,
    }

    arg = '{} {}'.format(
        common.parse_args(args_dict, repeat_arg=True, vals_sep=','), name)
    LOG.info("Creating port pair {}".format(name))
    code, output = cli.openstack(cmd='sfc port pair create',
                                 positional_args=arg, ssh_client=con_ssh,
                                 fail_ok=fail_ok,
                                 auth_info=auth_info)
    table_ = table_parser.table(output)
    pair_id = table_parser.get_value_two_col_table(table_, field='ID')
    if pair_id and cleanup:
        ResourceCleanup.add('port_pair', pair_id, scope=cleanup)

    if code > 0:
        return 1, output

    LOG.info("Port pair {} created successfully".format(pair_id))
    return 0, pair_id


def delete_sfc_port_pairs(port_pairs=None, value='ID', check_first=True,
                          fail_ok=False, con_ssh=None, auth_info=None):
    """
    Delete port pairs
    Args:
        port_pairs (str|list|tuple|None):
        value: ID or Name
        check_first (bool):
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns (tuple): (<code>(int), <successfully_deleted_pairs>(list),
    <rejected_pairs>(list), <rejection_messages>list)
        (0, <successfully_deleted_pairs>(list), [], [])
        (1, <successfully_deleted_pairs_if_any>, <rejected_pairs>(list),
        <rejection_messages>list)    # fail_ok=True

    """
    if not port_pairs:
        port_pairs = get_sfc_port_pairs(field=value, auth_info=auth_info,
                                        con_ssh=con_ssh)
    else:
        if isinstance(port_pairs, str):
            port_pairs = [port_pairs]

        if check_first:
            existing_pairs = get_sfc_port_pairs(field=value,
                                                auth_info=auth_info,
                                                con_ssh=con_ssh)
            port_pairs = list(set(port_pairs) & set(existing_pairs))

    if not port_pairs:
        msg = 'Port pair(s) do not exist. Do nothing.'
        LOG.info(msg)
        return -1, msg

    errors = []
    LOG.info("Deleting port pair(s): {}".format(port_pairs))
    for port_pair in port_pairs:
        code, output = cli.openstack(cmd='sfc port pair delete',
                                     positional_args=port_pair,
                                     ssh_client=con_ssh,
                                     fail_ok=fail_ok, auth_info=auth_info)

        if code > 0:
            errors.append(output)

    if errors:
        return 1, '\n'.join(errors)

    post_del_pairs = get_sfc_port_pairs(field=value, auth_info=auth_info,
                                        con_ssh=con_ssh)
    failed_pairs = list(set(port_pairs) & set(post_del_pairs))
    if failed_pairs:
        msg = "Some port-pair(s) still exist after deletion: {}".format(
            failed_pairs)
        LOG.warning(msg)
        if fail_ok:
            return 2, msg
        raise exceptions.NeutronError(msg)

    msg = "Port pair(s) deleted successfully."
    LOG.info(msg)
    return 0, msg


def get_sfc_port_pairs(field='ID', con_ssh=None, auth_info=None, **filters):
    """
    Get port pairs
    Args:
        field (str|tuple|list): header of the table. ID or Name
        con_ssh:
        auth_info:
        **filters:

    Returns (list):

    """
    arg = '--print-empty'
    table_ = table_parser.table(
        cli.openstack('sfc port pair list', positional_args=arg,
                      ssh_client=con_ssh, auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, **filters)


def create_sfc_port_pair_group(port_pairs=None, port_pair_val='ID', name=None,
                               description=None, group_param=None,
                               fail_ok=False, con_ssh=None, auth_info=None,
                               cleanup=None):
    """
    Create a port pair group
    Args:
        port_pairs (str|list|tuple|None):
        port_pair_val (str): ID or Name
        name (str|None):
        description (str|None):
        group_param (str|None):
        fail_ok (bool):
        con_ssh:
        auth_info:
        cleanup

    Returns (tuple):
        (0, <port pair group id>)
        (1, <std_err>)

    """
    args_dict = {
        '--port-pair': port_pairs,
        '--description': description,
        '--port-pair-group-parameters': group_param
    }

    if not name:
        name = 'port_pair_group'
        name = common.get_unique_name(name_str=name)
    arg = '{} {}'.format(
        common.parse_args(args_dict, repeat_arg=True, vals_sep=','), name)

    LOG.info("Creating port pair group {}".format(name))
    code, output = cli.openstack('sfc port pair group create', arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    table_ = table_parser.table(output)
    group_id = table_parser.get_value_two_col_table(table_, 'ID')
    if cleanup and group_id:
        ResourceCleanup.add('port_pair_group', group_id, scope=cleanup)

    if code > 0:
        return 1, output

    # Check specified port-pair(s) are in created group
    port_pairs_in_group = eval(
        table_parser.get_value_two_col_table(table_, 'Port Pair'))
    if port_pairs:
        if port_pair_val.lower() != 'id':
            pair_ids = []
            for port_pair in port_pairs:
                port_pair_id = \
                    get_sfc_port_pairs(Name=port_pair, con_ssh=con_ssh,
                                       auth_info=auth_info)[0]
                pair_ids.append(port_pair_id)
            port_pairs = pair_ids
        assert sorted(port_pairs_in_group) == sorted(
            port_pairs), "Port pairs expected in group: {}. Actual: {}". \
            format(port_pairs, port_pairs_in_group)
    else:
        assert not port_pairs_in_group, "Port pair(s) exist in group even " \
                                        "though no port pair is specified"

    LOG.info("Port pair group {} created successfully".format(name))
    return 0, group_id


def set_sfc_port_pair_group(group, port_pairs=None, name=None, description=None,
                            fail_ok=False, con_ssh=None,
                            auth_info=None):
    """
    Set port pair group with given values
    Args:
        group (str): port pair group to set
        port_pairs (list|str|tuple|None): port pair(s) to add
        name (str|None):
        description (str|None):
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns (tuple):
        (0, "Port pair group set successfully")
        (1, <std_err>)

    """
    LOG.info("Setting port pair group {}".format(group))
    arg = ''
    verify = {}
    if port_pairs is not None:
        if port_pairs:
            if isinstance(port_pairs, str):
                port_pairs = [port_pairs]
            port_pairs = list(port_pairs)
            for port_pair in port_pairs:
                arg += ' --port-pair {}'.format(port_pair)

            verify['Port Pair'] = port_pairs
        else:
            arg += ' --no-port-pair'
            verify['Port Pair'] = []

    if name is not None:
        arg += ' --name {}'.format(name)
        verify['Name'] = name
    if description is not None:
        arg += ' --description {}'.format(description)
        verify['Description'] = description

    arg = '{} {}'.format(arg, group)
    code, output = cli.openstack('sfc port pair group set', positional_args=arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    LOG.info("Verify port pair group is set correctly")
    table_ = table_parser.table(output)
    for key, val in verify.items():
        actual_val = table_parser.get_value_two_col_table(table_, key)
        if isinstance(val, list):
            actual_val = eval(actual_val)
            if val:
                assert set(val) <= set(
                    actual_val), "Port pair(s) set: {}; pairs in group: " \
                                 "{}".format(val, actual_val)
                assert len(set(actual_val)) == len(
                    actual_val), "Duplicated item found in Port pairs field: " \
                                 "{}". format(actual_val)
            else:
                assert not actual_val, "Port pair still exist in group {} " \
                                       "after setting to no: {}". \
                    format(group, actual_val)
        else:
            assert val == actual_val, "Value set for {} is {} ; " \
                                      "actual: {}".format(key, val, actual_val)

    msg = "Port pair group set successfully"
    LOG.info("Port pair group set successfully")
    return 0, msg


def unset_sfc_port_pair_group(group, port_pairs='all', fail_ok=False,
                              con_ssh=None, auth_info=None):
    """
    Remove port pair(s) from a group
    Args:
        group (str):
        port_pairs (str|list|tuple|None): port_pair(s). When 'all': remove
        all port pairs from group.
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns:
        (0, <remaining port pairs in group>(list))
        (1, <std_err>(str))

    """
    LOG.info("Unsetting port pair group {}".format(group))
    arg = ''
    if port_pairs == 'all':
        arg = '--all-port-pair'
    else:
        if isinstance(port_pairs, str):
            port_pairs = [port_pairs]
        port_pairs = list(port_pairs)

        for port_pair in port_pairs:
            arg += ' --port-pair {}'.format(port_pair)

    arg = '{} {}'.format(arg, group)

    code, output = cli.openstack('sfc port pair group unset',
                                 positional_args=arg, ssh_client=con_ssh,
                                 fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    LOG.info("Verify port pair group is unset correctly")
    table_ = table_parser.table(output)
    actual_pairs = eval(
        table_parser.get_value_two_col_table(table_, 'Port Pair'))
    if port_pairs == 'all':
        assert not actual_pairs
    else:
        unremoved_pairs = list(set(actual_pairs) & set(port_pairs))
        assert not unremoved_pairs

    LOG.info("Port pairs are successfully removed from group {}".format(group))
    return 0, actual_pairs


def delete_sfc_port_pair_group(group, check_first=True, fail_ok=False,
                               auth_info=None, con_ssh=None):
    """
    Delete given port pair group
    Args:
        group (str):
        check_first (bool): Whether to check before deletion
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (tuple):
        (-1, 'Port pair group <group> does not exist. Skip deleting.')      #
        check_first=True
        (0, 'Port pair group <group> successfully deleted')
        (1, <std_err>)      # CLI rejected. fail_ok=True

    """
    if check_first:
        group_id = get_sfc_port_pair_group_values(group=group, field='ID',
                                                  auth_info=auth_info,
                                                  con_ssh=con_ssh,
                                                  fail_ok=True)
        if group_id is None:
            msg = 'Port pair group {} does not exist. Skip deleting.'.format(
                group)
            LOG.info(msg)
            return -1, msg

    LOG.info("Deleting port pair group {}".format(group))
    code, output = cli.openstack('sfc port pair group delete', group,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    group_id = get_sfc_port_pair_group_values(group=group, field='ID',
                                              auth_info=auth_info,
                                              con_ssh=con_ssh,
                                              fail_ok=True)
    assert group_id is None, "Port pair group {} still exists after " \
                             "deletion".format(group)

    msg = 'Port pair group {} successfully deleted'.format(group)
    LOG.info(msg)
    return 0, msg


def get_sfc_port_pair_groups(field='ID', auth_info=None, con_ssh=None):
    """
    Get port pair groups
    Args:
        field (str|tuple|list): field(s) for port pair groups table
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('sfc port pair group list --print-empty',
                      ssh_client=con_ssh, auth_info=auth_info)[1])

    return table_parser.get_multi_values(table_, field)


def get_sfc_port_pair_group_values(group, field='Port Pair', fail_ok=False,
                                   auth_info=None, con_ssh=None):
    """
    Get port pair group value from 'openstack sfc port pair group show'
    Args:
        group (str):
        field (str|list|tuple):
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (list|None):
        None    # if group does not exist. Only when fail_ok=True
        str|dict|list   # value of given field.

    """
    code, output = cli.openstack('sfc port pair group show', group,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return None

    table_ = table_parser.table(output)
    values = table_parser.get_multi_values_two_col_table(table_, field,
                                                         evaluate=True)

    return values


def get_sfc_flow_classifiers(field='ID', auth_info=None, con_ssh=None):
    """
    Get flow classifiers
    Args:
        field (str|tuple|list): ID or Name
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('sfc flow classifier list --print-empty',
                      ssh_client=con_ssh, auth_info=auth_info)[1])

    return table_parser.get_multi_values(table_, field)


def get_sfc_port_chains(field='ID', auth_info=None, con_ssh=None):
    """
    Get flow classifiers
    Args:
        field (str): ID or Name
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('sfc port chain list --print-empty', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    return table_parser.get_multi_values(table_, field)


def create_sfc_port_chain(port_pair_groups, name=None, flow_classifiers=None,
                          description=None, chain_param=None,
                          auth_info=None, fail_ok=False, con_ssh=None,
                          cleanup=None):
    """
    Create port chain
    Args:
        port_pair_groups (str|list|tuple):
        name (str|None):
        flow_classifiers (str|list|tuple|None):
        description (str|None):
        chain_param (str|None):
        auth_info:
        fail_ok:
        con_ssh:
        cleanup

    Returns (tuple):
        (1, <std_err>)      # CLI rejected. fail_ok=True
        (0, <port_chain_id>)

    """

    args_dict = {
        '--port-pair-group': port_pair_groups,
        '--flow-classifier': flow_classifiers,
        '--description': description,
        '--chain-parameters': chain_param
    }
    arg = common.parse_args(args_dict, repeat_arg=True, vals_sep=',')

    if not name:
        name = common.get_unique_name(name_str='port_chain')

    arg = '{} {}'.format(arg, name)
    LOG.info("Creating port chain {}".format(name))
    code, output = cli.openstack('sfc port chain create', arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    table_ = table_parser.table(output, combine_multiline_entry=True)
    port_chain_id = table_parser.get_value_two_col_table(table_, 'ID')
    if cleanup:
        ResourceCleanup.add('port_chain', port_chain_id, scope=cleanup)

    LOG.info("Port chain {} successfully created".format(name))
    return 0, port_chain_id


def set_sfc_port_chain(port_chain, port_pair_groups=None, flow_classifiers=None,
                       no_flow_classifier=None,
                       no_port_pair_group=None, fail_ok=False, con_ssh=None,
                       auth_info=None):
    """
    Set port chain with given values
    Args:
        port_chain (str): port chain to set
        port_pair_groups (list|str|tuple|None): port pair group(s) to add.
        Use '' if no port pair group is desired
        flow_classifiers (list|str|tuple|None): flow classifier(s) to add.
        Use '' if no flow classifier is desired
        no_flow_classifier (bool|None)
        no_port_pair_group (bool|None)
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns (tuple):
        (0, "Port chain set successfully")
        (1, <std_err>)

    """
    LOG.info("Setting port chain {}".format(port_chain))
    arg_dict = {
        'flow-classifier': flow_classifiers,
        'no-flow-classifier': no_flow_classifier,
        'port-pair-group': port_pair_groups,
        'no-port-pair-group': no_port_pair_group,
    }

    arg = '{} {}'.format(common.parse_args(arg_dict, repeat_arg=True),
                         port_chain)
    code, output = cli.openstack('sfc port chain set', positional_args=arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "Port chain {} set successfully".format(port_chain)
    LOG.info(msg)
    return 0, msg


def unset_sfc_port_chain(port_chain, flow_classifiers=None,
                         port_pair_groups=None, all_flow_classifier=None,
                         fail_ok=False, con_ssh=None,
                         auth_info=None):
    """
    Remove port pair(s) from a group
    Args:
        port_chain (str):
        flow_classifiers (str|list|tuple|None): flow_classifier(s) to remove.
            When 'all': remove all flow_classifiers from group.
        port_pair_groups (str|list|tuple|None): port_pair_group(s) to remove.
        all_flow_classifier (bool|None)
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns:
        (0, "Port chain unset successfully")
        (1, <std_err>(str))

    """
    LOG.info("Unsetting port chain {}".format(port_chain))
    args_dict = {
        '--all-flow-classifier': all_flow_classifier,
        '--flow-classifier': flow_classifiers,
        '--port-pair-group': port_pair_groups
    }
    arg = common.parse_args(args_dict, repeat_arg=True)
    if not arg:
        raise ValueError("Nothing specified to unset.")

    arg = '{} {}'.format(arg, port_chain)
    code, output = cli.openstack('sfc port chain unset', arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    msg = "Port chain unset successfully"
    LOG.info(msg)
    return 0, msg


def delete_sfc_port_chain(port_chain, check_first=True, fail_ok=False,
                          auth_info=None, con_ssh=None):
    """
    Delete given port pair group
    Args:
        port_chain (str):
        check_first (bool): Whether to check before deletion
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (tuple):
        (-1, 'Port chain <chain> does not exist. Skip deleting.')      #
        check_first=True
        (0, 'Port chain <chain> successfully deleted')
        (1, <std_err>)      # CLI rejected. fail_ok=True

    """
    if check_first:
        chain_id = get_sfc_port_chain_values(port_chain=port_chain, fields='ID',
                                             auth_info=auth_info,
                                             con_ssh=con_ssh,
                                             fail_ok=True)
        if chain_id is None:
            msg = 'Port chain {} does not exist. Skip deleting.'.format(
                port_chain)
            LOG.info(msg)
            return -1, msg

    LOG.info("Deleting port chain {}".format(port_chain))
    code, output = cli.openstack('sfc port chain delete', port_chain,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    chain_id = get_sfc_port_chain_values(port_chain=port_chain, fields='ID',
                                         auth_info=auth_info, con_ssh=con_ssh,
                                         fail_ok=True)
    assert chain_id is None, "Port chain {} still exists after deletion".format(
        port_chain)

    msg = 'Port chain {} successfully deleted'.format(port_chain)
    LOG.info(msg)
    return 0, msg


def get_sfc_port_chain_values(port_chain, fields='Flow Classifiers',
                              fail_ok=False, auth_info=None, con_ssh=None):
    """
    Get port chain value from 'openstack sfc port chain show'
    Args:
        port_chain (str):
        fields (str|list|tuple):
        fail_ok (bool):
        auth_info:
        con_ssh:

    Returns (None|list): None    # if chain does not exist. Only when
    fail_ok=True

    """
    code, output = cli.openstack('sfc port chain show', port_chain,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return None

    table_ = table_parser.table(output)
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       evaluate=True,
                                                       merge_lines=True)


def get_sfc_flow_classifier_values(flow_classifier, fields='Protocol',
                                   fail_ok=False, auth_info=None, con_ssh=None):
    """
        Get flow classifier value from 'openstack sfc flow classifier show'
        Args:
            flow_classifier (str):
            fields (str):
            fail_ok (bool):
            auth_info:
            con_ssh:

        Returns (None|list): return None if flow classifier does not exist.
        Only when fail_ok=True

        """
    code, output = cli.openstack('sfc flow classifier show', flow_classifier,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return None

    table_ = table_parser.table(output)
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       merge_lines=True)


def create_flow_classifier(name=None, description=None, protocol=None,
                           ether_type=None, source_port=None,
                           dest_port=None, source_ip_prefix=None,
                           dest_ip_prefix=None, logical_source_port=None,
                           logical_dest_port=None, l7_param=None, fail_ok=False,
                           auth_info=None, con_ssh=None,
                           cleanup=None):
    """
    Create a flow classifier
    Args:
        name:
        description:
        protocol:
        ether_type:
        source_port:
        dest_port:
        source_ip_prefix:
        dest_ip_prefix:
        logical_source_port:
        logical_dest_port:
        l7_param:
        fail_ok:
        auth_info:
        con_ssh:
        cleanup

    Returns (tuple):
        (0, <flow_classifier_id>)
        (1, <std_err>)

    """
    arg_dict = {
        'description': description,
        'protocol': protocol,
        'ethertype': ether_type,
        'logical-source-port': logical_source_port,
        'logical-destination-port': logical_dest_port,
        'source-ip-prefix': source_ip_prefix,
        'destination-ip-prefix': dest_ip_prefix,
        'l7-parameters': l7_param,
        'source-port': source_port,
        'destination-port': dest_port,
    }

    arg = common.parse_args(arg_dict)
    if not name:
        name = 'flow_classifier'
        name = common.get_unique_name(name_str=name)

    arg += ' {}'.format(name)

    LOG.info("Creating flow classifier {}".format(name))
    code, output = cli.openstack('sfc flow classifier create', arg,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    table_ = table_parser.table(output)
    id_ = table_parser.get_value_two_col_table(table_, 'ID')
    if cleanup and id_:
        ResourceCleanup.add('flow_classifier', id_)

    msg = "Flow classifier {} successfully created.".format(id_)
    LOG.info(msg)
    return 0, id_


def delete_flow_classifier(flow_classifier, check_first=True, fail_ok=False,
                           auth_info=None, con_ssh=None):
    """
    Delete flow classifier
    Args:
        flow_classifier (str):
        check_first:
        fail_ok:
        auth_info:
        con_ssh:

    Returns (tuple):
        (-1, Flow classifier <flow_classifier> does not exist. Skip deletion.")
        (0, "Flow classifier <flow_classifier> successfully deleted")
        (1, <std_err>)

    """
    if check_first:
        info = get_sfc_flow_classifier_values(flow_classifier, fields='ID',
                                              fail_ok=True, con_ssh=con_ssh,
                                              auth_info=auth_info)
        if info is None:
            msg = "Flow classifier {} does not exist. Skip deletion.".format(
                flow_classifier)
            LOG.info(msg)
            return -1, msg

    code, output = cli.openstack('sfc flow classifier delete', flow_classifier,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    post_del_id = get_sfc_flow_classifier_values(flow_classifier, fields='ID',
                                                 auth_info=auth_info,
                                                 con_ssh=con_ssh,
                                                 fail_ok=True)[0]
    if post_del_id:
        err = "Flow classifier {} still exists after deletion".format(
            flow_classifier)
        LOG.warning(err)
        if fail_ok:
            return 2, err
        raise exceptions.NeutronError(err)

    msg = "Flow classifier {} successfully deleted".format(flow_classifier)
    LOG.info(msg)
    return 0, msg


def get_ip_for_eth(ssh_client, eth_name):
    """
    Get the IP addr for given eth on the ssh client provided
    Args:
        ssh_client (SSHClient): usually a vm_ssh
        eth_name (str): such as "eth1, eth1.1"

    Returns (str): The first matching ipv4 addr for given eth. such as
    "30.0.0.2"

    """
    if eth_name in ssh_client.exec_cmd('ip addr'.format(eth_name))[1]:
        output = ssh_client.exec_cmd('ip addr show {}'.format(eth_name),
                                     fail_ok=False)[1]
        if re.search('inet {}'.format(Networks.IPV4_IP), output):
            return re.findall('{}'.format(Networks.IPV4_IP), output)[0]
        else:
            LOG.warning(
                "Cannot find ip address for interface{}".format(eth_name))
            return ''

    else:
        LOG.warning(
            "Cannot find provided interface{} in 'ip addr'".format(eth_name))
        return ''


def _is_v4_only(ip_list):
    rtn_val = True
    for ip in ip_list:
        ip_addr = ipaddress.ip_address(ip)
        if ip_addr.version == 6:
            rtn_val = False
    return rtn_val


def get_internal_net_ids_on_vxlan(vxlan_provider_net_id, ip_version=4,
                                  mode='dynamic', con_ssh=None):
    """
    Get the networks ids that matches the vxlan underlay ip version
    Args:
        vxlan_provider_net_id: vxlan provider net id to get the networks info
        ip_version: 4 or 6 (IPV4 or IPV6)
        mode: mode of the vxlan: dynamic or static
        con_ssh (SSHClient):

    Returns (list): The list of networks name that matches the vxlan underlay
    (v4/v6) and the mode

    """
    rtn_networks = []
    networks = get_networks_on_providernet(providernet=vxlan_provider_net_id,
                                           field='id', con_ssh=con_ssh)
    if not networks:
        return rtn_networks
    provider_attributes = get_networks_on_providernet(
        providernet=vxlan_provider_net_id, con_ssh=con_ssh,
        field='providernet_attributes')
    if not provider_attributes:
        return rtn_networks

    index = 0
    new_attr_list = []
    # In the case where some val could be 'null', need to change that to 'None'
    for attr in provider_attributes:
        new_attr = attr.replace('null', 'None')
        new_attr_list.append(new_attr)

    # getting the configured vxlan mode
    dic_attr_1 = eval(new_attr_list[0])
    vxlan_mode = dic_attr_1['mode']

    if mode == 'static' and vxlan_mode == mode:
        data_if_name = host_helper.get_host_interfaces('compute-0',
                                                       net_type='data',
                                                       con_ssh=con_ssh)
        address = host_helper.get_host_addresses(host='compute-0',
                                                 ifname=data_if_name,
                                                 con_ssh=con_ssh)
        if ip_version == 4 and _is_v4_only(address):
            rtn_networks.append(networks[index])
        elif ip_version == 6 and not _is_v4_only(address):
            LOG.info("here in v6")
            rtn_networks = networks
        else:
            return rtn_networks
    elif mode == 'dynamic' and vxlan_mode == mode:
        for attr in provider_attributes:
            dic_attr = eval(attr)
            ip = dic_attr['group']
            ip_addr = ipaddress.ip_address(ip)
            if ip_addr.version == ip_version:
                rtn_networks.append(networks[index])
        index += 1

    return rtn_networks


def get_dpdk_user_data(con_ssh=None):
    """
    copy the cloud-config userdata to TiS server.
    This userdata adds wrsroot/li69nux user to guest

    Args:
        con_ssh (SSHClient):

    Returns (str): TiS filepath of the userdata

    """
    file_dir = '{}/userdata/'.format(ProjVar.get_var('USER_FILE_DIR'))
    file_name = UserData.DPDK_USER_DATA
    file_path = file_dir + file_name

    if con_ssh is None:
        con_ssh = get_cli_client()

    if con_ssh.file_exists(file_path=file_path):
        # LOG.info('userdata {} already exists. Return existing path'.format(
        # file_path))
        # return file_path
        con_ssh.exec_cmd('rm -f {}'.format(file_path), fail_ok=False)

    LOG.debug('Create userdata directory if not already exists')
    cmd = 'mkdir -p {};touch {}'.format(file_dir, file_path)
    con_ssh.exec_cmd(cmd, fail_ok=False)

    content = "#wrs-config\nFUNCTIONS=hugepages,avr\n"
    con_ssh.exec_cmd('echo "{}" >> {}'.format(content, file_path),
                     fail_ok=False)
    output = con_ssh.exec_cmd('cat {}'.format(file_path))[1]
    assert output in content

    return file_path


def get_ping_failure_duration(server, ssh_client, end_event, timeout=600,
                              ipv6=False, start_event=None,
                              ping_interval=0.2, single_ping_timeout=1,
                              cumulative=False, init_timeout=60):
    """
    Get ping failure duration in milliseconds
    Args:
        server (str): destination ip
        ssh_client (SSHClient): where the ping cmd sent from
        timeout (int): Max time to ping and gather ping loss duration before
        ipv6 (bool): whether to use ping IPv6 address
        start_event
        end_event: an event that signals the end of the ping
        ping_interval (int|float): interval between two pings in seconds
        single_ping_timeout (int): timeout for ping reply in seconds. Minimum
        is 1 second.
        cumulative (bool): Whether to accumulate the total loss time before
        end_event set
        init_timeout (int): Max time to wait before vm pingable

    Returns (int): ping failure duration in milliseconds. 0 if ping did not
    fail.

    """
    optional_args = ''
    if ipv6:
        optional_args += '6'

    fail_str = 'no answer yet'
    cmd = 'ping{} -i {} -W {} -D -O {} | grep -B 1 -A 1 ' \
          '--color=never "{}"'.format(optional_args, ping_interval,
                                      single_ping_timeout, server, fail_str)

    start_time = time.time()
    ping_init_end_time = start_time + init_timeout
    prompts = [ssh_client.prompt, fail_str]
    ssh_client.send_sudo(cmd=cmd)
    while time.time() < ping_init_end_time:
        index = ssh_client.expect(prompts, timeout=10, searchwindowsize=100,
                                  fail_ok=True)
        if index == 1:
            continue
        elif index == 0:
            raise exceptions.CommonError("Continuous ping cmd interrupted")

        LOG.info("Ping to {} succeeded".format(server))
        start_event.set()
        break
    else:
        raise exceptions.VMNetworkError(
            "VM is not reachable within {} seconds".format(init_timeout))

    end_time = start_time + timeout
    while time.time() < end_time:
        if end_event.is_set():
            LOG.info("End event set. Stop continuous ping and process results")
            break

    #  End ping upon end_event set or timeout reaches
    ssh_client.send_control()
    try:
        ssh_client.expect(fail_ok=False)
    except (exceptions.TiSError, pexpect.ExceptionPexpect):
        ssh_client.send_control()
        ssh_client.expect(fail_ok=False)

    # Process ping output to get the ping loss duration
    output = ssh_client.process_cmd_result(cmd='sudo {}'.format(cmd),
                                           get_exit_code=False)[1]
    lines = output.splitlines()
    prev_succ = ''
    duration = 0
    count = 0
    prev_line = ''
    succ_str = 'bytes from'
    post_succ = ''
    for line in lines:
        if succ_str in line:
            if prev_succ and (fail_str in prev_line):
                # Ping resumed after serious of lost ping
                count += 1
                post_succ = line
                tmp_duration = _parse_ping_timestamp(
                    post_succ) - _parse_ping_timestamp(prev_succ)
                LOG.info("Count {} ping loss duration: {}".format(count,
                                                                  tmp_duration))
                if cumulative:
                    duration += tmp_duration
                elif tmp_duration > duration:
                    duration = tmp_duration
            prev_succ = line

        prev_line = line

    if not post_succ:
        LOG.warning("Ping did not resume within {} seconds".format(timeout))
        duration = -1
    else:
        LOG.info("Final ping loss duration: {}".format(duration))
    return duration


def _parse_ping_timestamp(output):
    timestamp = math.ceil(float(re.findall(r'\[(.*)\]', output)[0]) * 1000)
    return timestamp


@contextmanager
def vconsole(ssh_client):
    """
    Enter vconsole for the given ssh connection.
    raises if vconsole connection cannot be established

    Args:
        ssh_client (SSHClient):
            the connection to use for vconsole session

    Yields (function):
        executer function for vconsole

    """
    LOG.info("Entering vconsole")
    original_prompt = ssh_client.get_prompt()
    ssh_client.set_prompt("AVS> ")
    try:
        ssh_client.exec_sudo_cmd("vconsole", get_exit_code=False)
    except Exception as err:
        # vconsole failed to connect
        # this is usually because vswitch initialization failed
        # check instance logs
        ssh_client.set_prompt(original_prompt)
        ssh_client.flush(3)
        ssh_client.send_control('c')
        ssh_client.flush(10)
        raise err

    def v_exec(cmd, fail_ok=False):
        LOG.info("vconsole execute: {}".format(cmd))
        if cmd.strip().lower() == 'quit':
            raise ValueError("shall not exit vconsole without proper cleanup")

        code, output = ssh_client.exec_cmd(cmd, get_exit_code=False)
        if "done" in output.lower():
            return 0, output

        LOG.warning(output)
        if not fail_ok:
            assert 0, 'vconsole failed to execute "{}"'.format(cmd)
        return 1, output

    yield v_exec

    LOG.info("Exiting vconsole")
    ssh_client.set_prompt(original_prompt)
    ssh_client.exec_cmd("quit")


def create_port_forwarding_rule(router_id, inside_addr=None, inside_port=None,
                                outside_port=None, protocol='tcp',
                                tenant=None, description=None, fail_ok=False,
                                auth_info=Tenant.get('admin'),
                                con_ssh=None):
    """

    Args:
        router_id (str): The router_id of the tenant router the
        portforwarding rule is created
        inside_addr(str): private ip address
        inside_port (int|str):  private protocol port number
        outside_port(int|str): The public layer4 protocol port number
        protocol(str): the protocol  tcp|udp|udp-lite|sctp|dccp
        tenant(str): The owner Tenant id.
        description(str): User specified text description. The default is
        "portforwarding"
        fail_ok:
        auth_info:
        con_ssh:

    Returns (tuple):
        0, <portforwarding rule id>, <success msg>    - Portforwarding rule
        created successfully
        1, '', <std_err>              - Portforwarding rule create cli rejected
        2, '', <std_err>  - Portforwarding rule create failed; one or more
        values required are not specified.


    """
    # Process args
    if tenant is None:
        tenant = Tenant.get_primary()['tenant']

    if description is None:
        description = '"portforwarding"'

    tenant_id = keystone_helper.get_projects(field='ID', name=tenant,
                                             con_ssh=con_ssh)[0]

    mgmt_ips_for_vms = get_mgmt_ips_for_vms()

    if inside_addr not in mgmt_ips_for_vms:
        msg = "The inside_addr {} must be one of the  vm mgmt internal " \
              "addresses: {}.".format(inside_addr, mgmt_ips_for_vms)
        return 1, msg

    args_dict = {
        '--tenant-id': tenant_id if auth_info == Tenant.get('admin') else None,
        '--inside-addr': inside_addr,
        '--inside-port': inside_port,
        '--outside-port': outside_port,
        '--protocol': protocol,
        '--description': description,
    }
    args = router_id

    for key, value in args_dict.items():
        if value is None:
            msg = 'A value must be specified for {}'.format(key)
            if fail_ok:
                return 1, '', msg
            raise exceptions.NeutronError(msg)
        else:
            args = "{} {} {}".format(key, value, args)

    LOG.info("Creating port forwarding with args: {}".format(args))
    # send portforwarding-create cli
    code, output = cli.neutron('portforwarding-create', args,
                               ssh_client=con_ssh, fail_ok=fail_ok,
                               auth_info=auth_info)

    # process result
    if code == 1:
        msg = 'Fail to create port forwarding rules: {}'.format(output)
        if fail_ok:
            return 1, '', msg
        raise exceptions.NeutronError(msg)

    table_ = table_parser.table(output)
    portforwarding_id = table_parser.get_value_two_col_table(table_, 'id')

    expt_values = {
        'router_id': router_id,
        'tenant_id': tenant_id
    }

    for field, expt_val in expt_values.items():
        if table_parser.get_value_two_col_table(table_, field) != expt_val:
            msg = "{} is not set to {} for portforwarding {}".format(
                field, expt_val, router_id)
            if fail_ok:
                return 2, portforwarding_id, msg
            raise exceptions.NeutronError(msg)

    succ_msg = "Portforwarding {} is created successfully.".format(
        portforwarding_id)
    LOG.info(succ_msg)
    return 0, portforwarding_id, succ_msg


def create_port_forwarding_rule_for_vm(vm_id, inside_addr=None,
                                       inside_port=None, outside_port=None,
                                       protocol='tcp',
                                       description=None, fail_ok=False,
                                       auth_info=Tenant.get('admin'),
                                       con_ssh=None):
    """

    Args:
        vm_id (str): The id of vm the portforwarding rule is created for
        inside_addr(str): private ip address; default is mgmt address of vm.
        inside_port (str):  private protocol port number; default is 80 ( web
            port)
        outside_port(str): The public layer4 protocol port number; default is
            8080
        protocol(str): the protocol  tcp|udp|udp-lite|sctp|dccp; default is tcp
        description(str): User specified text description. The default is
            "portforwarding"
        fail_ok:
        auth_info:
        con_ssh:

    Returns (tuple):
        0, <portforwarding rule id>, <success msg>    - Portforwarding rule
            created successfully
        1, '', <std_err>              - Portforwarding rule create cli rejected
        2, '', <std_err>  - Portforwarding rule create failed; one or more
            values required are not specified.

    """
    # Process args
    router_id = get_tenant_router()

    if inside_addr is None:
        inside_addr = get_mgmt_ips_for_vms(vm_id)[0]
    if inside_port is None:
        inside_port = "80"

    if outside_port is None:
        outside_port = "8080"

    return create_port_forwarding_rule(router_id, inside_addr=inside_addr,
                                       inside_port=inside_port,
                                       outside_port=outside_port,
                                       protocol=protocol,
                                       description=description, fail_ok=fail_ok,
                                       auth_info=auth_info,
                                       con_ssh=con_ssh)


def update_portforwarding_rule(portforwarding_id, inside_addr=None,
                               inside_port=None, outside_port=None,
                               protocol=None, description=None, fail_ok=False,
                               auth_info=Tenant.get('admin'), con_ssh=None):
    """

    Args:
        portforwarding_id (str): Id or name of portfowarding rule to update
        inside_addr (str): Private ip address
        inside_port (str): Private layer4 protocol port
        outside_port (str): Public layer4 protocol port
        protocol (str): protocol name tcp|udp|udp-lite|sctp|dccp
        description (str): User specified text description
        fail_ok:
        auth_info:
        con_ssh:

    Returns (tuple):
        0,  <command ouput>    - Portforwarding rule updated successfully


    """

    if portforwarding_id is None or not isinstance(portforwarding_id, str):
        raise ValueError(
            "Expecting string value for portforwarding_id. Get {}".format(
                type(portforwarding_id)))

    args = ''

    args_dict = {
        '--inside_addr': inside_addr,
        '--inside_port': inside_port,
        '--outside_port': outside_port,
        '--protocol': protocol,
        '--description': description,
    }

    for key, value in args_dict.items():
        if value is not None:
            args += ' {} {}'.format(key, value)

    if not args:
        raise ValueError("At least of the args need to be specified.")

    LOG.info("Updating router {}: {}".format(portforwarding_id, args))

    args = '{} {}'.format(portforwarding_id, args.strip())
    return cli.neutron('portforwarding-update', args, ssh_client=con_ssh,
                       fail_ok=fail_ok, auth_info=auth_info)


def delete_portforwarding_rules(pf_ids, auth_info=Tenant.get('admin'),
                                con_ssh=None, fail_ok=False):
    """
    Deletes list of portforwarding rules

    Args:
        pf_ids(list): list of portforwarding rules to be deleted.
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):
        0,  <command output>    - Portforwarding rules delete successful

    """
    if pf_ids is None or len(pf_ids) == 0:
        return 0, None

    for pf_id in pf_ids:
        rc, output = delete_portforwarding_rule(pf_id, auth_info=auth_info,
                                                con_ssh=con_ssh,
                                                fail_ok=fail_ok)
        if rc != 0:
            return rc, output
    return 0, None


def delete_portforwarding_rule(portforwarding_id, auth_info=Tenant.get('admin'),
                               con_ssh=None, fail_ok=False):
    """
    Deletes a single portforwarding rule
    Args:
        portforwarding_id (str): Id or name of portforwarding rule to delete.
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):
        0,  <command output>    - Portforwarding rules delete successful
        1, <err_msg> - Portforwarding rules delete cli rejected
        2, <err_msg> - Portforwarding rules delete fail

    """

    LOG.info("Deleting port-forwarding {}...".format(portforwarding_id))
    code, output = cli.neutron('portforwarding-delete', portforwarding_id,
                               ssh_client=con_ssh, fail_ok=fail_ok,
                               auth_info=auth_info)
    if code != 0:
        msg = "CLI rejected. Fail to delete Port-forwarding {}; {}".format(
            portforwarding_id, output)
        LOG.warn(msg)
        if fail_ok:
            return code, msg
        else:
            raise exceptions.NeutronError(msg)

    portforwardings = get_portforwarding_rules(auth_info=auth_info,
                                               con_ssh=con_ssh)
    if portforwarding_id in portforwardings:
        msg = "Port-forwarding {} is still showing in neutron " \
              "portforwarding-list".format(portforwarding_id)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg

    succ_msg = "Port-forwarding {} is successfully deleted.".format(
        portforwarding_id)
    LOG.info(succ_msg)
    return 0, succ_msg


def get_portforwarding_rules(router_id=None, inside_addr=None, inside_port=None,
                             outside_port=None,
                             protocol=None, strict=True, auth_info=None,
                             con_ssh=None):
    """
    Get porforwarding id(s) based on given criteria.
    Args:
        router_id (str): portforwarding router id
        inside_addr (str): portforwarding  inside_addr
        inside_port (str): portforwarding  inside_port
        outside_port (str): portforwarding   outside_port"
        protocol (str):  portforwarding  protocol
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (list): list of porforwarding id(s)

    """

    param_dict = {
        'router_id': router_id,
        'inside_addr': inside_addr,
        'inside_port': inside_port,
        'outside_port': outside_port,
        'protocol': protocol,
    }

    final_params = {}
    for key, val in param_dict.items():
        if val is not None:
            final_params[key] = str(val)

    table_ = table_parser.table(
        cli.neutron('portforwarding-list', ssh_client=con_ssh,
                    auth_info=auth_info)[1],
        combine_multiline_entry=True)
    if not table_parser.get_all_rows(table_):
        return []

    if router_id is not None:
        table_ = table_parser.filter_table(table_, strict=strict,
                                           router_id=router_id)

    return table_parser.get_values(table_, 'id', **final_params)


def get_portforwarding_rule_info(portforwarding_id, field='inside_addr',
                                 strict=True, auth_info=Tenant.get('admin'),
                                 con_ssh=None):
    """
    Get value of specified field for given portforwarding rule

    Args:
        portforwarding_id (str): Id or name of portforwarding rule
        field (str): the name of the field attribute
        strict (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (str): value of specified field for given portforwarding rule

    """

    table_ = table_parser.table(
        cli.neutron('portforwarding-show', portforwarding_id,
                    ssh_client=con_ssh, auth_info=auth_info)[1],
        combine_multiline_entry=True)
    return table_parser.get_value_two_col_table(table_, field, strict)


def create_pci_alias_for_devices(dev_type, hosts=None, devices=None,
                                 alias_names=None, apply=True, con_ssh=None):
    """
    Create pci alias for given devices by adding nova pci-alias service
    parameters
    Args:
        dev_type (str): Valid values: 'gpu-pf', 'user'
        hosts (str|list|tuple|None): Check devices on given host(s).
            Check all hosts when None
        devices (str|list|tuple|None): Devices to add in pci-alias.
            When None, add all devices for given dev_type
        alias_names (str|list|tuple|None): Pci alias' to create.
            When None, name automatically.
        apply (bool): whether to apply after nova service parameters modify
        con_ssh:

    Returns (list): list of dict.
        e.g., [{'device_id': '1d2d', 'vendor_id': '8086', 'name': user_intel-1},
               {'device_id': '1d26', 'vendor_id': '8086', 'name':
               user_intel-2}, ... ]

    Examples:
        network_helper.create_pci_alias_for_devices(dev_type='user',
            hosts=('compute-2', 'compute-3'))
        network_helper.create_pci_alias_for_devices(dev_type='gpu-pf',
            devices='pci_0000_0c_00_0')

    """
    LOG.info("Prepare for adding pci alias")
    if not hosts:
        hosts = host_helper.get_hypervisors(con_ssh=con_ssh)

    if not devices:
        if 'gpu' in dev_type:
            class_id = DevClassID.GPU
        else:
            class_id = DevClassID.USB
        devices = host_helper.get_host_devices(host=hosts[0], field='address',
                                               list_all=True, regex=True,
                                               **{'class id': class_id})
    elif isinstance(devices, str):
        devices = [devices]

    if not alias_names:
        alias_names = [None] * len(devices)
    elif isinstance(alias_names, str):
        alias_names = [alias_names]

    if len(devices) != len(alias_names):
        raise ValueError(
            "Number of devices do not match number of alias names provided")

    LOG.info(
        "Ensure devices are enabled on hosts {}: {}".format(hosts, devices))
    host_helper.enable_disable_hosts_devices(hosts, devices)

    host = hosts[0]
    devices_to_create = []
    param_strs = []
    for i in range(len(devices)):
        device = devices[i]
        alias_name = alias_names[i]
        dev_id, vendor_id, vendor_name = host_helper.get_host_device_values(
            host=host, device=device,
            fields=('device id', 'vendor id', 'vendor name'))

        if not alias_name:
            alias_name = '{}_{}'.format(dev_type,
                                        vendor_name.split()[0].lower())
            alias_name = common.get_unique_name(name_str=alias_name)

        param = {'device_id': dev_id, 'vendor_id': vendor_id,
                 'name': alias_name}
        param_str = ','.join(
            ['{}={}'.format(key, val) for key, val in param.items()])
        param_strs.append(param_str)

        pci_alias_dict = {'device id': dev_id, 'vendor id': vendor_id,
                          'pci alias': alias_name}
        devices_to_create.append(pci_alias_dict)

    LOG.info("Create nova pci alias service parameters: {}".format(
        devices_to_create))
    system_helper.create_service_parameter(
        service='nova', section='pci_alias',
        con_ssh=con_ssh, name=dev_type,
        value='"{}"'.format(';'.join(param_strs)))

    if apply:
        LOG.info("Apply service parameters")
        system_helper.apply_service_parameters(service='nova')
        LOG.info("Verify nova pci alias' are listed after applying service "
                 "parameters: {}".format(devices_to_create))
        _check_pci_alias_created(devices_to_create, con_ssh=con_ssh)

    return devices_to_create


def _check_pci_alias_created(devices, con_ssh=None, timeout=60):
    end_time = time.time() + timeout
    out = None
    while time.time() < end_time:
        code, out = cli.nova('device-list', ssh_client=con_ssh, fail_ok=True,
                             auth_info=Tenant.get('admin'))
        if code == 0:
            break
        time.sleep(10)
    else:
        raise exceptions.NovaError(
            'nova device-list failed. Error: \n{}'.format(out))

    pci_alias_dict = get_pci_device_list_info(con_ssh=con_ssh)
    for param_ in devices:
        pci_alias = param_.get('pci alias')
        assert pci_alias, "pci alias {} is not shown in nova " \
                          "device-list".format(pci_alias)
        created_alias = pci_alias_dict[pci_alias]
        assert param_.get('vendor id') == created_alias['vendor id']
        assert param_.get('device id') == created_alias['device id']


def get_qos_policies(field='id', name=None, qos_ids=None, con_ssh=None,
                     auth_info=None):
    """
    Get qos policies
    Args:
        field (str|list|tuple)
        name
        qos_ids(str|list|None): QoS id to filter name.
        con_ssh(SSHClient):  If None, active controller ssh will be used.
        auth_info(dict): Tenant dict. If None, primary tenant will be used.

    Returns(list): List of neutron qos names filtered by qos_id.

    """
    table_ = table_parser.table(
        cli.neutron('qos-list', ssh_client=con_ssh, auth_info=auth_info)[1])
    filters = {'id': qos_ids, 'name': name}

    return table_parser.get_multi_values(table_, field, **filters)


def create_qos(name=None, tenant_name=None, description=None, scheduler=None,
               dscp=None, ratelimit=None, fail_ok=False,
               con_ssh=None, auth_info=Tenant.get('admin'), cleanup=None):
    """
    Args:
        name(str): Name of the QoS to be created.
        tenant_name(str): Such as tenant1, tenant2. If none uses primary tenant.
        description(str): Description of the created QoS.
        scheduler(dict): Dictionary of scheduler policies formatted
            as {'policy': value}.
        dscp(dict): Dictionary of dscp policies formatted as {'policy': value}.
        ratelimit(dict): Dictionary of ratelimit policies formatted
            as {'policy': value}.
        fail_ok(bool):
        con_ssh(SSHClient):
        auth_info(dict): Run the neutron qos-create cli using this
            authorization info. Admin by default,
        cleanup (str):

    Returns(tuple): exit_code(int), qos_id(str)
                    (0, qos_id) qos successfully created.
                    (1, output) qos not created successfully
    """
    tenant_id = keystone_helper.get_projects(field='ID',
                                             name=tenant_name,
                                             con_ssh=con_ssh)[0]
    check_dict = {}
    args = ''
    current_qos = get_qos_policies(field='name', con_ssh=con_ssh,
                                   auth_info=auth_info)
    if name is None:
        if tenant_name is None:
            tenant_name = common.get_tenant_name(Tenant.get_primary())
            name = common.get_unique_name("{}-qos".format(tenant_name),
                                          existing_names=current_qos,
                                          resource_type='qos')
        else:
            name = common.get_unique_name("{}-qos".format(tenant_name),
                                          existing_names=current_qos,
                                          resource_type='qos')
    args_dict = {'name': name,
                 'tenant-id': tenant_id,
                 'description': description,
                 'scheduler': scheduler,
                 'dscp': dscp,
                 'ratelimit': ratelimit
                 }
    check_dict['policies'] = {}
    for key, value in args_dict.items():
        if value:
            if key in ('scheduler', 'dscp', 'ratelimit'):
                args += " --{}".format(key)
                for policy, val in value.items():
                    args += " {}={}".format(policy, val)
                    value[policy] = str(val)
                check_dict['policies'][key] = value
            else:
                args += " --{} '{}'".format(key, value)
                if key is 'tenant-id':
                    key = 'tenant_id'
                check_dict[key] = value

    LOG.info("Creating QoS with args: {}".format(args))
    exit_code, output = cli.neutron('qos-create', args, ssh_client=con_ssh,
                                    fail_ok=fail_ok, auth_info=auth_info)
    if exit_code == 1:
        return 1, output

    table_ = table_parser.table(output)
    for key, exp_value in check_dict.items():
        if key is 'policies':
            actual_value = eval(
                table_parser.get_value_two_col_table(table_, key))
        else:
            actual_value = table_parser.get_value_two_col_table(table_, key)
        if actual_value != exp_value:
            msg = "Qos created but {} expected to be {} but actually {}".format(
                key, exp_value, actual_value)
            raise exceptions.NeutronError(msg)

    qos_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup:
        ResourceCleanup.add('network_qos', qos_id, scope=cleanup)
    LOG.info("QoS successfully created")
    return 0, qos_id


def delete_qos(qos_id, auth_info=Tenant.get('admin'), con_ssh=None,
               fail_ok=False):
    """

    Args:
        qos_id(str): QoS to be deleted
        auth_info(dict): tenant to be used, if none admin will be used
        con_ssh(SSHClient):
        fail_ok(bool):

    Returns: code(int), output(string)
            (0, "QoS <qos_id> successfully deleted" )
            (1, <std_err>)  openstack qos delete cli rejected
    """

    LOG.info("deleting QoS: {}".format(qos_id))
    code, output = cli.neutron('qos-delete', qos_id, ssh_client=con_ssh,
                               fail_ok=fail_ok, auth_info=auth_info)
    if code == 1:
        return 1, output

    if qos_id in get_qos_policies(auth_info=auth_info, con_ssh=con_ssh):
        msg = "QoS {} still listed in neutron QoS list".format(qos_id)
        raise exceptions.NeutronError(msg)

    succ_msg = "QoS {} successfully deleted".format(qos_id)
    LOG.info(succ_msg)
    return 0, succ_msg


def update_net_qos(net_id, qos_id=None, fail_ok=False,
                   auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Update network qos to given value
    Args:
        net_id (str): network to update
        qos_id (str|None): when None, remove the qos from network
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple): (code, msg)
        (0, "Network <net_id> qos is successfully updated to <qos_id>")
        (1, <std_err>)  openstack network update cli rejected

    """
    if qos_id:
        kwargs = {'--wrs-tm:qos': qos_id}
        arg_str = '--wrs-tm:qos {}'.format(qos_id)
    else:
        kwargs = {'--no-qos': None}
        arg_str = '--no-qos'

    code, msg = cli.neutron('net-update', '{} {}'.format(arg_str, net_id),
                            ssh_client=con_ssh, fail_ok=fail_ok,
                            auth_info=auth_info)
    if code > 0:
        return code, msg

    if '--no-qos' in kwargs:
        actual_qos = get_network_values(net_id, fields='wrs-tm:qos',
                                        auth_info=auth_info, con_ssh=con_ssh)[0]
        assert not actual_qos, "Qos {} is not removed from {}".format(
            actual_qos, net_id)

    msg = "Network {} qos is successfully updated to {}".format(net_id, qos_id)
    LOG.info(msg)
    return 0, msg
