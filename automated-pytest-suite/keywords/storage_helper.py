#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


"""
This module provides helper functions for storage based testing

Including:
- system commands for system/host storage configs
- CEPH related helper functions that are not using system commands

"""

import re
import time

from consts.auth import Tenant
from consts.stx import EventLogID, BackendState, BackendTask, GuestImages, \
    PartitionStatus
from consts.timeout import HostTimeout, SysInvTimeout

from keywords import system_helper, host_helper, keystone_helper, common

from utils import table_parser, cli, exceptions
from utils.clients.ssh import ControllerClient, get_cli_client
from utils.tis_log import LOG


def is_ceph_healthy(con_ssh=None):
    """
    Query 'ceph -s' and return True if ceph health is okay
    and False otherwise.

    Args:
        con_ssh (SSHClient):

    Returns:
        - (bool) True if health okay, False otherwise
        - (string) message
    """

    health_ok = 'HEALTH_OK'
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    rtn_code, out = con_ssh.exec_cmd('ceph -s')
    if rtn_code > 0:
        LOG.warning('ceph -s failed to execute.')
        return False

    health_state = re.findall('health: (.*)\n', out)
    if not health_state:
        LOG.warning('Unable to determine ceph health state')
        return False

    health_state = health_state[0]
    if health_ok in health_state:
        LOG.info('CEPH cluster is healthy')
        return True

    msg = 'CEPH unhealthy. State: {}'.format(health_state)
    LOG.warning(msg)
    return False


def get_ceph_osd_count(fail_ok=False, con_ssh=None):
    """
    Return the number of OSDs on a CEPH system"
    Args:
        fail_ok
        con_ssh(SSHClient):

    Returns (int): Return the number of OSDs on the system,
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    rtn_code, out = con_ssh.exec_cmd('ceph -s', fail_ok=fail_ok)
    if rtn_code > 0:
        return 0

    osds = re.search(r'(\d+) osds', out)
    if osds:
        LOG.info('There are {} OSDs on the system'.format(osds.group(1)))
        return int(osds.group(1))

    msg = 'There are no OSDs on the system'
    LOG.info(msg)
    if fail_ok:
        return 0
    else:
        raise exceptions.StorageError(msg)


def get_osd_host(osd_id, fail_ok=False, con_ssh=None):
    """
    Return the host associated with the provided OSD ID
    Args:
        con_ssh(SSHClient):
        fail_ok
        osd_id (int): an OSD number, e.g. 0, 1, 2, 3...

    Returns (str|None): hostname is found else None
    """
    storage_hosts = system_helper.get_storage_nodes(con_ssh=con_ssh)
    for host in storage_hosts:
        osd_list = get_host_stors(host, 'osdid')
        if int(osd_id) in osd_list:
            msg = 'OSD ID {} is on host {}'.format(osd_id, host)
            LOG.info(msg)
            return host

    msg = 'Could not find host for OSD ID {}'.format(osd_id)
    LOG.warning(msg)
    if not fail_ok:
        raise exceptions.StorageError(msg)


def kill_process(host, pid):
    """
    Given the id of an OSD, kill the process and ensure it restarts.
    Args:
        host (string) - the host to ssh into, e.g. 'controller-1'
        pid (string) - pid to kill, e.g. '12345'

    Returns:
        - (bool) True if process was killed, False otherwise
        - (string) message
    """

    cmd = 'kill -9 {}'.format(pid)

    # SSH could be redundant if we are on controller-0 (oh well!)
    LOG.info('Kill process {} on {}'.format(pid, host))
    with host_helper.ssh_to_host(host) as host_ssh:
        with host_ssh.login_as_root() as root_ssh:
            root_ssh.exec_cmd(cmd, expect_timeout=60)
            LOG.info(cmd)

        LOG.info('Ensure the PID is no longer listed')
        pid_exists, msg = check_pid_exists(pid, root_ssh)
        if pid_exists:
            return False, msg

    return True, msg


def get_osd_pid(osd_host, osd_id, con_ssh=None, fail_ok=False):
    """
    Given the id of an OSD, return the pid.
    Args:
        osd_host (string) - the host to ssh into, e.g. 'storage-0'
        osd_id (int|str) - osd_id to get the pid of, e.g. '0'
        con_ssh
        fail_ok

    Returns (int|None):

    """
    pid_file = '/var/run/ceph/osd.{}.pid'.format(osd_id)
    return __get_pid_from_file(osd_host, pid_file=pid_file, con_ssh=con_ssh,
                               fail_ok=fail_ok)


def get_mon_pid(mon_host, con_ssh=None, fail_ok=False):
    """
    Given the host name of a monitor, return the pid of the ceph-mon process
    Args:
        mon_host (string) - the host to get the pid of, e.g. 'storage-1'
        con_ssh (SSHClient)
        fail_ok

    Returns (int|None)

    """
    pid_file = '/var/run/ceph/mon.{}.pid'.format(
        'controller' if system_helper.is_aio_duplex() else mon_host)
    return __get_pid_from_file(mon_host, pid_file=pid_file, con_ssh=con_ssh,
                               fail_ok=fail_ok)


def __get_pid_from_file(host, pid_file, con_ssh=None, fail_ok=False):
    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        rtn_code, out = host_ssh.exec_cmd('cat {}'.format(pid_file),
                                          expect_timeout=10, fail_ok=fail_ok)
        mon_match = r'(\d+)'
        pid = re.match(mon_match, out)
        if pid:
            msg = '{} for {} is {}'.format(pid_file, host, pid.group(1))
            LOG.info(msg)
            return pid.group(1)

    msg = '{} for {} was not found'.format(pid_file, host)
    LOG.warning(msg)
    if not fail_ok:
        raise exceptions.StorageError(msg)


def get_osds(host=None, con_ssh=None):
    """
    Given a hostname, get all OSDs on that host

    Args:
        con_ssh(SSHClient)
        host(str|None): the host to ssh into
    Returns:
        (list) List of OSDs on the host.  Empty list if none.
    """

    osd_list = []

    if host:
        osd_list += get_host_stors(host, 'osdid', con_ssh)
    else:
        storage_hosts = system_helper.get_storage_nodes()
        for host in storage_hosts:
            osd_list += get_host_stors(host, 'osdid', con_ssh)

    return osd_list


def is_osd_up(osd_id, con_ssh=None):
    """
    Determine if a particular OSD is up.

    Args:
        osd_id (int) - ID of OSD we want to query
        con_ssh

    Returns:
        (bool) True if OSD is up, False if OSD is down
    """

    cmd = r"ceph osd tree | grep 'osd.{}\s'".format(osd_id)
    rtn_code, out = con_ssh.exec_cmd(cmd, expect_timeout=60)
    if re.search('up', out):
        return True
    else:
        return False


def check_pid_exists(pid, host_ssh):
    """
    Check if a PID exists on a particular host.
    Args:
        host_ssh (SSHClient)
        pid (int|str): the process ID
    Returns (bool):
        True if pid exists and False otherwise
    """

    cmd = 'kill -0 {}'.format(pid)

    rtn_code, out = host_ssh.exec_cmd(cmd, expect_timeout=60)
    if rtn_code != 1:
        msg = 'Process {} exists'.format(pid)
        return True, msg

    msg = 'Process {} does not exist'.format(pid)
    return False, msg


def get_storage_group(host):
    """
    Determine the storage replication group name associated with the storage
    host.

    Args:
        host (string) - storage host, e.g. 'storage-0'
    Returns:
        storage_group (string) - group name, e.g. 'group-0'
        msg (string) - log message
    """
    peers = system_helper.get_host_values(host, fields='peers')[0]

    storage_group = re.search(r'(group-\d+)', peers)
    msg = 'Unable to determine replication group for {}'.format(host)
    assert storage_group, msg
    storage_group = storage_group.group(0)
    msg = 'The replication group for {} is {}'.format(host, storage_group)
    return storage_group, msg


def download_images(dload_type='all', img_dest='~/images/', con_ssh=None):
    """
    Retrieve images for testing purposes.  Note, this will add *a lot* of time
    to the test execution.

    Args:
        - type: 'all' to get all images (default),
                'ubuntu' to get ubuntu images,
                'centos' to get centos images
        - con_ssh
        - image destination - where on fileystem images are stored

    Returns:
        - List containing the names of the imported images
    """

    def _wget(urls):
        """
        This function does a wget on the provided urls.
        """
        for url in urls:
            cmd_ = 'wget {} --no-check-certificate -P {}'.format(url, img_dest)
            rtn_code_, out_ = con_ssh.exec_cmd(cmd_, expect_timeout=7200)
            assert not rtn_code, out_

    centos_image_location = \
        [
            'http://cloud.centos.org/centos/7/images/CentOS-7-x86_64'
            '-GenericCloud.qcow2',
            'http://cloud.centos.org/centos/6/images/CentOS-6-x86_64'
            '-GenericCloud.qcow2']

    ubuntu_image_location = \
        [
            'https://cloud-images.ubuntu.com/precise/current/precise-server'
            '-cloudimg-amd64-disk1.img']

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    LOG.info('Create directory for image storage')
    cmd = 'mkdir -p {}'.format(img_dest)
    rtn_code, out = con_ssh.exec_cmd(cmd)
    assert not rtn_code, out

    LOG.info('wget images')
    if dload_type == 'ubuntu' or dload_type == 'all':
        LOG.info("Downloading ubuntu image")
        _wget(ubuntu_image_location)
    elif dload_type == 'centos' or dload_type == 'all':
        LOG.info("Downloading centos image")
        _wget(centos_image_location)


def find_images(con_ssh=None, image_type='qcow2', image_name=None,
                location=None):
    """
    This function finds all images of a given type, in the given location.
    This is designed to save test time, to prevent downloading images if not
    necessary.

    Arguments:
        - image_type(string): image format, e.g. 'qcow2', 'raw', etc.
          - if the user specifies 'all', return all images
        - location(string): where to find images, e.g. '~/images'

    Test Steps:
        1.  Cycle through the files in a given location
        2.  Create a list of image names of the expected type

    Return:
        - image_names(list): list of image names of a given type, e.g.
          'cgcs-guest.img' or all images if the user specified 'all' as the
          argument to image_type.
    """

    image_names = []
    if not location:
        location = GuestImages.DEFAULT['image_dir']
    if not con_ssh:
        con_ssh = get_cli_client()

    cmd = 'ls {}'.format(location)
    rtn_code, out = con_ssh.exec_cmd(cmd)
    image_list = out.split()
    LOG.info('Found the following files: {}'.format(image_list))
    if image_type == 'all' and not image_name:
        return image_list, location

    # Return a list of image names where the image type matches what the user
    # is looking for, e.g. qcow2
    for image in image_list:
        if image_name and image_name not in image:
            continue
        image_path = location + "/" + image
        cmd = 'qemu-img info {}'.format(image_path)
        rtn_code, out = con_ssh.exec_cmd(cmd)
        if image_type in out:
            image_names.append(image)

    LOG.info('{} images available: {}'.format(image_type, image_names))
    return image_names, location


def find_image_size(con_ssh, image_name='cgcs-guest.img', location='~/images'):
    """
    This function uses qemu-img info to determine what size of flavor to use.
    Args:
        con_ssh:
        image_name (str): e.g. 'cgcs-guest.img'
        location (str):  where to find images, e.g. '~/images'

    Returns:
        image_size(int): e.g. 8
    """

    image_path = location + "/" + image_name
    cmd = 'qemu-img info {}'.format(image_path)
    rtn_code, out = con_ssh.exec_cmd(cmd)
    virtual_size = re.search(r'virtual size: (\d+\.*\d*[M|G])', out)
    msg = 'Unable to determine size of image {}'.format(image_name)
    assert virtual_size.group(0), msg
    # If the size is less than 1G, round to 1
    # If the size is greater than 1G, round up
    if 'M' in virtual_size.group(1):
        image_size = 1
    else:
        image_size = round(float(virtual_size.group(1).strip('G')))

    return image_size


def wait_for_ceph_health_ok(con_ssh=None, timeout=300, fail_ok=False,
                            check_interval=5):
    end_time = time.time() + timeout
    output = None
    while time.time() < end_time:
        rc, output = is_ceph_healthy(con_ssh=con_ssh)
        if rc:
            return True

        time.sleep(check_interval)
    else:
        err_msg = "Ceph is not healthy  within {} seconds: {}".format(timeout,
                                                                      output)
        if fail_ok:
            LOG.warning(err_msg)
            return False, err_msg
        else:
            raise exceptions.TimeoutException(err_msg)


def get_storage_backends(field='backend', con_ssh=None,
                         auth_info=Tenant.get('admin_platform'), **filters):
    """
    Get storage backends values from system storage-backend-list
    Args:
        field (str|list|tuple):
        con_ssh:
        auth_info:
        **filters:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('storage-backend-list', ssh_client=con_ssh,
                   auth_info=auth_info)[1],
        combine_multiline_entry=True)
    return table_parser.get_multi_values(table_, field, **filters)


def get_storage_backend_values(backend, fields=None, rtn_dict=False,
                               con_ssh=None,
                               auth_info=Tenant.get('admin_platform'),
                               **kwargs):
    """
    Get storage backend values for given backend via system storage-backend-show

    Args:
        backend (str): storage backend to get info (e.g. ceph)
        fields (list|tuple|str|None): keys to return, e.g., ['name',
        'backend', 'task']
        rtn_dict (bool)
        con_ssh:
        auth_info

    Returns (list|dict):
      Examples:
           Input: ('cinder_pool_gib', 'glance_pool_gib',
           'ephemeral_pool_gib', 'object_pool_gib',
                   'ceph_total_space_gib', 'object_gateway')
          Output:
            if rtn_dict: {'cinder_pool_gib': 202, 'glance_pool_gib': 20,
            'ephemeral_pool_gib': 0,
                              'object_pool_gib': 0, 'ceph_total_space_gib':
                              222,  'object_gateway': False}
            if list: [202, 20, 0, 0, 222, False]
    """
    # valid_backends = ['ceph-store', 'lvm-store', 'file-store',
    # 'shared_services]
    backend = backend.lower()
    if re.fullmatch('ceph|lvm|file', backend):
        backend += '-store'
    elif backend == 'external':
        backend = 'shared_services'

    table_ = table_parser.table(
        cli.system('storage-backend-show', backend, ssh_client=con_ssh,
                   auth_info=auth_info)[1],
        combine_multiline_entry=True)
    if not fields:
        fields = table_parser.get_column(table_, 'Property')
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       evaluate=True,
                                                       rtn_dict=rtn_dict,
                                                       **kwargs)


def wait_for_storage_backend_vals(backend, timeout=300, fail_ok=False,
                                  con_ssh=None,
                                  auth_info=Tenant.get('admin_platform'),
                                  **expt_values):
    if not expt_values:
        raise ValueError(
            "At least one key/value pair has to be provided via expt_values")

    LOG.info(
        "Wait for storage backend {} to reach: {}".format(backend, expt_values))
    end_time = time.time() + timeout
    dict_to_check = expt_values.copy()
    stor_backend_info = None
    while time.time() < end_time:
        stor_backend_info = get_storage_backend_values(
            backend=backend, fields=list(dict_to_check.keys()),
            rtn_dict=True, con_ssh=con_ssh, auth_info=auth_info)
        dict_to_iter = dict_to_check.copy()
        for key, expt_val in dict_to_iter.items():
            actual_val = stor_backend_info[key]
            if str(expt_val) == str(actual_val):
                dict_to_check.pop(key)

        if not dict_to_check:
            return True, dict_to_check

    if fail_ok:
        return False, stor_backend_info
    raise exceptions.StorageError(
        "Storage backend show field(s) did not reach expected value(s). "
        "Expected: {}; Actual: {}".format(dict_to_check, stor_backend_info))


def add_storage_backend(backend='ceph', ceph_mon_gib='20', ceph_mon_dev=None,
                        ceph_mon_dev_controller_0_uuid=None,
                        ceph_mon_dev_controller_1_uuid=None, con_ssh=None,
                        fail_ok=False):
    """

    Args:
        backend (str): The backend to add. Only ceph is supported
        ceph_mon_gib(int/str): The ceph-mon-lv size in GiB. The default is 20GiB
        ceph_mon_dev (str): The disk device that the ceph-mon will be created
            on. This applies to both controllers. In
            case of separate device names on controllers use the options
            below to specify device name for each controller
        ceph_mon_dev_controller_0_uuid (str): The uuid of controller-0 disk
        device that the ceph-mon will be created on
        ceph_mon_dev_controller_1_uuid (str): The uuid of controller-1 disk
        device that the ceph-mon will be created on
        con_ssh:
        fail_ok:

    Returns:

    """

    if backend is not 'ceph':
        msg = "Invalid backend {} specified. Valid choices are {}".format(
            backend, ['ceph'])
        if fail_ok:
            return 1, msg
        else:
            raise exceptions.CLIRejected(msg)
    if isinstance(ceph_mon_gib, int):
        ceph_mon_gib = str(ceph_mon_gib)

    cmd = 'system storage-backend-add --ceph-mon-gib {}'.format(ceph_mon_gib)
    if ceph_mon_dev:
        cmd += ' --ceph-mon-dev {}'.format(
            ceph_mon_dev if '/dev' in ceph_mon_dev else '/dev/' +
                                                        ceph_mon_dev.strip())
    if ceph_mon_dev_controller_0_uuid:
        cmd += ' --ceph_mon_dev_controller_0_uuid {}'.format(
            ceph_mon_dev_controller_0_uuid)
    if ceph_mon_dev_controller_1_uuid:
        cmd += ' --ceph_mon_dev_controller_1_uuid {}'.format(
            ceph_mon_dev_controller_1_uuid)

    cmd += " {}".format(backend)
    controler_ssh = con_ssh if con_ssh else \
        ControllerClient.get_active_controller()
    controler_ssh.send(cmd)
    index = controler_ssh.expect([controler_ssh.prompt, r'\[yes/N\]'])
    if index == 1:
        controler_ssh.send('yes')
        controler_ssh.expect()

    rc, output = controler_ssh.process_cmd_result(cmd)
    if rc != 0:
        if fail_ok:
            return rc, output
        raise exceptions.CLIRejected("Fail Cli command cmd: {}".format(cmd))
    else:
        output = table_parser.table(output)
        return rc, output


def modify_storage_backend(backend, cinder=None, glance=None, ephemeral=None,
                           object_gib=None, object_gateway=None,
                           services=None, lock_unlock=False, fail_ok=False,
                           con_ssh=None):
    """
    Modify ceph storage backend pool allocation

    Args:
        backend (str): storage backend to modify (e.g. ceph)
        cinder:
        glance:
        ephemeral:
        object_gib:
        object_gateway (bool|None)
        services (str|list|tuple):
        lock_unlock (bool): whether to wait for config out-of-date alarms
        against controllers and lock/unlock them
        fail_ok:
        con_ssh:

    Returns:
        0, dict of new allocation
        1, cli err message

    """
    if re.fullmatch('ceph|lvm|file', backend):
        backend += '-store'
    backend = backend.lower()

    args = ''
    if services:
        if isinstance(services, (list, tuple)):
            services = ','.join(services)
        args = '-s {} '.format(services)
    args += backend

    get_storage_backend_values(backend, fields='backend')

    if cinder:
        args += ' cinder_pool_gib={}'.format(cinder)

    if 'ceph' in backend:
        if glance:
            args += ' glance_pool_gib={}'.format(glance)
        if ephemeral:
            args += ' ephemeral_pool_gib={}'.format(ephemeral)
        if object_gateway is not None:
            args += ' object_gateway={}'.format(object_gateway)
        if object_gib:
            args += ' object_pool_gib={}'.format(object_gib)

    code, out = cli.system('storage-backend-modify', args, con_ssh,
                           fail_ok=fail_ok)
    if code > 0:
        return 1, out

    if lock_unlock:
        from testfixtures.recover_hosts import HostsToRecover
        LOG.info(
            "Lock unlock controllers and ensure config out-of-date alarms "
            "clear")
        system_helper.wait_for_alarm(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                                     timeout=30, fail_ok=False,
                                     entity_id='controller-')

        active_controller, standby_controller = \
            system_helper.get_active_standby_controllers(con_ssh=con_ssh)
        for controller in [standby_controller, active_controller]:
            if not controller:
                continue
            HostsToRecover.add(controller)
            host_helper.lock_host(controller, swact=True, con_ssh=con_ssh)
            wait_for_storage_backend_vals(
                backend=backend,
                **{'task': BackendTask.RECONFIG_CONTROLLER,
                   'state': BackendState.CONFIGURING})

            host_helper.unlock_host(controller, con_ssh=con_ssh)

        system_helper.wait_for_alarm_gone(
            alarm_id=EventLogID.CONFIG_OUT_OF_DATE, fail_ok=False)

    # TODO return new values of storage allocation and check they are the
    #  right values
    updated_backend_info = get_storage_backend_values(backend, rtn_dict=True)
    return 0, updated_backend_info


def add_ceph_mon(host, con_ssh=None, fail_ok=False):
    """

    Args:
        host:
        con_ssh:
        fail_ok:

    Returns:

    """

    valid_ceph_mon_hosts = ['controller-0', 'controller-1', 'storage-0',
                            'compute-0']
    if host not in valid_ceph_mon_hosts:
        msg = "Invalid host {} specified. Valid choices are {}".format(
            host, valid_ceph_mon_hosts)
        if fail_ok:
            return 1, msg
        else:
            raise exceptions.CLIRejected(msg)

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    existing_ceph_mons = get_ceph_mon_values(con_ssh=con_ssh)
    if host in existing_ceph_mons:
        state = get_ceph_mon_state(host, con_ssh=con_ssh)
        LOG.warning(
            "Host {} is already added as ceph-mon and is in state: {}".format(
                host, state))
        if state == 'configuring':
            wait_for_ceph_mon_configured(host, con_ssh=con_ssh, fail_ok=True)
            state = get_ceph_mon_state(host, con_ssh=con_ssh)
        if state == 'configured' or state == 'configuring':
            return 0, None
        else:
            msg = "The existing ceph-mon is in state {}".format(state)
            if fail_ok:
                return 1, msg
            else:
                raise exceptions.HostError(msg)

    if not host_helper.is_host_locked(host, con_ssh=con_ssh):
        rc, output = host_helper.lock_host(host, con_ssh=con_ssh)
        if rc != 0:
            msg = "Cannot add ceph-mon to host {} because the host fail to " \
                  "lock: {}".format(host, output)
            if fail_ok:
                return rc, msg
            else:
                raise exceptions.HostError(msg)

    cmd = 'ceph-mon-add'.format(host)

    rc, output = cli.system(cmd, host, ssh_client=con_ssh, fail_ok=fail_ok)
    if rc != 0:
        msg = "CLI command {} failed to add ceph mon in host {}: {}".format(
            cmd, host, output)
        LOG.warning(msg)
        if fail_ok:
            return rc, msg
        else:
            raise exceptions.StorageError(msg)
    rc, state, output = wait_for_ceph_mon_configured(host, con_ssh=con_ssh,
                                                     fail_ok=True)
    if state == 'configured':
        return 0, None
    elif state == 'configuring':
        return 1, "The ceph mon in host {} is in state {}".format(host, state)
    else:
        return 2, "The ceph mon in host {} failed: state = {}; msg = {}".format(
            host, state, output)


def wait_for_ceph_mon_configured(host, state=None,
                                 timeout=HostTimeout.CEPH_MON_ADD_CONFIG,
                                 con_ssh=None,
                                 fail_ok=False, check_interval=5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        state = get_ceph_mon_state(host, con_ssh=con_ssh)
        if state == 'configured':
            return True, state, None

        time.sleep(check_interval)

    msg = "The added ceph-mon on host {} did not reach configured state " \
          "within {} seconds. Last state = {}" \
        .format(host, timeout, state)
    if fail_ok:
        LOG.warning(msg)
        return False, state, msg
    else:
        raise exceptions.StorageError(msg)


def get_ceph_mon_values(field='hostname', hostname=None, uuid=None, state=None,
                        task=None, con_ssh=None):
    """

    Args:
        field:
        hostname:
        uuid:
        state:
        task:
        con_ssh:

    Returns:

    """
    ceph_mons = []
    table_ = table_parser.table(
        cli.system('ceph-mon-list', ssh_client=con_ssh)[1],
        combine_multiline_entry=True)

    filters = {}
    if table_:
        if hostname:
            filters['hostname'] = hostname
        if uuid:
            filters['uuid'] = uuid
        if state:
            filters['state'] = state
        if task:
            filters['task'] = task

        table_ = table_parser.filter_table(table_, **filters)
        ceph_mons = table_parser.get_column(table_, field)
    return ceph_mons


def get_ceph_mon_state(hostname, con_ssh=None):
    return get_ceph_mon_values(field='state', hostname=hostname,
                               con_ssh=con_ssh)[0]


def get_fs_mount_path(ssh_client, fs):
    mount_cmd = 'mount | grep --color=never {}'.format(fs)
    exit_code, output = ssh_client.exec_sudo_cmd(mount_cmd, fail_ok=True)

    mounted_on = fs_type = None
    msg = "Filesystem {} is not mounted".format(fs)
    is_mounted = exit_code == 0
    if is_mounted:
        # Get the first mount point
        mounted_on, fs_type = \
            re.findall('{} on ([^ ]*) type ([^ ]*) '.format(fs), output)[0]
        msg = "Filesystem {} is mounted on {}".format(fs, mounted_on)

    LOG.info(msg)
    return mounted_on, fs_type


def is_fs_auto_mounted(ssh_client, fs):
    auto_cmd = 'cat /etc/fstab | grep --color=never {}'.format(fs)
    exit_code, output = ssh_client.exec_sudo_cmd(auto_cmd, fail_ok=True)

    is_auto_mounted = exit_code == 0
    LOG.info("Filesystem {} is {}auto mounted".format(fs,
                                                      '' if is_auto_mounted
                                                      else 'not '))
    return is_auto_mounted


def mount_partition(ssh_client, disk, partition=None, fs_type=None):
    if not partition:
        partition = '/dev/{}'.format(disk)

    disk_id = ssh_client.exec_sudo_cmd(
        'blkid | grep --color=never "{}:"'.format(partition))[1]
    if disk_id:
        mount_on, fs_type_ = get_fs_mount_path(ssh_client=ssh_client,
                                               fs=partition)
        if mount_on:
            return mount_on, fs_type_

        fs_type = re.findall('TYPE="([^ ]*)"', disk_id)[0]
        if 'swap' == fs_type:
            fs_type = 'swap'
            turn_on_swap(ssh_client=ssh_client, disk=disk, partition=partition)
            mount_on = 'none'
    else:
        mount_on = None
        if not fs_type:
            fs_type = 'ext4'

        LOG.info("mkfs for {}".format(partition))

        cmd = "mkfs -t {} {}".format(fs_type, partition)
        ssh_client.exec_sudo_cmd(cmd, fail_ok=False)

    if not mount_on:
        mount_on = '/mnt/{}'.format(disk)
        LOG.info("mount {} to {}".format(partition, mount_on))
        ssh_client.exec_sudo_cmd(
            'mkdir -p {}; mount {} {}'.format(mount_on, partition, mount_on),
            fail_ok=False)
        LOG.info("{} successfully mounted to {}".format(partition, mount_on))
        mount_on_, fs_type_ = get_fs_mount_path(ssh_client=ssh_client,
                                                fs=partition)
        assert mount_on == mount_on_ and fs_type == fs_type_

    return mount_on, fs_type


def turn_on_swap(ssh_client, disk, partition=None):
    if not partition:
        partition = '/dev/{}'.format(disk)
    swap_info = ssh_client.exec_sudo_cmd(
        'blkid | grep --color=never "{}:"'.format(partition), fail_ok=False)[1]
    swap_uuid = re.findall('UUID="(.*)" TYPE="swap"', swap_info)[0]
    LOG.info('swapon for {}'.format(partition))
    proc_swap = ssh_client.exec_sudo_cmd(
        'cat /proc/swaps | grep --color=never "{} "'.format(partition))[1]
    if not proc_swap:
        ssh_client.exec_sudo_cmd('swapon {}'.format(partition))
        proc_swap = ssh_client.exec_sudo_cmd(
            'cat /proc/swaps | grep --color=never "{} "'.format(partition))[1]
        assert proc_swap, "swap partition is not shown in /proc/swaps after " \
                          "swapon"

    return swap_uuid


def auto_mount_fs(ssh_client, fs, mount_on=None, fs_type=None,
                  check_first=True):
    if check_first:
        if is_fs_auto_mounted(ssh_client=ssh_client, fs=fs):
            return

    if fs_type == 'swap' and not mount_on:
        raise ValueError("swap uuid required via mount_on")

    if not mount_on:
        mount_on = '/mnt/{}'.format(fs.rsplit('/', maxsplit=1)[-1])

    if not fs_type:
        fs_type = 'ext4'
    cmd = 'echo "{} {} {}  defaults 0 0" >> /etc/fstab'.format(fs, mount_on,
                                                               fs_type)
    ssh_client.exec_sudo_cmd(cmd, fail_ok=False)
    ssh_client.exec_sudo_cmd('cat /etc/fstab', get_exit_code=False)


def modify_swift(enable=True, check_first=True, fail_ok=False, apply=True,
                 con_ssh=None):
    """
    Enable/disable swift service
    Args:
        enable:
        check_first:
        fail_ok:
        apply:
        con_ssh

    Returns (tuple):
        (-1, "swift service parameter is already xxx")      only apply when
        check_first=True
        (0, <success_msg>)
        (1, <std_err>)      system service-parameter-modify cli got rejected.

    """
    if enable:
        expt_val = 'true'
        extra_str = 'enable'
    else:
        expt_val = 'false'
        extra_str = 'disable'

    if check_first:
        swift_endpoints = keystone_helper.get_endpoints(service_name='swift',
                                                        con_ssh=con_ssh,
                                                        cli_filter=False)
        if enable is bool(swift_endpoints):
            msg = "swift service parameter is already {}d. Do nothing.".format(
                extra_str)
            LOG.info(msg)
            return -1, msg

    LOG.info("Modify system service parameter to {} Swift".format(extra_str))
    code, msg = system_helper.modify_service_parameter(service='swift',
                                                       section='config',
                                                       name='service_enabled',
                                                       value=expt_val,
                                                       apply=apply,
                                                       check_first=False,
                                                       fail_ok=fail_ok,
                                                       con_ssh=con_ssh)

    if apply and code == 0:
        LOG.info("Check Swift endpoints after service {}d".format(extra_str))
        swift_endpoints = keystone_helper.get_endpoints(service_name='swift',
                                                        con_ssh=con_ssh,
                                                        cli_filter=False)
        if enable is not bool(swift_endpoints):
            raise exceptions.SwiftError(
                "Swift endpoints did not {} after modify".format(extra_str))
        msg = 'Swift is {}d successfully'.format(extra_str)

    return code, msg


def get_qemu_image_info(image_filename, ssh_client, fail_ok=False):
    """
    Provides information about the disk image filename, like file format,
    virtual size and disk size
    Args:
        image_filename (str); the disk image file name
        ssh_client:
        fail_ok:

    Returns:
        0, dict { image: <image name>, format: <format>, virtual size:
        <size>, disk size: <size}
        1, error msg

    """
    img_info = {}
    cmd = 'qemu-img info {}'.format(image_filename)
    rc, output = ssh_client.exec_cmd(cmd, fail_ok=True)
    if rc == 0:
        lines = output.split('\n')
        for line in lines:
            key = line.split(':')[0].strip()
            value = line.split(':')[1].strip()
            img_info[key] = value

        return 0, img_info
    else:
        msg = "qemu-img info failed: {}".format(output)
        LOG.warning(msg)
        if fail_ok:
            return 1, msg
        else:
            raise exceptions.CommonError(msg)


def convert_image_format(src_image_filename, dest_image_filename, dest_format,
                         ssh_client, source_format=None,
                         fail_ok=False):
    """
    Converts the src_image_filename to  dest_image_filename using format
    dest_format
    Args:
       src_image_filename (str):  the source disk image filename to be converted
       dest_image_filename (str): the destination disk image filename
       dest_format (str): image format to convert to. Valid formats are:
       qcow2, qed, raw, vdi, vpc, vmdk
       source_format(str): optional - source image file format
       ssh_client:
       fail_ok:

    Returns:

    """

    args_ = ''
    if source_format:
        args_ = ' -f {}'.format(source_format)

    cmd = 'qemu-img convert {} {} {}'.format(args_, src_image_filename,
                                             dest_image_filename)
    rc, output = ssh_client.exec_cmd(cmd, fail_ok=True)
    if rc == 0:
        return 0, "Disk image {} converted to {} format successfully".format(
            dest_image_filename, dest_format)
    else:
        msg = "qemu-img convert failed: {}".format(output)
        LOG.warning(msg)
        if fail_ok:
            return 1, msg
        else:
            raise exceptions.CommonError(msg)


def check_controllerfs(**kwargs):
    """
    This validates that the underlying controller filesystem aligns with the
    expected values.

    Arguments:
    - kwargs - dict of name:value pair(s)
    """

    con_ssh = ControllerClient.get_active_controller()

    for fs in kwargs:
        if fs == "database":
            fs_name = "pgsql-lv"
            expected_size = int(kwargs[fs]) * 2
        elif fs == "glance":
            fs_name = "cgcs-lv"
            expected_size = int(kwargs[fs])
        else:
            fs_name = fs + "-lv"
            expected_size = int(kwargs[fs])

        cmd = "lvs --units g --noheadings -o lv_size -S lv_name={}".format(
            fs_name)
        rc, out = con_ssh.exec_sudo_cmd(cmd)

        actual_size = re.match(r'[\d]+', out.lstrip())
        assert actual_size, "Unable to determine actual filesystem size"
        assert int(actual_size.group(0)) == expected_size, \
            "{} should be {} but was {}".format(fs, expected_size, actual_size)


def get_storage_monitors_count():
    # Only 2 storage monitor available. At least 2 unlocked and enabled hosts
    # with monitors are required.
    # Please ensure hosts with monitors are unlocked and enabled -
    # candidates: controller-0, controller-1,
    raise NotImplementedError


def create_storage_profile(host, profile_name='', con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    """
    Create a storage profile

    Args:
        host (str): hostname or id
        profile_name (str): name of the profile to create
        con_ssh (SSHClient):
        auth_info

    Returns (str): uuid of the profile created if success, '' otherwise

    """
    if not profile_name:
        profile_name = time.strftime('storprof_%Y%m%d_%H%M%S_',
                                     time.localtime())

    cmd = 'storprofile-add {} {}'.format(profile_name, host)

    table_ = table_parser.table(
        cli.system(cmd, ssh_client=con_ssh, fail_ok=False, auth_info=auth_info)[
            1])
    uuid = table_parser.get_value_two_col_table(table_, 'uuid')

    return uuid


def delete_storage_profile(profile='', con_ssh=None,
                           auth_info=Tenant.get('admin_platform')):
    """
    Delete a storage profile

    Args:
        profile (str): name of the profile to create
        con_ssh (SSHClient):
        auth_info

    Returns (): no return if success, will raise exception otherwise

    """
    if not profile:
        raise ValueError(
            'Name or uuid must be provided to delete the storage-profile')

    cmd = 'storprofile-delete {}'.format(profile)

    cli.system(cmd, ssh_client=con_ssh, fail_ok=False, auth_info=auth_info)


def get_host_partitions(host, state=None, disk=None, field='uuid', con_ssh=None,
                        auth_info=Tenant.get('admin_platform')):
    """
    Return partitions based on their state.

    Arguments:
        host(str|list|tuple) - list of host names
        state(str|None) - partition state, i.e. Creating, Ready, In-use,
        Deleting,
        disk (str|None)
        field (str|list|tuple)
        con_ssh
        auth_info

    Return (list):

    """
    args = '--disk {} {}'.format(disk, host) if disk else host
    table_ = table_parser.table(
        cli.system('host-disk-partition-list --nowrap', args,
                   ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    kwargs = {'state': state} if state else {}
    values = table_parser.get_multi_values(table_, field, **kwargs)

    return values


def get_host_partition_values(host, uuid, fields, con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    """
    Return requested information about a partition on a given host.

    Args:
        host(str) - hostname, e.g. controller-0
        uuid(str) - uuid of partition
        fields(str|list|tuple) - the parameter wanted, e.g. size_gib
        con_ssh
        auth_info

    Returns:
    * param_value(list) - the value of the desired parameter
    """

    args = "{} {}".format(host, uuid)
    rc, out = cli.system('host-disk-partition-show', args, fail_ok=True,
                         ssh_client=con_ssh, auth_info=auth_info)
    if rc > 0:
        return None

    table_ = table_parser.table(out)
    values = []
    for field in fields:
        convert_to_gib = False
        if field == 'size_gib':
            field = 'size_mib'
            convert_to_gib = True

        param_value = table_parser.get_value_two_col_table(table_, field)
        if '_mib' in field:
            param_value = float(param_value)
        if convert_to_gib:
            param_value = float(param_value) / 1024

        values.append(param_value)

    return values


def delete_host_partition(host, uuid, fail_ok=False,
                          timeout=SysInvTimeout.PARTITION_DELETE, con_ssh=None,
                          auth_info=Tenant.get('admin_platform')):
    """
    Delete a partition from a specific host.

    Arguments:
    * host(str) - hostname, e.g. controller-0
    * uuid(str) - uuid of partition
    * timeout(int) - how long to wait for partition deletion (sec)

    Returns:
    * rc, out - return code and output of the host-disk-partition-delete
    """

    rc, out = cli.system('host-disk-partition-delete {} {}'.format(host, uuid),
                         fail_ok=fail_ok, ssh_client=con_ssh,
                         auth_info=auth_info)
    if rc > 0:
        return 1, out

    wait_for_host_partition_status(host=host, uuid=uuid, timeout=timeout,
                                   final_status=None,
                                   interim_status=PartitionStatus.DELETING,
                                   con_ssh=con_ssh, auth_info=auth_info)
    return 0, "Partition successfully deleted"


def create_host_partition(host, device_node, size_gib, fail_ok=False, wait=True,
                          timeout=SysInvTimeout.PARTITION_CREATE,
                          con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Create a partition on host.

    Arguments:
    * host(str) - hostname, e.g. controller-0
    * device_node(str) - device, e.g. /dev/sdh
    * size_gib(str) - size of partition in gib
    * wait(bool) - if True, wait for partition creation.  False, return
    * immediately.
    * timeout(int) - how long to wait for partition creation (sec)

    Returns:
    * rc, out - return code and output of the host-disk-partition-command
    """
    args = '{} {} {}'.format(host, device_node, size_gib)
    rc, out = cli.system('host-disk-partition-add', args, fail_ok=fail_ok,
                         ssh_client=con_ssh, auth_info=auth_info)
    if rc > 0 or not wait:
        return rc, out

    uuid = table_parser.get_value_two_col_table(table_parser.table(out), "uuid")
    wait_for_host_partition_status(host=host, uuid=uuid, timeout=timeout,
                                   con_ssh=con_ssh, auth_info=auth_info)
    return 0, uuid


def modify_host_partition(host, uuid, size_gib, fail_ok=False,
                          timeout=SysInvTimeout.PARTITION_MODIFY,
                          final_status=PartitionStatus.READY, con_ssh=None,
                          auth_info=Tenant.get('admin_platform')):
    """
    This test modifies the size of a partition.

    Args:
        host(str) - hostname, e.g. controller-0
        uuid(str) - uuid of the partition
        size_gib(str) - new partition size in gib
        fail_ok
        timeout(int) - how long to wait for partition creation (sec)
        final_status (str|list)
        con_ssh
        auth_info

    Returns:
    * rc, out - return code and output of the host-disk-partition-command
    """

    args = '-s {} {} {}'.format(size_gib, host, uuid)
    rc, out = cli.system('host-disk-partition-modify', args, fail_ok=fail_ok,
                         ssh_client=con_ssh, auth_info=auth_info)
    if rc > 0:
        return 1, out

    uuid = table_parser.get_value_two_col_table(table_parser.table(out), "uuid")
    wait_for_host_partition_status(host=host, uuid=uuid, timeout=timeout,
                                   interim_status=PartitionStatus.MODIFYING,
                                   final_status=final_status, con_ssh=con_ssh,
                                   auth_info=auth_info)

    msg = "{} partition successfully modified".format(host)
    LOG.info(msg)
    return 0, msg


def wait_for_host_partition_status(host, uuid,
                                   final_status=PartitionStatus.READY,
                                   interim_status=PartitionStatus.CREATING,
                                   timeout=120, fail_ok=False,
                                   con_ssh=None,
                                   auth_info=Tenant.get('admin_platform')):
    """
    Wait for host partition to reach given status
    Args:
        host:
        uuid:
        final_status (str|list|None|tuple):
        interim_status:
        timeout:
        fail_ok:
        con_ssh
        auth_info

    Returns (bool):

    """
    if not final_status:
        final_status = [None]
    elif isinstance(final_status, str):
        final_status = (final_status,)

    valid_status = list(final_status)
    if isinstance(interim_status, str):
        interim_status = (interim_status,)
    for status_ in interim_status:
        valid_status.append(status_)

    end_time = time.time() + timeout
    prev_status = ''
    while time.time() < end_time:
        status = \
            get_host_partition_values(host, uuid, "status", con_ssh=con_ssh,
                                      auth_info=auth_info)[0]
        assert status in valid_status, "Partition has unexpected state " \
                                       "{}".format(status)

        if status in final_status:
            LOG.info(
                "Partition {} on host {} has reached state: {}".format(uuid,
                                                                       host,
                                                                       status))
            return True
        elif status != prev_status:
            prev_status = status
            LOG.info("Partition {} on host {} is in {} state".format(uuid, host,
                                                                     status))

        time.sleep(5)

    msg = "Partition {} on host {} not in {} state within {} seconds".format(
        uuid, host, final_status, timeout)
    LOG.warning(msg)
    if fail_ok:
        return False
    else:
        raise exceptions.StorageError(msg)


def get_host_disks(host, field='uuid', auth_info=Tenant.get('admin_platform'),
                   con_ssh=None, **kwargs):
    """
    Get values from system host-disk-list
    Args:
        host (str):
        field (str|list|tuple)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (dict):

    """
    table_ = table_parser.table(
        cli.system('host-disk-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, evaluate=True, **kwargs)


def get_host_disk_values(host, disk, fields,
                         auth_info=Tenant.get('admin_platform'), con_ssh=None):
    """
    Get host disk values via system host-disk-show
    Args:
        host:
        disk:
        fields:
        auth_info:
        con_ssh:

    Returns:

    """
    table_ = table_parser.table(
        cli.system('host-disk-show', '{} {}'.format(host, disk),
                   ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       evaluate=True)


def get_host_disks_with_free_space(host, disk_list,
                                   auth_info=Tenant.get('admin_platform'),
                                   con_ssh=None):
    """
    Given a list of disks, return the ones with free space.

    Arguments:
        host(str) - hostname, e.g. ocntroller-0
        disk_list (list) - list of disks
        auth_info
        con_ssh

    Returns (dict): disks that have usable space.
    """

    free_disks = {}
    for disk in disk_list:
        LOG.info("Querying disk {} on host {}".format(disk, host))
        available_space = float(
            get_host_disk_values(host, disk, fields='available_gib',
                                 auth_info=auth_info,
                                 con_ssh=con_ssh)[0])
        LOG.info("{} has disk {} with {} gib available".format(host, disk,
                                                               available_space))
        if available_space <= 0:
            LOG.info(
                "Removing disk {} from host {} due to insufficient "
                "space".format(
                    disk, host))
        else:
            free_disks[disk] = available_space

    return free_disks


def get_hosts_rootfs(hosts, auth_info=Tenant.get('admin_platform'),
                     con_ssh=None):
    """
    This returns the rootfs disks of each node.

    Arguments:
    * hosts(list) - e.g. controller-0, controller-1, etc.

    Returns:
    * Dict of host mapped to rootfs disk
    """

    rootfs_uuid = {}
    for host in hosts:
        rootfs_device = system_helper.get_host_values(host, 'rootfs_device',
                                                      auth_info=auth_info,
                                                      con_ssh=con_ssh)[0]
        LOG.debug("{} is using rootfs disk: {}".format(host, rootfs_device))
        key = 'device_path'
        if '/dev/disk' not in rootfs_device:
            key = 'device_node'
            rootfs_device = '/dev/{}'.format(rootfs_device)

        disk_uuids = get_host_disks(host, 'uuid', auth_info=auth_info,
                                    con_ssh=con_ssh, **{key: rootfs_device})
        rootfs_uuid[host] = disk_uuids

    LOG.info("Root disk UUIDS: {}".format(rootfs_uuid))
    return rootfs_uuid


def get_controllerfs_list(field='Size in GiB', fs_name=None, con_ssh=None,
                          auth_info=Tenant.get('admin_platform'),
                          **filters):
    table_ = table_parser.table(
        cli.system('controllerfs-list --nowrap', ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    if fs_name:
        filters['FS Name'] = fs_name

    return table_parser.get_multi_values(table_, field, evaluate=True,
                                         **filters)


def get_controllerfs_values(filesystem, fields='size', rtn_dict=False,
                            auth_info=Tenant.get('admin_platform'),
                            con_ssh=None):
    """
    Returns the value of a particular filesystem.

    Arguments:
    - fields (str|list|tuple) - what value to get, e.g. size
    - filesystem(str) - e.g. scratch, database, etc.

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('controllerfs-show', filesystem, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       rtn_dict=rtn_dict,
                                                       evaluate=True)


def get_controller_fs_values(con_ssh=None,
                             auth_info=Tenant.get('admin_platform')):
    table_ = table_parser.table(
        cli.system('controllerfs-show', ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    rows = table_parser.get_all_rows(table_)
    values = {}
    for row in rows:
        values[row[0].strip()] = row[1].strip()
    return values


def modify_controllerfs(fail_ok=False, auth_info=Tenant.get('admin_platform'),
                        con_ssh=None, **kwargs):
    """
    Modifies the specified controller filesystem, e.g. scratch, database, etc.

    Arguments:
    - kwargs - dict of name:value pair(s)
    - fail_ok(bool) - True if failure is expected.  False if not.
    """

    attr_values_ = ['{}="{}"'.format(attr, value) for attr, value in
                    kwargs.items()]
    args_ = ' '.join(attr_values_)

    rc, out = cli.system("controllerfs-modify", args_, fail_ok=fail_ok,
                         ssh_client=con_ssh, auth_info=auth_info)
    if rc > 0:
        return 1, out

    msg = "Filesystem update succeeded"
    LOG.info(msg)
    return 0, msg


def get_host_stors(host, field='uuid', con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get host storage values from system host-stor-list
    Args:
        host:
        field (str|tuple|list):
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('host-stor-list --nowrap', host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values(table_, field, evaluate=True)


def get_host_stor_values(host, stor_uuid, fields="size", con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Returns the value of a particular filesystem.

    Arguments:
        host
        stor_uuid
        fields (str|list|tuple)
        auth_info
        con_ssh

    Returns (list):

    """
    args = '{} {}'.format(host, stor_uuid)
    table_ = table_parser.table(
        cli.system('host-stor-show', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
    return table_parser.get_multi_values_two_col_table(table_, fields,
                                                       evaluate=True)


def get_storage_tiers(cluster, field='uuid', con_ssh=None,
                      auth_info=Tenant.get('admin_platform'), **filters):
    """

    Args:
        cluster:
        field (str|tuple|list):
        con_ssh:
        auth_info:
        **filters:

    Returns:

    """
    table_ = table_parser.table(
        cli.system('storage-tier-list {}'.format(cluster), ssh_client=con_ssh,
                   auth_info=auth_info), combine_multiline_entry=True)
    return table_parser.get_multi_values(table_, field, **filters)


def add_host_storage(host, disk_uuid, journal_location=None, journal_size=None,
                     function=None, tier_uuid=None,
                     auth_info=Tenant.get('admin_platform'), con_ssh=None,
                     fail_ok=False):
    """
    Add storage to host
    Args:
        host:
        disk_uuid:
        journal_location:
        journal_size:
        function:
        tier_uuid:
        auth_info:
        con_ssh:
        fail_ok:

    Returns (tuple):

    """
    if not host or not disk_uuid:
        raise ValueError("host name and disk uuid must be specified")

    args_dict = {
        '--journal-location': journal_location,
        '--journal-size': journal_size,
        '--tier-uuid': tier_uuid
    }
    args = common.parse_args(args_dict)

    function = ' {}'.format(function) if function else ''
    args += " {} {}{}".format(host, function, disk_uuid)
    LOG.info("Adding storage to {}".format(host))
    rc, output = cli.system('host-stor-add', ssh_client=con_ssh,
                            fail_ok=fail_ok, auth_info=auth_info)
    if rc > 0:
        return 1, output

    table_ = table_parser.table(output)
    uuid = table_parser.get_value_two_col_table(table_, 'uuid')
    LOG.info("Storage added to {} successfully: {}".format(host, uuid))
    return 0, uuid


def clear_local_storage_cache(host, con_ssh=None):
    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        with host_ssh.login_as_root() as root_ssh:
            root_ssh.exec_cmd('rm -rf /var/lib/nova/instances/_base/*',
                              fail_ok=True)
            root_ssh.exec_cmd('sync;echo 3 > /proc/sys/vm/drop_caches',
                              fail_ok=True)
