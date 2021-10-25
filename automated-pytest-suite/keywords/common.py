#
# Copyright (c) 2019, 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


#############################################################
# DO NOT import anything from helper modules to this module #
#############################################################

import socket
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime

import pexpect
import yaml
from pytest import skip

from consts.auth import Tenant, TestFileServer, HostLinuxUser
from consts.stx import Prompt
from consts.proj_vars import ProjVar
from utils import exceptions
from utils.clients.ssh import ControllerClient, NATBoxClient, SSHClient, \
    get_cli_client
from utils.tis_log import LOG


def scp_from_test_server_to_user_file_dir(source_path, dest_dir, dest_name=None,
                                          timeout=900, con_ssh=None,
                                          central_region=False):
    if con_ssh is None:
        con_ssh = get_cli_client(central_region=central_region)
    if dest_name is None:
        dest_name = source_path.split(sep='/')[-1]

    if ProjVar.get_var('USER_FILE_DIR') == ProjVar.get_var('TEMP_DIR'):
        LOG.info("Copy file from test server to localhost")
        source_server = TestFileServer.SERVER
        source_user = TestFileServer.USER
        source_password = TestFileServer.PASSWORD
        dest_path = dest_dir if not dest_name else os.path.join(dest_dir,
                                                                dest_name)
        LOG.info('Check if file already exists on TiS')
        if con_ssh.file_exists(file_path=dest_path):
            LOG.info('dest path {} already exists. Return existing path'.format(
                dest_path))
            return dest_path

        os.makedirs(dest_dir, exist_ok=True)
        con_ssh.scp_on_dest(source_user=source_user, source_ip=source_server,
                            source_path=source_path,
                            dest_path=dest_path, source_pswd=source_password,
                            timeout=timeout)
        return dest_path
    else:
        LOG.info("Copy file from test server to active controller")
        return scp_from_test_server_to_active_controller(
            source_path=source_path, dest_dir=dest_dir,
            dest_name=dest_name, timeout=timeout, con_ssh=con_ssh)


def _scp_from_remote_to_active_controller(source_server, source_path,
                                          dest_dir, dest_name=None,
                                          source_user=None,
                                          source_password=None,
                                          timeout=900, con_ssh=None,
                                          is_dir=False):
    """
    SCP file or files under a directory from remote server to TiS server

    Args:
        source_path (str): remote server file path or directory path
        dest_dir (str): destination directory. should end with '/'
        dest_name (str): destination file name if not dir
        timeout (int):
        con_ssh:
        is_dir

    Returns (str|None): destination file/dir path if scp successful else None

    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    if not source_user:
        source_user = TestFileServer.USER
    if not source_password:
        source_password = TestFileServer.PASSWORD

    if dest_name is None and not is_dir:
        dest_name = source_path.split(sep='/')[-1]

    dest_path = dest_dir if not dest_name else os.path.join(dest_dir, dest_name)

    LOG.info('Check if file already exists on TiS')
    if not is_dir and con_ssh.file_exists(file_path=dest_path):
        LOG.info('dest path {} already exists. Return existing path'.format(
            dest_path))
        return dest_path

    LOG.info('Create destination directory on tis server if not already exists')
    cmd = 'mkdir -p {}'.format(dest_dir)
    con_ssh.exec_cmd(cmd, fail_ok=False)

    nat_name = ProjVar.get_var('NATBOX')
    if nat_name:
        nat_name = nat_name.get('name')
    if nat_name and ProjVar.get_var('IS_VBOX'):
        LOG.info('VBox detected, performing intermediate scp')

        nat_dest_path = '/tmp/{}'.format(dest_name)
        nat_ssh = NATBoxClient.get_natbox_client()

        if not nat_ssh.file_exists(nat_dest_path):
            LOG.info("scp file from {} to NatBox: {}".format(nat_name,
                                                             source_server))
            nat_ssh.scp_on_dest(source_user=source_user,
                                source_ip=source_server,
                                source_path=source_path,
                                dest_path=nat_dest_path,
                                source_pswd=source_password, timeout=timeout,
                                is_dir=is_dir)

        LOG.info(
            'scp file from natbox {} to active controller'.format(nat_name))
        dest_user = HostLinuxUser.get_user()
        dest_pswd = HostLinuxUser.get_password()
        dest_ip = ProjVar.get_var('LAB').get('floating ip')
        nat_ssh.scp_on_source(source_path=nat_dest_path, dest_user=dest_user,
                              dest_ip=dest_ip, dest_path=dest_path,
                              dest_password=dest_pswd, timeout=timeout,
                              is_dir=is_dir)

    else:  # if not a VBox lab, scp from remote server directly to TiS server
        LOG.info("scp file(s) from {} to tis".format(source_server))
        con_ssh.scp_on_dest(source_user=source_user, source_ip=source_server,
                            source_path=source_path,
                            dest_path=dest_path, source_pswd=source_password,
                            timeout=timeout, is_dir=is_dir)

    return dest_path


def scp_from_test_server_to_active_controller(source_path, dest_dir,
                                              dest_name=None, timeout=900,
                                              con_ssh=None,
                                              is_dir=False):
    """
    SCP file or files under a directory from test server to TiS server

    Args:
        source_path (str): test server file path or directory path
        dest_dir (str): destination directory. should end with '/'
        dest_name (str): destination file name if not dir
        timeout (int):
        con_ssh:
        is_dir (bool)

    Returns (str|None): destination file/dir path if scp successful else None

    """
    skip('Shared Test File Server is not ready')
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    source_server = TestFileServer.SERVER
    source_user = TestFileServer.USER
    source_password = TestFileServer.PASSWORD

    return _scp_from_remote_to_active_controller(
        source_server=source_server,
        source_path=source_path,
        dest_dir=dest_dir,
        dest_name=dest_name,
        source_user=source_user,
        source_password=source_password,
        timeout=timeout,
        con_ssh=con_ssh,
        is_dir=is_dir)


def scp_from_active_controller_to_test_server(source_path, dest_dir,
                                              dest_name=None, timeout=900,
                                              is_dir=False,
                                              con_ssh=None):
    """
    SCP file or files under a directory from test server to TiS server

    Args:
        source_path (str): test server file path or directory path
        dest_dir (str): destination directory. should end with '/'
        dest_name (str): destination file name if not dir
        timeout (int):
        is_dir (bool):
        con_ssh:

    Returns (str|None): destination file/dir path if scp successful else None

    """
    skip('Shared Test File Server is not ready')
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    dir_option = '-r ' if is_dir else ''
    dest_server = TestFileServer.SERVER
    dest_user = TestFileServer.USER
    dest_password = TestFileServer.PASSWORD

    dest_path = dest_dir if not dest_name else os.path.join(dest_dir, dest_name)

    scp_cmd = 'scp -oStrictHostKeyChecking=no -o ' \
              'UserKnownHostsFile=/dev/null ' \
              '{}{} {}@{}:{}'.\
        format(dir_option, source_path, dest_user, dest_server, dest_path)

    LOG.info("scp file(s) from tis server to test server")
    con_ssh.send(scp_cmd)
    index = con_ssh.expect(
        [con_ssh.prompt, Prompt.PASSWORD_PROMPT, Prompt.ADD_HOST],
        timeout=timeout)
    if index == 2:
        con_ssh.send('yes')
        index = con_ssh.expect([con_ssh.prompt, Prompt.PASSWORD_PROMPT],
                               timeout=timeout)
    if index == 1:
        con_ssh.send(dest_password)
        index = con_ssh.expect(timeout=timeout)

    assert index == 0, "Failed to scp files"

    exit_code = con_ssh.get_exit_code()
    assert 0 == exit_code, "scp not fully succeeded"

    return dest_path


def scp_from_localhost_to_active_controller(
        source_path, dest_path=None,
        dest_user=None,
        dest_password=None,
        timeout=900, is_dir=False):

    active_cont_ip = ControllerClient.get_active_controller().host
    if not dest_path:
        dest_path = HostLinuxUser.get_home()
    if not dest_user:
        dest_user = HostLinuxUser.get_user()
    if not dest_password:
        dest_password = HostLinuxUser.get_password()

    return scp_from_local(source_path, active_cont_ip, dest_path=dest_path,
                          dest_user=dest_user, dest_password=dest_password,
                          timeout=timeout, is_dir=is_dir)


def scp_from_active_controller_to_localhost(
        source_path, dest_path='',
        src_user=None,
        src_password=None,
        timeout=900, is_dir=False):

    active_cont_ip = ControllerClient.get_active_controller().host
    if not src_user:
        src_user = HostLinuxUser.get_user()
    if not src_password:
        src_password = HostLinuxUser.get_password()

    return scp_to_local(source_path=source_path, source_ip=active_cont_ip,
                        source_user=src_user, source_password=src_password,
                        dest_path=dest_path, timeout=timeout, is_dir=is_dir)


def scp_from_local(source_path, dest_ip, dest_path,
                   dest_user,
                   dest_password,
                   timeout=900, is_dir=False):
    """
    Scp file(s) from localhost (i.e., from where the automated tests are
    executed).

    Args:
        source_path (str): source file/directory path
        dest_ip (str): ip of the destination host
        dest_user (str): username of destination host.
        dest_password (str): password of destination host
        dest_path (str): destination directory path to copy the file(s) to
        timeout (int): max time to wait for scp finish in seconds
        is_dir (bool): whether to copy a single file or a directory

    """
    dir_option = '-r ' if is_dir else ''

    cmd = 'scp -oStrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ' \
          '{}{} {}@{}:{}'. \
        format(dir_option, source_path, dest_user, dest_ip, dest_path)

    _scp_on_local(cmd, remote_password=dest_password, timeout=timeout)


def scp_to_local(source_path, source_ip, source_user, source_password,
                 dest_path, timeout=900, is_dir=False):
    """
    Scp file(s) to localhost (i.e., to where the automated tests are executed).

    Args:
        source_path (str): source file/directory path
        source_ip (str): ip of the source host.
        source_user (str): username of source host.
        source_password (str): password of source host
        dest_path (str): destination directory path to copy the file(s) to
        timeout (int): max time to wait for scp finish in seconds
        is_dir (bool): whether to copy a single file or a directory

    """
    dir_option = '-r ' if is_dir else ''
    cmd = 'scp -oStrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ' \
          '{}{}@{}:{} {}'.\
        format(dir_option, source_user, source_ip, source_path, dest_path)

    _scp_on_local(cmd, remote_password=source_password, timeout=timeout)


def _scp_on_local(cmd, remote_password, logdir=None, timeout=900):
    LOG.debug('scp cmd: {}'.format(cmd))

    logdir = logdir or ProjVar.get_var('LOG_DIR')
    logfile = os.path.join(logdir, 'scp_files.log')

    with open(logfile, mode='a', encoding='utf8') as f:
        local_child = pexpect.spawn(command=cmd, encoding='utf-8', logfile=f)
        index = local_child.expect([pexpect.EOF, 'assword:', 'yes/no'],
                                   timeout=timeout)

        if index == 2:
            local_child.sendline('yes')
            index = local_child.expect([pexpect.EOF, 'assword:'],
                                       timeout=timeout)

        if index == 1:
            local_child.sendline(remote_password)
            local_child.expect(pexpect.EOF, timeout=timeout)


def get_tenant_name(auth_info=None):
    """
    Get name of given tenant. If None is given, primary tenant name will be
    returned.

    Args:
        auth_info (dict|None): Tenant dict

    Returns:
        str: name of the tenant

    """
    if auth_info is None:
        auth_info = Tenant.get_primary()
    return auth_info['tenant']


class Count:
    __vm_count = 0
    __flavor_count = 0
    __volume_count = 0
    __image_count = 0
    __server_group = 0
    __router = 0
    __subnet = 0
    __other = 0

    @classmethod
    def get_vm_count(cls):
        cls.__vm_count += 1
        return cls.__vm_count

    @classmethod
    def get_flavor_count(cls):
        cls.__flavor_count += 1
        return cls.__flavor_count

    @classmethod
    def get_volume_count(cls):
        cls.__volume_count += 1
        return cls.__volume_count

    @classmethod
    def get_image_count(cls):
        cls.__image_count += 1
        return cls.__image_count

    @classmethod
    def get_sever_group_count(cls):
        cls.__server_group += 1
        return cls.__server_group

    @classmethod
    def get_router_count(cls):
        cls.__router += 1
        return cls.__router

    @classmethod
    def get_subnet_count(cls):
        cls.__subnet += 1
        return cls.__subnet

    @classmethod
    def get_other_count(cls):
        cls.__other += 1
        return cls.__other


class NameCount:
    __names_count = {
        'vm': 0,
        'flavor': 0,
        'volume': 0,
        'image': 0,
        'server_group': 0,
        'subnet': 0,
        'heat_stack': 0,
        'qos': 0,
        'other': 0,
    }

    @classmethod
    def get_number(cls, resource_type='other'):
        cls.__names_count[resource_type] += 1
        return cls.__names_count[resource_type]

    @classmethod
    def get_valid_types(cls):
        return list(cls.__names_count.keys())


def get_unique_name(name_str, existing_names=None, resource_type='other'):
    """
    Get a unique name string by appending a number to given name_str

    Args:
        name_str (str): partial name string
        existing_names (list): names to avoid
        resource_type (str): type of resource. valid values: 'vm'

    Returns:

    """
    valid_types = NameCount.get_valid_types()
    if resource_type not in valid_types:
        raise ValueError(
            "Invalid resource_type provided. Valid types: {}".format(
                valid_types))

    if existing_names:
        if resource_type in ['image', 'volume', 'flavor']:
            unique_name = name_str
        else:
            unique_name = "{}-{}".format(name_str, NameCount.get_number(
                resource_type=resource_type))

        for i in range(50):
            if unique_name not in existing_names:
                return unique_name

            unique_name = "{}-{}".format(name_str, NameCount.get_number(
                resource_type=resource_type))
        else:
            raise LookupError("Cannot find unique name.")
    else:
        unique_name = "{}-{}".format(name_str, NameCount.get_number(
            resource_type=resource_type))

    return unique_name


def parse_cpus_list(cpus):
    """
    Convert human friendly pcup list to list of integers.
    e.g., '5-7,41-43, 43, 45' >> [5, 6, 7, 41, 42, 43, 43, 45]

    Args:
        cpus (str):

    Returns (list): list of integers

    """
    if isinstance(cpus, str):
        if cpus.strip() == '':
            return []

        cpus = cpus.split(sep=',')

    cpus_list = list(cpus)

    for val in cpus:
        # convert '3-6' to [3, 4, 5, 6]
        if '-' in val:
            cpus_list.remove(val)
            min_, max_ = val.split(sep='-')

            # unpinned:20; pinned_cpulist:-, unpinned_cpulist:10-19,30-39
            if min_ != '':
                cpus_list += list(range(int(min_), int(max_) + 1))

    return sorted([int(val) for val in cpus_list])


def get_timedelta_for_isotimes(time1, time2):
    """

    Args:
        time1 (str): such as "2016-08-16T12:59:45.440697+00:00"
        time2 (str):

    Returns ()

    """

    def _parse_time(time_):
        time_ = time_.strip().split(sep='.')[0].split(sep='+')[0]
        if 'T' in time_:
            pattern = "%Y-%m-%dT%H:%M:%S"
        elif ' ' in time_:
            pattern = "%Y-%m-%d %H:%M:%S"
        else:
            raise ValueError("Unknown format for time1: {}".format(time_))
        time_datetime = datetime.strptime(time_, pattern)
        return time_datetime

    time1_datetime = _parse_time(time_=time1)
    time2_datetime = _parse_time(time_=time2)

    return time2_datetime - time1_datetime


def _execute_with_openstack_cli():
    """
    DO NOT USE THIS IN TEST FUNCTIONS!
    """
    return ProjVar.get_var('OPENSTACK_CLI')


def get_date_in_format(ssh_client=None, date_format="%Y%m%d %T"):
    """
    Get date in given format.
    Args:
        ssh_client (SSHClient):
        date_format (str): Please see date --help for valid format strings

    Returns (str): date output in given format

    """
    if ssh_client is None:
        ssh_client = ControllerClient.get_active_controller()
    return ssh_client.exec_cmd("date +'{}'".format(date_format), fail_ok=False)[
        1]


def write_to_file(file_path, content, mode='a'):
    """
    Write content to specified local file
    Args:
        file_path (str): file path on localhost
        content (str): content to write to file
        mode (str): file operation mode. Default is 'a' (append to end of file).

    Returns: None

    """
    time_stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    with open(file_path, mode=mode, encoding='utf8') as f:
        f.write(
            '\n-----------------[{}]-----------------\n{}\n'.format(time_stamp,
                                                                    content))


def collect_software_logs(con_ssh=None):
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    LOG.info("Collecting all hosts logs...")
    con_ssh.exec_cmd('source /etc/platform/openrc', get_exit_code=False)
    con_ssh.send('collect all')

    expect_list = ['.*password for sysadmin:', 'collecting data.',
                   con_ssh.prompt]
    index_1 = con_ssh.expect(expect_list, timeout=20)
    if index_1 == 2:
        LOG.error(
            "Something is wrong with collect all. Check ssh console log for "
            "detail.")
        return
    elif index_1 == 0:
        con_ssh.send(con_ssh.password)
        con_ssh.expect('collecting data')

    index_2 = con_ssh.expect(['/scratch/ALL_NODES.*', con_ssh.prompt],
                             timeout=1200)
    if index_2 == 0:
        output = con_ssh.cmd_output
        con_ssh.expect()
        logpath = re.findall('.*(/scratch/ALL_NODES_.*.tar).*', output)[0]
        LOG.info(
            "\n################### TiS server log path: {}".format(logpath))
    else:
        LOG.error("Collecting logs failed. No ALL_NODES logs found.")
        return

    dest_path = ProjVar.get_var('LOG_DIR')
    try:
        LOG.info("Copying log file from active controller to local {}".format(
            dest_path))
        scp_from_active_controller_to_localhost(
            source_path=logpath, dest_path=dest_path, timeout=300)
        LOG.info("{} is successfully copied to local directory: {}".format(
            logpath, dest_path))
    except Exception as e:
        LOG.warning("Failed to copy log file to localhost.")
        LOG.error(e, exc_info=True)


def parse_args(args_dict, repeat_arg=False, vals_sep=' '):
    """
    parse args dictionary and convert it to string
    Args:
        args_dict (dict): key/value pairs
        repeat_arg: if value is tuple, list, dict, should the arg be repeated.
            e.g., True for --nic in nova boot. False for -m in gnocchi
            measures aggregation
        vals_sep (str): separator to join multiple vals. Only applicable when
        repeat_arg=False.

    Returns (str):

    """

    def convert_val_dict(key__, vals_dict, repeat_key):
        vals_ = []
        for k, v in vals_dict.items():
            if ' ' in v:
                v = '"{}"'.format(v)
            vals_.append('{}={}'.format(k, v))
        if repeat_key:
            args_str = ' ' + ' '.join(
                ['{} {}'.format(key__, v_) for v_ in vals_])
        else:
            args_str = ' {} {}'.format(key__, vals_sep.join(vals_))
        return args_str

    args = ''
    for key, val in args_dict.items():
        if val is None:
            continue

        key = key if key.startswith('-') else '--{}'.format(key)
        if isinstance(val, str):
            if ' ' in val:
                val = '"{}"'.format(val)
            args += ' {}={}'.format(key, val)
        elif isinstance(val, bool):
            if val:
                args += ' {}'.format(key)
        elif isinstance(val, (int, float)):
            args += ' {}={}'.format(key, val)
        elif isinstance(val, dict):
            args += convert_val_dict(key__=key, vals_dict=val,
                                     repeat_key=repeat_arg)
        elif isinstance(val, (list, tuple)):
            if repeat_arg:
                for val_ in val:
                    if isinstance(val_, dict):
                        args += convert_val_dict(key__=key, vals_dict=val_,
                                                 repeat_key=False)
                    else:
                        args += ' {}={}'.format(key, val_)
            else:
                args += ' {}={}'.format(key, vals_sep.join(val))
        else:
            raise ValueError(
                "Unrecognized value type. Key: {}; value: {}".format(key, val))

    return args.strip()


def get_symlink(ssh_client, file_path):
    code, output = ssh_client.exec_cmd(
        'ls -l {} | grep --color=never ""'.format(file_path))
    if code != 0:
        LOG.warning('{} not found!'.format(file_path))
        return None

    res = re.findall('> (.*)', output)
    if not res:
        LOG.warning('No symlink found for {}'.format(file_path))
        return None

    link = res[0].strip()
    return link


def is_file(filename, ssh_client):
    code = ssh_client.exec_cmd('test -f {}'.format(filename), fail_ok=True)[0]
    return 0 == code


def is_directory(dirname, ssh_client):
    code = ssh_client.exec_cmd('test -d {}'.format(dirname), fail_ok=True)[0]
    return 0 == code


def lab_time_now(con_ssh=None, date_format='%Y-%m-%dT%H:%M:%S'):
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    date_cmd_format = date_format + '.%N'
    timestamp = get_date_in_format(ssh_client=con_ssh,
                                   date_format=date_cmd_format)
    with_milliseconds = timestamp.split('.')[0] + '.{}'.format(
        int(int(timestamp.split('.')[1]) / 1000))
    format1 = date_format + '.%f'
    parsed = datetime.strptime(with_milliseconds, format1)

    return with_milliseconds.split('.')[0], parsed


@contextmanager
def ssh_to_remote_node(host, username=None, password=None, prompt=None,
                       ssh_client=None, use_telnet=False,
                       telnet_session=None):
    """
    ssh to a external node from sshclient.

    Args:
        host (str|None): hostname or ip address of remote node to ssh to.
        username (str):
        password (str):
        prompt (str):
        ssh_client (SSHClient): client to ssh from
        use_telnet:
        telnet_session:

    Returns (SSHClient): ssh client of the host

    Examples: with ssh_to_remote_node('128.224.150.92) as remote_ssh:
                  remote_ssh.exec_cmd(cmd)
    """

    if not host:
        raise exceptions.SSHException(
            "Remote node hostname or ip address must be provided")

    if use_telnet and not telnet_session:
        raise exceptions.SSHException(
            "Telnet session cannot be none if using telnet.")

    if not ssh_client and not use_telnet:
        ssh_client = ControllerClient.get_active_controller()

    if not use_telnet:
        from keywords.security_helper import LinuxUser
        default_user, default_password = LinuxUser.get_current_user_password()
    else:
        default_user = HostLinuxUser.get_user()
        default_password = HostLinuxUser.get_password()

    user = username if username else default_user
    password = password if password else default_password
    if use_telnet:
        original_host = telnet_session.exec_cmd('hostname')[1]
    else:
        original_host = ssh_client.host

    if not prompt:
        prompt = '.*' + host + r'\:~\$'

    remote_ssh = SSHClient(host, user=user, password=password,
                           initial_prompt=prompt)
    remote_ssh.connect()
    current_host = remote_ssh.host
    if not current_host == host:
        raise exceptions.SSHException(
            "Current host is {} instead of {}".format(current_host, host))
    try:
        yield remote_ssh
    finally:
        if current_host != original_host:
            remote_ssh.close()


def ssh_to_stx(lab=None, set_client=False):
    if not lab:
        lab = ProjVar.get_var('LAB')

    con_ssh = SSHClient(lab['floating ip'], user=HostLinuxUser.get_user(),
                        password=HostLinuxUser.get_password(),
                        initial_prompt=Prompt.CONTROLLER_PROMPT)

    con_ssh.connect(retry=True, retry_timeout=30, use_current=False)
    if set_client:
        ControllerClient.set_active_controller(con_ssh)

    return con_ssh


def get_yaml_data(filepath):
    """
    Returns the yaml data in json
    Args:
        filepath(str): location of the yaml file to load
    Return(json):
        returns the json data
    """
    with open(filepath, 'r', encoding='utf8') as f:
        data = yaml.safe_load(f)
    return data


def write_yaml_data_to_file(data, filename, directory=None):
    """
    Writes data to a file in yaml format
    Args:
        data(json): data in json format
        filename(str): filename
        directory(boo): directory to save the file
    Return(str):
        returns the location of the yaml file
    """
    if directory is None:
        directory = ProjVar.get_var('LOG_DIR')
    src_path = "{}/{}".format(directory, filename)
    with open(src_path, 'w', encoding='utf8') as f:
        yaml.dump(data, f)
    return src_path


def get_lab_fip(region=None):
    """
    Returns system OAM floating ip
    Args:
        region (str|None): central_region or subcloud, only applicable to DC
    Returns (str): floating ip of the lab
    """
    if ProjVar.get_var('IS_DC'):
        if not region:
            region = ProjVar.get_var('PRIMARY_SUBCLOUD')
        elif region == 'RegionOne':
            region = 'central_region'
        oam_fip = ProjVar.get_var('lab')[region]["floating ip"]
    else:
        oam_fip = ProjVar.get_var('lab')["floating ip"]

    return oam_fip


def get_dnsname(region='RegionOne'):
    # means that the dns name is unreachable
    return None