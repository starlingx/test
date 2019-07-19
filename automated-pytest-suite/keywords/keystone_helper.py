#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import re

from consts.auth import Tenant, HostLinuxUser
from consts.proj_vars import ProjVar
from utils import cli, exceptions, table_parser
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG
from keywords import common


def get_roles(field='ID', con_ssh=None, auth_info=Tenant.get('admin'),
              **kwargs):
    table_ = table_parser.table(cli.openstack('role list', ssh_client=con_ssh,
                                              auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, **kwargs)


def get_users(field='ID', con_ssh=None, auth_info=Tenant.get('admin'),
              **kwargs):
    """
    Return a list of user id(s) with given user name.

    Args:
        field (str|list|tuple):
        con_ssh (SSHClient):
        auth_info

    Returns (list): list of user id(s)

    """
    table_ = table_parser.table(cli.openstack('user list', ssh_client=con_ssh,
                                              auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, **kwargs)


def add_or_remove_role(add_=True, role='admin', project=None, user=None,
                       domain=None, group=None, group_domain=None,
                       project_domain=None, user_domain=None, inherited=None,
                       check_first=True, fail_ok=False,
                       con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Add or remove given role for specified user and tenant. e.g., add admin
    role to tenant2 user on tenant2 project

    Args:
        add_(bool): whether to add or remove
        role (str): an existing role from openstack role list
        project (str): tenant name. When unset, the primary tenant name
            will be used
        user (str): an existing user that belongs to given tenant
        domain (str): Include <domain> (name or ID)
        group (str): Include <group> (name or ID)
        group_domain (str): Domain the group belongs to (name or ID).
            This can be used in case collisions between group names exist.
        project_domain (str): Domain the project belongs to (name or ID).
            This can be used in case collisions between project names exist.
        user_domain (str): Domain the user belongs to (name or ID).
            This can be used in case collisions between user names exist.
        inherited (bool): Specifies if the role grant is inheritable to the
            sub projects
        check_first (bool): whether to check if role already exists for given
            user and tenant
        fail_ok (bool): whether to throw exception on failure
        con_ssh (SSHClient): active controller ssh session
        auth_info (dict): auth info to use to executing the add role cli

    Returns (tuple):

    """
    tenant_dict = {}

    if project is None:
        tenant_dict = Tenant.get_primary()
        project = tenant_dict['tenant']

    if user is None:
        user = tenant_dict.get('user', project)

    if check_first:
        existing_roles = get_role_assignments(role=role, project=project,
                                              user=user,
                                              user_domain=user_domain,
                                              group=group,
                                              group_domain=group_domain,
                                              domain=domain,
                                              project_domain=project_domain,
                                              inherited=inherited,
                                              effective_only=False,
                                              con_ssh=con_ssh,
                                              auth_info=auth_info)
        if existing_roles:
            if add_:
                msg = "Role already exists with given criteria: {}".format(
                    existing_roles)
                LOG.info(msg)
                return -1, msg
        else:
            if not add_:
                msg = "Role with given criteria does not exist. Do nothing."
                LOG.info(msg)
                return -1, msg

    msg_str = 'Add' if add_ else 'Remov'
    LOG.info(
        "{}ing {} role to {} user under {} project".format(msg_str, role, user,
                                                           project))

    sub_cmd = "--user {} --project {}".format(user, project)
    if inherited is True:
        sub_cmd += ' --inherited'

    optional_args = {
        'domain': domain,
        'group': group,
        'group-domain': group_domain,
        'project-domain': project_domain,
        'user-domain': user_domain,
    }

    for key, val in optional_args.items():
        if val is not None:
            sub_cmd += ' --{} {}'.format(key, val)

    sub_cmd += ' {}'.format(role)

    cmd = 'role add' if add_ else 'role remove'
    res, out = cli.openstack(cmd, sub_cmd, ssh_client=con_ssh, fail_ok=fail_ok,
                             auth_info=auth_info)

    if res == 1:
        return 1, out

    LOG.info("{} cli accepted. Check role is {}ed "
             "successfully".format(cmd, msg_str))
    post_roles = get_role_assignments(role=role, project=project, user=user,
                                      user_domain=user_domain, group=group,
                                      group_domain=group_domain, domain=domain,
                                      project_domain=project_domain,
                                      inherited=inherited, effective_only=True,
                                      con_ssh=con_ssh, auth_info=auth_info)

    err_msg = ''
    if add_ and not post_roles:
        err_msg = "No role is added with given criteria"
    elif post_roles and not add_:
        err_msg = "Role is not removed"
    if err_msg:
        if fail_ok:
            LOG.warning(err_msg)
            return 2, err_msg
        else:
            raise exceptions.KeystoneError(err_msg)

    succ_msg = "Role is successfully {}ed".format(msg_str)
    LOG.info(succ_msg)
    return 0, succ_msg


def get_role_assignments(field='Role', names=True, role=None, user=None,
                         project=None, user_domain=None, group=None,
                         group_domain=None, domain=None, project_domain=None,
                         inherited=None, effective_only=None,
                         con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get values from 'openstack role assignment list' table

    Args:
        field (str|list|tuple): role assignment table header to determine
            which values to return
        names (bool): whether to display role assignment with name
            (default is ID)
        role (str): an existing role from openstack role list
        project (str): tenant name. When unset, the primary tenant name
            will be used
        user (str): an existing user that belongs to given tenant
        domain (str): Include <domain> (name or ID)
        group (str): Include <group> (name or ID)
        group_domain (str): Domain the group belongs to (name or ID). This can
            be used in case collisions between group names exist.
        project_domain (str): Domain the project belongs to (name or ID). This
            can be used in case collisions between project names exist.
        user_domain (str): Domain the user belongs to (name or ID). This can
            be used in case collisions between user names exist.
        inherited (bool): Specifies if the role grant is inheritable to the
            sub projects
        effective_only (bool): Whether to show effective roles only
        con_ssh (SSHClient): active controller ssh session
        auth_info (dict): auth info to use to executing the add role cli

    Returns (list): list of values

    """
    optional_args = {
        'role': role,
        'user': user,
        'project': project,
        'domain': domain,
        'group': group,
        'group-domain': group_domain,
        'project-domain': project_domain,
        'user-domain': user_domain,
        'names': True if names else None,
        'effective': True if effective_only else None,
        'inherited': True if inherited else None
    }
    args = common.parse_args(optional_args)

    role_assignment_tab = table_parser.table(
        cli.openstack('role assignment list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    if not role_assignment_tab['headers']:
        LOG.info("No role assignment is found with criteria: {}".format(args))
        return []

    return table_parser.get_multi_values(role_assignment_tab, field)


def set_user(user, name=None, project=None, password=None, project_doamin=None,
             email=None, description=None,
             enable=None, fail_ok=False, auth_info=Tenant.get('admin'),
             con_ssh=None):
    LOG.info("Updating {}...".format(user))
    arg = ''
    optional_args = {
        'name': name,
        'project': project,
        'password': password,
        'project-domain': project_doamin,
        'email': email,
        'description': description,
    }
    for key, val in optional_args.items():
        if val is not None:
            arg += "--{} '{}' ".format(key, val)

    if enable is not None:
        arg += '--{} '.format('enable' if enable else 'disable')

    if not arg.strip():
        raise ValueError(
            "Please specify the param(s) and value(s) to change to")

    arg += user

    code, output = cli.openstack('user set', arg, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, output

    if name or project or password:
        tenant_dictname = user.upper()
        Tenant.update(tenant_dictname, username=name, password=password,
                      tenant=project)

    if password and user == 'admin':
        from consts.proj_vars import ProjVar
        if ProjVar.get_var('REGION') != 'RegionOne':
            LOG.info(
                "Run openstack_update_admin_password on secondary region "
                "after admin password change")
            if not con_ssh:
                con_ssh = ControllerClient.get_active_controller()
            with con_ssh.login_as_root(timeout=30) as con_ssh:
                con_ssh.exec_cmd(
                    "echo 'y' | openstack_update_admin_password '{}'".format(
                        password))

    msg = 'User {} updated successfully'.format(user)
    LOG.info(msg)
    return 0, output


def get_endpoints(field='ID', endpoint_id=None, service_name=None,
                  service_type=None, enabled=None, interface="admin",
                  region=None, url=None, strict=False,
                  auth_info=Tenant.get('admin'), con_ssh=None, cli_filter=True):
    """
    Get a list of endpoints with given arguments
    Args:
        field (str|list|tuple): valid header of openstack endpoints list
        table. 'ID'
        endpoint_id (str): id of the endpoint
        service_name (str): Service name of endpoint like novaav3, neutron,
        keystone. vim, heat, swift, etc
        service_type(str): Service type
        enabled (str): True/False
        interface (str): Interface of endpoints. valid entries: admin,
        internal, public
        region (str): RegionOne or RegionTwo
        url (str): url of endpoint
        strict(bool):
        auth_info (dict):
        con_ssh (SSHClient):
        cli_filter (bool): whether to filter out using cli. e.g., openstack
        endpoint list --service xxx

    Returns (list):

    """
    pre_args_str = ''
    if cli_filter:
        pre_args_dict = {
            '--service': service_name,
            '--interface': interface,
            '--region': region,
        }

        pre_args = []
        for key, val in pre_args_dict.items():
            if val:
                pre_args.append('{}={}'.format(key, val))
        pre_args_str = ' '.join(pre_args)

    output = cli.openstack('endpoint list', positional_args=pre_args_str,
                           ssh_client=con_ssh, auth_info=auth_info)[1]
    if not output.strip():
        LOG.warning("No endpoints returned with param: {}".format(pre_args_str))
        return []

    table_ = table_parser.table(output)

    kwargs = {
        'ID': endpoint_id,
        'Service Name': service_name,
        'Service Type': service_type,
        'Enabled': enabled,
        'Interface': interface,
        'URL': url,
        'Region': region,
    }
    kwargs = {k: v for k, v in kwargs.items() if v}
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=True, merge_lines=True, **kwargs)


def get_endpoints_values(endpoint_id, fields, con_ssh=None,
                         auth_info=Tenant.get('admin')):
    """
    Gets the  endpoint target field value for given  endpoint Id
    Args:
        endpoint_id: the endpoint id to get the value of
        fields: the target field name to retrieve value of
        con_ssh:
        auth_info

    Returns (list): list of endpoint values

    """
    table_ = table_parser.table(
        cli.openstack('endpoint show', endpoint_id, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields)


def is_https_enabled(con_ssh=None, source_openrc=True,
                     auth_info=Tenant.get('admin_platform')):
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    table_ = table_parser.table(
        cli.openstack('endpoint list', ssh_client=con_ssh, auth_info=auth_info,
                      source_openrc=source_openrc)[1])
    con_ssh.exec_cmd('unset OS_REGION_NAME')  # Workaround
    filters = {'Service Name': 'keystone', 'Service Type': 'identity',
               'Interface': 'public'}
    keystone_pub = table_parser.get_values(table_=table_, target_header='URL',
                                           **filters)[0]
    return 'https' in keystone_pub


def delete_users(user, fail_ok=False, auth_info=Tenant.get('admin'),
                 con_ssh=None):
    """
    Delete the given openstack user
    Args:
        user: user name to delete
        fail_ok: if the deletion expected to fail
        auth_info
        con_ssh

    Returns: tuple, (code, msg)
    """
    return cli.openstack('user delete', user, ssh_client=con_ssh,
                         fail_ok=fail_ok, auth_info=auth_info)


def get_projects(field='ID', auth_info=Tenant.get('admin'), con_ssh=None,
                 strict=False, **filters):
    """
    Get list of Project names or IDs
    Args:
        field (str|list|tuple):
        auth_info:
        con_ssh:
        strict (bool): used for filters
        filters

    Returns (list):

    """
    table_ = table_parser.table(
        cli.openstack('project list', ssh_client=con_ssh, auth_info=auth_info)[
            1])
    return table_parser.get_multi_values(table_, field, strict=strict,
                                         **filters)


def create_project(name=None, field='ID', domain=None, parent=None,
                   description=None, enable=None, con_ssh=None,
                   rtn_exist=None, fail_ok=False, auth_info=Tenant.get('admin'),
                   **properties):
    """
    Create a openstack project
    Args:
        name (str|None):
        field (str): ID or Name. Whether to return project id or name if
        created successfully
        domain (str|None):
        parent (str|None):
        description (str|None):
        enable (bool|None):
        con_ssh:
        rtn_exist
        fail_ok:
        auth_info:
        **properties:

    Returns (tuple):
        (0, <project>)
        (1, <std_err>)

    """
    if not name:
        existing_names = get_projects(field='Name',
                                      auth_info=Tenant.get('admin'),
                                      con_ssh=con_ssh)
        max_count = 0
        end_str = ''
        for name in existing_names:
            match = re.match(r'tenant(\d+)(.*)', name)
            if match:
                count, end_str = match.groups()
                max_count = max(int(count), max_count)
        name = 'tenant{}{}'.format(max_count + 1, end_str)

    LOG.info("Create/Show openstack project {}".format(name))

    arg_dict = {
        'domain': domain,
        'parent': parent,
        'description': description,
        'enable': True if enable is True else None,
        'disable': True if enable is False else None,
        'or-show': rtn_exist,
        'property': properties,
    }

    arg_str = common.parse_args(args_dict=arg_dict, repeat_arg=True)
    arg_str += ' {}'.format(name)

    code, output = cli.openstack('project create', arg_str, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    project_ = table_parser.get_value_two_col_table(table_parser.table(output),
                                                    field=field)
    LOG.info("Project {} successfully created/showed.".format(project_))

    return 0, project_


def create_user(name=None, field='name', domain=None, project=None,
                project_domain=None, rtn_exist=None,
                password=HostLinuxUser.get_password(), email=None,
                description=None, enable=None,
                auth_info=Tenant.get('admin'), fail_ok=False, con_ssh=None):
    """
    Create an openstack user
    Args:
        name (str|None):
        field: name or id
        domain:
        project (str|None): default project
        project_domain:
        rtn_exist (bool)
        password:
        email:
        description:
        enable:
        auth_info:
        fail_ok:
        con_ssh:

    Returns (tuple):
        (0, <user>)
        (1, <std_err>)

    """

    if not name:
        name = 'user'
        common.get_unique_name(name_str=name)

    LOG.info("Create/Show openstack user {}".format(name))
    arg_dict = {
        'domain': domain,
        'project': project,
        'project-domain': project_domain,
        'password': password,
        'email': email,
        'description': description,
        'enable': True if enable is True else None,
        'disable': True if enable is False else None,
        'or-show': rtn_exist,
    }

    arg_str = '{} {}'.format(common.parse_args(args_dict=arg_dict), name)

    code, output = cli.openstack('user create', arg_str, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    user = table_parser.get_value_two_col_table(table_parser.table(output),
                                                field=field)
    LOG.info("Openstack user {} successfully created/showed".format(user))

    return 0, user
