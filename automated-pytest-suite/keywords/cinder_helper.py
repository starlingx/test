#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import re
import os
import random
import time
import math

from consts.auth import Tenant
from consts.stx import GuestImages, Prompt
from consts.timeout import VolumeTimeout
from keywords import common, glance_helper
from testfixtures.fixture_resources import ResourceCleanup
from utils import table_parser, cli, exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG


def get_any_volume(status='available', bootable=True, auth_info=None,
                   con_ssh=None, new_name=None, cleanup=None):
    """
    Get an id of any volume that meets the criteria. Create one if none exists.

    Args:
        status (str):
        bootable (str|bool):
        auth_info (dict):
        con_ssh (SSHClient):
        new_name (str): This is only used if no existing volume found and new
        volume needs to be created
        cleanup (str|None)

    Returns:
        str: volume id

    """
    volumes = get_volumes(status=status, bootable=bootable, auth_info=auth_info,
                          con_ssh=con_ssh)
    if volumes:
        return 0, random.choice(volumes)
    else:
        return 1, create_volume(name=new_name, bootable=bootable,
                                auth_info=auth_info, con_ssh=con_ssh,
                                cleanup=cleanup)[1]


def get_volumes(vols=None, full_name=None, project=None, project_domain=None,
                user=None, user_domain=None, all_=True,
                long=True, name=None, name_strict=False, vol_type=None,
                size=None, status=None, attached_vm=None,
                bootable=None, field='ID', auth_info=Tenant.get('admin'),
                con_ssh=None):
    """
    Return a list of volume ids based on the given criteria

    Args:
        vols (list or str):
        full_name
        project
        project_domain
        user
        user_domain
        all_ (bool)
        long (bool)
        name (str): post execution table filters
        name_strict (bool):
        vol_type (str):
        size (str):
        status:(str|list|tuple)
        attached_vm (str):
        bootable (str|bool): true or false
        field (str)
        auth_info (dict): could be Tenant.get('admin'),Tenant.get('tenant1'),
        Tenant.get('tenant2')
        con_ssh (str):

    Returns (list): a list of volume ids based on the given criteria
    """
    args_dict = {
        '--long': long,
        '--a': all_,
        '--name': full_name,
        '--project': project,
        '--project-domain': project_domain,
        '--user': user,
        '--user-domain': user_domain,
    }
    args = common.parse_args(args_dict)
    table_ = table_parser.table(
        cli.openstack('volume list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    if name is not None:
        table_ = table_parser.filter_table(table_, strict=name_strict,
                                           **{'Name': name})
    if bootable is not None:
        bootable = str(bootable).lower()
    filters = {
        'ID': vols,
        'Type': vol_type,
        'Size': size,
        'Attached to': attached_vm,
        'Status': status,
        'Bootable': bootable
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    if filters:
        table_ = table_parser.filter_table(table_, **filters)

    return table_parser.get_column(table_, field)


def get_volume_snapshot_values(vol_snapshot, fields, strict=True, con_ssh=None,
                               auth_info=None):
    """
    Get volume snapshot values for given fields via openstack volume snapshot
    show
    Args:
        vol_snapshot (str):
        fields (list|str|tuple):
        strict (bool):
        con_ssh:
        auth_info:

    Returns (list): values for given fields

    """

    if isinstance(fields, str):
        fields = [fields]

    table_ = table_parser.table(
        cli.openstack('volume snapshot show', vol_snapshot, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    vals = []
    for field in fields:
        vals.append(
            table_parser.get_value_two_col_table(table_, field, strict=strict))

    return vals


def get_volume_snapshot_list(vol_snaps=None, name=None, name_strict=False,
                             size=None, status=None, volume=None,
                             field='ID', auth_info=Tenant.get('admin'),
                             con_ssh=None):
    """
    Return a list of volume ids based on the given criteria

    Args:
        vol_snaps (list or str):
        name (str):
        name_strict (bool):
        size (str):
        status:(str)
        volume (str):
        field
        auth_info (dict): could be Tenant.get('admin'),Tenant.get('tenant1'),
        Tenant.get('tenant2')
        con_ssh (str):

    Returns (list): a list of volume snapshot ids based on the given criteria

    """
    optional_args = {
        'ID': vol_snaps,
        'Size': size,
        'Status': status,
        'Volume': volume,
    }

    criteria = {}
    for key, value in optional_args.items():
        if value is not None:
            criteria[key] = value

    table_ = table_parser.table(
        cli.openstack('volume snapshot list --a --long', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    if name:
        table_ = table_parser.filter_table(table_, strict=name_strict,
                                           **{'Name': name})

    return table_parser.get_values(table_, field, **criteria)


def get_volumes_attached_to_vms(volumes=None, vms=None, header='ID',
                                con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Filter out the volumes that are attached to a vm.
    Args:
        volumes (list or str): list of volumes ids to filter out from. When
        None, filter from all volumes
        vms (list or str): get volumes attached to given vm(s). When None,
        filter volumes attached to any vm
        header (str): header of the column in the table to return
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (list): a list of values from the column specified or [] if no
    match found

    """
    table_ = table_parser.table(
        cli.openstack('volume list --a', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    # Filter from given volumes if provided
    if volumes is not None:
        table_ = table_parser.filter_table(table_, ID=volumes)

    # Filter from given vms if provided
    if vms:
        table_ = table_parser.filter_table(table_, strict=False,
                                           **{'Attached to': vms})
    # Otherwise filter out volumes attached to any vm
    else:
        table_ = table_parser.filter_table(table_, strict=False, regex=True,
                                           **{'Attached to': r'.*\S.*'})

    return table_parser.get_column(table_, header)


def create_volume(name=None, description=None, source_type='image',
                  source_id=None, vol_type=None, size=None,
                  avail_zone=None, properties=None, hints=None,
                  multi_attach=None, bootable=True, read_only=None,
                  consistency_group=None, fail_ok=False, auth_info=None,
                  con_ssh=None,
                  avail_timeout=VolumeTimeout.STATUS_CHANGE, guest_image=None,
                  cleanup=None):
    """
    Create a volume with given criteria.

    Args:
        name (str|None): display name of the volume
        description (str|None): description of the volume
        source_type (str|None): image, snapshot, volume, or None.
        source_id (str|None): source volume id to create volume from
        vol_type (str|None): volume type such as 'raw'
        size (int|None): volume size in GBs
        avail_zone (str|None): availability zone
        properties (str|list|tuple|dict|None): metadata key and value pairs
            '[<key=value> [<key=value> ...]]'
        bootable (bool|None): When False, the source id params will be
            ignored and non-bootable volume will be created
        read_only (bool|None)
        hints (str|list|tuple|dict|None)
        multi_attach
        consistency_group (str|None)
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):
        guest_image (str): guest image name if image_id unspecified. valid
            values: cgcs-guest, ubuntu, centos_7, etc
        avail_timeout (int)
        cleanup (None|str): teardown level

    Returns (tuple):  (return_code, volume_id or err msg)
        (-1, existing_vol_id)   # returns existing volume_id instead of
        creating a new one. Applies when rtn_exist=True.
        (0, vol_id)     # Volume created successfully and in available state.
        (1, <stderr>)   # Create volume cli rejected with sterr
        (2, vol_id)   # volume created, but not in available state.
        (3, vol_id]: if volume created, but not in given bootable state.

    Notes:
        snapshot_id > source_vol_id > image_id if more than one source ids
        are provided.
    """
    valid_cleanups = ('module', 'session', 'function', 'class', None)
    if cleanup not in valid_cleanups:
        raise ValueError(
            "Invalid scope provided. Choose from: {}".format(valid_cleanups))

    valid_source_types = (None, 'image', 'volume', 'source', 'snapshot')
    if source_type not in valid_source_types:
        raise ValueError(
            "Invalid source type specified. Choose from: {}".format(
                valid_source_types))

    if source_type and not source_id:
        if source_type != 'image':
            raise ValueError(
                "source_id has to be provided for {}".format(source_type))

        # Get glance image id as source_id based on guest_image value
        guest_image = guest_image if guest_image else GuestImages.DEFAULT[
            'guest']
        source_id = glance_helper.get_image_id_from_name(guest_image,
                                                         strict=True,
                                                         auth_info=auth_info,
                                                         con_ssh=con_ssh)
        if size is None:
            size = GuestImages.IMAGE_FILES[guest_image][1]

    if size is None:
        # size is required if source_type is not volume or snapshot
        if not source_type:
            size = 2
        elif source_type == 'image':
            if guest_image:
                size = GuestImages.IMAGE_FILES[guest_image][1]
            else:
                # check glance image size via openstack image show to
                # determine the volume size
                image_size = glance_helper.get_image_values(source_id, 'size',
                                                            auth_info=auth_info,
                                                            con_ssh=con_ssh)[0]
                size = max(2, math.ceil(image_size / math.pow(1024, 3)))

    if not name:
        if not auth_info:
            auth_info = Tenant.get_primary()
        name = 'vol-{}'.format(auth_info['tenant'])
    existing_volumes = get_volumes(field='Name', auth_info=auth_info,
                                   con_ssh=con_ssh)
    name = common.get_unique_name(name, resource_type='volume',
                                  existing_names=existing_volumes)

    optional_args = {'--size': size,
                     '--description': description,
                     '--type': vol_type,
                     '--availability-zone': avail_zone,
                     '--consistency-group': consistency_group,
                     '--property': properties,
                     '--hint': hints,
                     '--multi-attach': multi_attach,
                     '--bootable': True if bootable else None,
                     '--non-bootable': True if bootable is False else None,
                     '--read-only': True if read_only else None,
                     '--read-write': True if read_only is False else None,
                     }
    if source_type:
        source_type = 'source' if 'volume' in source_type else source_type
        optional_args['--{}'.format(source_type)] = source_id

    args = '{} {}'.format(common.parse_args(optional_args, repeat_arg=True),
                          name)
    LOG.info("Creating Volume with args: {}".format(args))
    exit_code, cmd_output = cli.openstack('volume create', args,
                                          ssh_client=con_ssh, fail_ok=fail_ok,
                                          auth_info=auth_info)

    table_ = table_parser.table(cmd_output)
    volume_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup and volume_id:
        ResourceCleanup.add('volume', volume_id, scope=cleanup)

    if exit_code > 0:
        return 1, cmd_output

    LOG.info("Post action check started for create volume.")
    if not wait_for_volume_status(volume=volume_id, status='available',
                                  auth_info=auth_info, fail_ok=fail_ok,
                                  timeout=avail_timeout):
        LOG.warning(
            "Volume {} did not reach available state within {}s after "
            "creation".format(
                name, avail_timeout))
        return 2, volume_id

    LOG.info("Volume is created and in available state: {}".format(volume_id))
    return 0, volume_id


def get_volume_show_values(volume, fields, con_ssh=None,
                           auth_info=Tenant.get('admin')):
    """
    Get values for given cinder volume via openstack volume show
    Args:
        volume:
        fields (str|tuple|list):
        con_ssh:
        auth_info:

    Returns (list):

    """
    if not volume:
        raise ValueError("Volume is not provided.")

    if isinstance(fields, str):
        fields = (fields,)

    table_ = table_parser.table(
        cli.openstack('volume show', volume, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    vals = []
    for field in fields:
        field = field.lower()
        val = table_parser.get_value_two_col_table(table_, field=field,
                                                   merge_lines=True)
        if field == 'properties':
            val = table_parser.convert_value_to_dict(val)
        elif val and (field in ('attachments', 'volume_image_metadata') or
                      val.lower() in ('true', 'false', 'none')):
            try:
                LOG.info('val: {}'.format(val))
                val = eval(
                    val.replace('true', 'True').replace('none', 'None').replace(
                        'false', 'False'))
            except (NameError, SyntaxError):
                pass
        vals.append(val)

    return vals


def wait_for_volume_status(volume, status='available',
                           timeout=VolumeTimeout.STATUS_CHANGE, fail_ok=True,
                           check_interval=5, con_ssh=None, auth_info=None):
    """

    Args:
        volume (str):
        status (str/list):
        timeout (int):
        fail_ok (bool):
        check_interval (int):
        con_ssh (str):
        auth_info (dict):

    Returns:
        True if the status of the volume is same as the status(str) that was
        passed into the function \n
        false if timed out or otherwise

    """
    return __wait_for_vol_status(volume, is_snapshot=False, status=status,
                                 timeout=timeout, fail_ok=fail_ok,
                                 check_interval=check_interval, con_ssh=con_ssh,
                                 auth_info=auth_info)


def wait_for_vol_snapshot_status(vol_snapshot, status='available',
                                 timeout=VolumeTimeout.STATUS_CHANGE,
                                 fail_ok=False,
                                 check_interval=5, con_ssh=None,
                                 auth_info=None):
    """
    Wait for cinder volume or volume snapshot to reach given state
    Args:
        vol_snapshot (str):
        status (str/list):
        timeout (int):
        fail_ok (bool):
        check_interval (int):
        con_ssh (str):
        auth_info (dict):

    Returns:
        True if the status of the volume is same as the status(str) that was
        passed into the function \n
        false if timed out or otherwise

    """
    return __wait_for_vol_status(vol_snapshot, is_snapshot=True, status=status,
                                 timeout=timeout,
                                 fail_ok=fail_ok, check_interval=check_interval,
                                 con_ssh=con_ssh, auth_info=auth_info)


def __wait_for_vol_status(volume, is_snapshot=False, status='available',
                          timeout=VolumeTimeout.STATUS_CHANGE,
                          fail_ok=False, check_interval=5, con_ssh=None,
                          auth_info=None):
    if isinstance(status, str):
        status = (status,)

    vol_str = 'snapshot ' if is_snapshot else ''
    LOG.info("Waiting for cinder volume {}{} status: {}".format(vol_str, volume,
                                                                status))
    end_time = time.time() + timeout
    current_status = prev_status = None

    func = get_volume_snapshot_values if is_snapshot else get_volume_show_values

    while time.time() < end_time:
        current_status = func(
            volume, fields='status', con_ssh=con_ssh, auth_info=auth_info)[0]
        if current_status in status:
            LOG.info("Volume {}{} is in {} state".format(vol_str, volume,
                                                         current_status))
            return True
        elif current_status == 'error':
            msg = 'Volume {}{} is in error status'.format(vol_str, volume)
            LOG.warning(msg)
            if fail_ok:
                return False
            raise exceptions.VolumeError(msg)
        elif current_status != prev_status:
            LOG.info("Volume {}status is: {}".format(vol_str, current_status))
            prev_status = current_status

        time.sleep(check_interval)
    else:
        msg = "Timed out waiting for volume {}{} status to reach status: {}. " \
              "Actual status: {}". \
            format(vol_str, volume, status, current_status)
        LOG.warning(msg)
        if fail_ok:
            return False
        raise exceptions.TimeoutException(msg)


def get_vol_snapshots(status='available', volume=None, vol_id=None, name=None,
                      size=None, field='ID',
                      con_ssh=None, auth_info=None):
    """
    Get one volume snapshot id that matches the given criteria.

    Args:
        status (str): snapshot status. e.g., 'available', 'in use'
        volume (str): Name of the volume the snapshot created from
        vol_id (str): volume id the snapshot was created from
        name (str): snapshot name
        size (int):
        field (str)
        con_ssh (SSHClient):
        auth_info (dict):

    Returns:
        A string of snapshot id. Return None if no matching snapshot found.

    """
    table_ = table_parser.table(
        cli.openstack('snapshot list', ssh_client=con_ssh, auth_info=auth_info)[
            1])
    if size is not None:
        size = str(size)

    if vol_id and not volume:
        volume = get_volumes(vols=vol_id, field='Name')[0]

    possible_args = {
        'status': status,
        "Volume": volume,
        'Status': status,
        'name': name,
        'Size': size
    }

    args_ = {}
    for key, val in possible_args.items():
        if val:
            args_[key] = val

    return table_parser.get_values(table_, field, **args_)


def _wait_for_volumes_deleted(volumes, timeout=VolumeTimeout.DELETE,
                              fail_ok=True,
                              check_interval=3, con_ssh=None,
                              auth_info=Tenant.get('admin')):
    """
        check if a specific field still exist in a specified column for
        cinder list

    Args:
        volumes(list or str): ids of volumes
        timeout (int):
        fail_ok (bool):
        check_interval (int):
        con_ssh:
        auth_info (dict):

    Returns (tuple):    (result(boot), volumes_deleted(list))

    """
    if isinstance(volumes, str):
        volumes = [volumes]

    vols_to_check = list(volumes)
    end_time = time.time() + timeout
    while time.time() < end_time:
        existing_vols = get_volumes(long=False, auth_info=auth_info,
                                    con_ssh=con_ssh)
        vols_to_check = list(set(existing_vols) & set(vols_to_check))
        if not vols_to_check:
            return True, list(volumes)

        time.sleep(check_interval)
    else:
        if fail_ok:
            return False, list(set(volumes) - set(vols_to_check))
        raise exceptions.TimeoutException(
            "Timed out waiting for volume(s) to be removed from openstack "
            "volume list: "
            "{}.".format(vols_to_check))


def delete_volumes(volumes=None, fail_ok=False, timeout=VolumeTimeout.DELETE,
                   check_first=True, con_ssh=None,
                   auth_info=Tenant.get('admin')):
    """
    Delete volume(s).

    Args:
        volumes (list|str): ids of the volumes to delete. If None,
        all available volumes under given Tenant will be
            deleted. If given Tenant is admin, available volumes for all
            tenants will be deleted.
        fail_ok (bool): True or False
        timeout (int): CLI timeout and waiting for volumes disappear timeout
        in seconds.
        check_first (bool): Whether to check volumes existence before attempt
        to delete
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): (rtn_code (int), msg (str))
        (-1, "No volume to delete. Do nothing.") # No volume given and no
        volume exists on system for given tenant
        (-1, ""None of the given volume(s) exist on system. Do nothing."")
        # None of the given volume(s) exists on
            system for given tenant
        (0, "Volume(s) deleted successfully")   # volume is successfully
        deleted.
        (1, <stderr>)   # Delete volume cli returns stderr
        (2, "Delete request(s) accepted but some volume(s) did not disappear
        within <timeout> seconds".)
        (3, "Delete request(s) rejected and post check failed for accepted
        request(s). \nCLI error: <stderr>"

    """
    if volumes is None:
        volumes = get_volumes(status=('available', 'error'),
                              auth_info=auth_info, con_ssh=con_ssh)

    LOG.info("Deleting volume(s): {}".format(volumes))

    if not volumes:
        msg = "No volume to delete. Do nothing."
        LOG.info(msg)
        return -1, msg

    if isinstance(volumes, str):
        volumes = [volumes]
    volumes = list(volumes)

    if check_first:
        vols_to_del = get_volumes(vols=volumes, auth_info=auth_info,
                                  con_ssh=con_ssh)
        if not vols_to_del:
            msg = "None of the given volume(s) exist on system. Do nothing."
            LOG.info(msg)
            return -1, msg

        if not vols_to_del == volumes:
            LOG.info(
                "Some volume(s) don't exist. Given volumes: {}. Volumes to "
                "delete: {}.".
                format(volumes, vols_to_del))
    else:
        vols_to_del = volumes

    vols_to_del_str = ' '.join(vols_to_del)

    LOG.debug("Volumes to delete: {}".format(vols_to_del))
    exit_code, cmd_output = cli.openstack('volume delete', vols_to_del_str,
                                          ssh_client=con_ssh, fail_ok=fail_ok,
                                          auth_info=auth_info, timeout=timeout)

    vols_to_check = []
    if exit_code == 1:
        for vol in vols_to_del:
            # if cinder delete on a specific volume ran successfully, then it
            # has no output regarding that vol
            if vol not in cmd_output:
                vols_to_check.append(vol)
    else:
        vols_to_check = vols_to_del

    LOG.info("Waiting for volumes to be removed from cinder list: {}".format(
        vols_to_check))
    all_deleted, vols_deleted = _wait_for_volumes_deleted(vols_to_check,
                                                          fail_ok=True,
                                                          con_ssh=con_ssh,
                                                          auth_info=auth_info,
                                                          timeout=timeout)

    if exit_code == 1:
        if all_deleted:
            if fail_ok:
                return 1, cmd_output
            raise exceptions.CLIRejected(cmd_output)
        else:
            msg = "Delete request(s) rejected and post check failed for " \
                  "accepted request(s). \nCLI error: {}". \
                format(cmd_output)
            if fail_ok:
                LOG.warning(msg)
                return 3, msg
            raise exceptions.VolumeError(msg)

    if not all_deleted:
        msg = "Delete request(s) accepted but some volume(s) did not " \
              "disappear within {} seconds".format(timeout)
        if fail_ok:
            LOG.warning(msg)
            return 2, msg
        raise exceptions.VolumeError(msg)

    LOG.info("Volume(s) are successfully deleted: {}".format(vols_to_check))
    return 0, "Volume(s) deleted successfully"


def delete_volume_snapshots(snapshots=None, force=False, check_first=True,
                            fail_ok=False, auth_info=Tenant.get('admin'),
                            con_ssh=None):
    """
    Delete given volume snapshot via cinder snapshot-delete

    Args:
        snapshots (str|list):
        force (bool):
        check_first (bool):
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple):
        (0, volume snapshot  <volume_snap_id> is successfully deleted)
        (1, <std_err>)
        (2, volume snapshot <volume_snap_id> still exists in cinder qos-list
        after deletion)

    """

    if not snapshots:
        snapshots_to_del = get_volume_snapshot_list(auth_info=auth_info)
    else:
        snapshots_to_del = [snapshots] if isinstance(snapshots, str) else list(
            snapshots)
        if check_first:
            snapshots_to_del = list(set(snapshots_to_del) & set(
                get_volume_snapshot_list(auth_info=auth_info)))

    if not snapshots_to_del:
        msg = "No volume snapshot to delete or provided snapshot(s) not " \
              "exist on system"
        LOG.info(msg)
        return -1, msg

    args_ = '{}{}'.format('--force ' if force else '',
                          ' '.join(snapshots_to_del))
    code, output = cli.openstack('snapshot delete', args_, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code == 1:
        return code, output

    post_vol_snap_list = get_volume_snapshot_list(auth_info=auth_info)
    undeleted_snapshots = list(set(snapshots_to_del) & set(post_vol_snap_list))
    if undeleted_snapshots:
        err_msg = "Volume snapshot {} still exists in cinder snapshot-list " \
                  "after deletion".format(undeleted_snapshots)
        if fail_ok:
            LOG.warning(err_msg)
            return 2, err_msg
        else:
            raise exceptions.CinderError(err_msg)

    succ_msg = "Volume snapshot(s) successfully deleted: {}".format(
        snapshots_to_del)
    LOG.info(succ_msg)
    return 0, succ_msg


def create_volume_qos(qos_name=None, consumer=None, field='id', fail_ok=False,
                      auth_info=Tenant.get('admin'), con_ssh=None, **specs):
    """
    Create volume QoS with given name and specs

    Args:
        qos_name (str):
        fail_ok (bool):
        consumer (str): Valid consumer of QoS specs are: ['front-end',
        'back-end', 'both']
        field (str)
        auth_info (dict):
        con_ssh (SSHClient):
        **specs: QoS specs
            format: **{<spec_name1>: <spec_value1>, <spec_name2>: <spec_value2>}

    Returns (tuple):
        (0, QoS <id> created successfully with specs: <specs dict>)
        (1, <std_err>)

    """
    if not qos_name:
        qos_name = 'vol_qos'

    qos_name = common.get_unique_name(qos_name,
                                      get_volume_qos_list(field='name'),
                                      resource_type='qos')
    args_dict = {
        '--consumer': consumer,
        '--property': specs,
    }
    args_ = common.parse_args(args_dict, repeat_arg=True)

    LOG.info("Creating QoS {} with args: {}".format(qos_name, args_))
    args_ += ' {}'.format(qos_name)
    code, output = cli.openstack('volume qos create', args_, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, output

    qos_tab = table_parser.table(output)
    qos_value = table_parser.get_value_two_col_table(qos_tab, field)

    LOG.info(
        "QoS {} created successfully with specs: {}".format(qos_name, specs))
    return 0, qos_value


def delete_volume_qos(qos_ids, force=False, check_first=True, fail_ok=False,
                      auth_info=Tenant.get('admin'),
                      con_ssh=None):
    """
    Delete given list of QoS'

    Args:
        qos_ids (list|str|tuple):
        force (bool):
        check_first (bool):
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns:

    """
    if isinstance(qos_ids, str):
        qos_ids = [qos_ids]

    qos_ids_to_del = list(qos_ids)
    if check_first:
        existing_qos_list = get_volume_qos_list(auth_info=auth_info,
                                                con_ssh=con_ssh)
        qos_ids_to_del = list(set(existing_qos_list) & set(qos_ids))
        if not qos_ids_to_del:
            msg = "None of the QoS specs {} exist in cinder qos-list. Do " \
                  "nothing.".format(qos_ids)
            LOG.info(msg)
            return -1, msg

    rejected_list = []
    for qos in qos_ids_to_del:
        args = qos if force is None else '--force {} {}'.format(force, qos)
        code, output = cli.openstack('volume qos delete', args,
                                     ssh_client=con_ssh, fail_ok=fail_ok,
                                     auth_info=auth_info)
        if code > 0:
            rejected_list.append(qos)

    qos_list_to_check = list(set(qos_ids) - set(rejected_list))

    undeleted_list = []
    if qos_list_to_check:
        undeleted_list = \
            wait_for_qos_deleted(qos_ids=qos_list_to_check, fail_ok=fail_ok,
                                 con_ssh=con_ssh,
                                 auth_info=auth_info)[1]

    if rejected_list or undeleted_list:
        reject_str = ' Deletion rejected volume QoS: {}.'.format(
            rejected_list) if rejected_list else ''
        undeleted_str = ' Volume QoS still exists after deletion: {}.'.format(
            undeleted_list) if undeleted_list else ''
        err_msg = "Some QoS's failed to delete.{}{}".format(reject_str,
                                                            undeleted_str)
        LOG.warning(err_msg)
        if fail_ok:
            return 1, err_msg
        else:
            raise exceptions.CinderError(err_msg)

    succ_msg = "QoS's successfully deleted: {}".format(qos_ids)
    LOG.info(succ_msg)
    return 0, succ_msg


def wait_for_qos_deleted(qos_ids, timeout=10, check_interval=1, fail_ok=False,
                         auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Wait for given list of QoS to be gone from cinder qos-list
    Args:
        qos_ids (list):
        timeout (int):
        check_interval (int):
        auth_info (dict)
        fail_ok (bool):
        con_ssh (SSHClient):

    Returns (tuple):
        (True, [])          All given QoS ids are gone from cinder qos-list
        (False, [undeleted_qos_list])       Some given QoS' still exist in
        cinder qos-list

    """
    LOG.info("Waiting for QoS' to be deleted from system: {}".format(qos_ids))
    if isinstance(qos_ids, str):
        qos_ids = (qos_ids,)

    qos_undeleted = list(qos_ids)
    end_time = time.time() + timeout

    while time.time() < end_time:
        existing_qos_list = get_volume_qos_list(con_ssh=con_ssh,
                                                auth_info=auth_info)
        qos_undeleted = list(set(existing_qos_list) & set(qos_undeleted))

        if not qos_undeleted:
            msg = "QoS' all gone from 'openstack volume qos list': {}".format(
                qos_ids)
            LOG.info(msg)
            return True, []

        time.sleep(check_interval)

    err_msg = "Timed out waiting for QoS' to be gone from cinder qos-list: " \
              "{}".format(qos_undeleted)
    LOG.warning(err_msg)
    if fail_ok:
        return False, qos_undeleted
    else:
        raise exceptions.CinderError(err_msg)


def create_volume_type(name=None, public=None, project=None,
                       project_domain=None, field='id', fail_ok=False,
                       auth_info=Tenant.get('admin'), con_ssh=None,
                       **properties):
    """
    Create a volume type with given name

    Args:
        name (str|None): name for the volume type
        public (bool|None):
        project (str|None)
        project_domain (str|None)
        field (str): 'id' or 'name'
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple):
        (0, <vol_type_id>)      - volume type created successfully
        (1, <std_err>)          - cli rejected
        (2, <vol_type_id>)      - volume type public flag is not as expected

    """

    if not name:
        name = 'vol_type'
    name = common.get_unique_name(name, get_volume_types(field='Name'))
    LOG.info("Creating volume type {}".format(name))

    args_dict = {
        '--public': True if public else None,
        '--private': True if public is False else None,
        '--property': properties,
        '--project': project,
        '--project-domain': project_domain,
    }

    args_ = ' '.join((common.parse_args(args_dict, repeat_arg=True), name))
    code, output = cli.openstack('volume type create', args_,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code == 1:
        return 1, output

    table_ = table_parser.table(output)
    vol_type = table_parser.get_value_two_col_table(table_, field)

    LOG.info("Volume type {} is created successfully".format(vol_type))
    return 0, vol_type


def delete_volume_types(vol_types, check_first=True, fail_ok=False,
                        auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Delete given volume type

    Args:
        vol_types (list|str|tuple): volume type ID(s) to delete
        check_first (bool):
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple):
        (-1, None of the volume types <ids> exist in cinder qos-list. Do
        nothing.)
        (0, Volume types successfully deleted: <ids>)
        (1, <std_err>)
        (2, Volume types delete rejected: <ids>; volume types still in cinder
        type-list after deletion: <ids>)

    """

    LOG.info("Delete volume types started")
    if isinstance(vol_types, str):
        vol_types = (vol_types,)

    vol_types_to_del = list(vol_types)
    if check_first:
        existing_vol_types = get_volume_types(auth_info=auth_info,
                                              con_ssh=con_ssh)
        vol_types_to_del = list(set(existing_vol_types) & set(vol_types))
        if not vol_types_to_del:
            msg = "None of the volume types {} exist in cinder qos-list. Do " \
                  "nothing.".format(vol_types)
            LOG.info(msg)
            return -1, msg

    args = ' '.join(vol_types_to_del)
    code, output = cli.openstack('volume type delete', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 1:
        return 1, output

    LOG.info("Check volume types are gone from 'openstack volume type list'")
    post_vol_types = get_volume_types(auth_info=auth_info, con_ssh=con_ssh)
    types_undeleted = list(set(post_vol_types) & set(vol_types_to_del))

    if types_undeleted:
        err_msg = "Volume type(s) still in exist after deletion: {}".format(
            types_undeleted)
        LOG.warning(err_msg)
        if fail_ok:
            return 2, err_msg
        else:
            raise exceptions.CinderError(err_msg)

    succ_msg = "Volume types successfully deleted: {}".format(vol_types)
    LOG.info(succ_msg)
    return 0, succ_msg


def get_volume_types(long=False, ids=None, public=None, name=None, strict=True,
                     field='ID', con_ssh=None,
                     auth_info=Tenant.get('admin')):
    """
    Get cinder volume types via openstack volume type list
    Args:
        long (bool)
        ids (str|list|tuple|None):
        public:
        name:
        strict:
        field (str|list|tuple):
        con_ssh:
        auth_info:

    Returns (list):

    """
    args = '--long' if long else ''
    table_ = table_parser.table(
        cli.openstack('volume type list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    filters = {}
    if ids:
        filters['ID'] = ids
    if public is not None:
        filters['Is Public'] = public

    if filters:
        table_ = table_parser.filter_table(table_, **filters)

    if name is not None:
        table_ = table_parser.filter_table(table_, strict=strict,
                                           **{'Name': name})

    return table_parser.get_multi_values(table_, field)


def get_volume_qos_list(field='id', qos_id=None, name=None, consumer=None,
                        strict=True, con_ssh=None,
                        auth_info=Tenant.get('admin')):
    """
    Get qos list based on given filters

    Args:
        field (str|list|tuple): 'id', 'name', 'associations', etc...
        qos_id (list|str|None): volume qos id(s) to filter out from
        name (str|None): name of the qos' to filter for
        consumer (str): consumer of the qos' to filter for
        strict (bool):
        con_ssh:
        auth_info:

    Returns (list): list of matching volume QoS'

    """

    kwargs_raw = {
        'ID': qos_id,
        'Name': name,
        'Consumer': consumer,
    }

    kwargs = {}
    for key, val in kwargs_raw.items():
        if val is not None:
            kwargs[key] = val

    table_ = table_parser.table(
        cli.openstack('volume qos list', ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    return table_parser.get_multi_values(table_, field, strict=strict, **kwargs)


def associate_volume_qos(volume_qos, volume_type, fail_ok=False,
                         auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Associates qos spec with specified volume type.
    # must be an admin to perform cinder qos-associate

    Args:
        volume_qos (str)
        volume_type (str)
        auth_info
        fail_ok (bool)
        con_ssh

    Returns (tuple)

    """
    args_ = '{} {}'.format(volume_qos, volume_type)

    LOG.info(
        "Associate volume qos {} to type {}".format(volume_qos, volume_type))
    code, output = cli.openstack('volume qos associate', args_,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "Volume qos {} is successfully associated to volume type {}".format(
        volume_qos, volume_type)
    LOG.info(msg)
    return 0, msg


def disassociate_volume_qos(volume_qos, volume_type=None, all_vol_types=False,
                            fail_ok=False, con_ssh=None,
                            auth_info=Tenant.get('admin')):
    """
    Disassociate a volume QoS spec from volume type(s)

    Args:
        volume_qos (str):
        volume_type (str|None): volume type name/id
        all_vol_types (bool):
        fail_ok (bool):
        con_ssh:
        auth_info (dict)

    Returns (tuple):

    """
    if not all_vol_types and not volume_type:
        raise ValueError(
            'volume_type has to be specified unless all_vol_types=True')

    if all_vol_types:
        args_ = '--all'
    else:
        args_ = '--volume-type {}'.format(volume_type)

    LOG.info("Disassociating volume qos {} from: {}".format(volume_qos, args_))
    args_ = '{} {}'.format(args_, volume_qos)
    code, output = cli.openstack('volume qos disassociate', args_,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if code > 0:
        return 1, output

    msg = "Volume QoS {} is successfully disassociated".format(volume_qos)
    LOG.info(msg)
    return 0, msg


def get_qos_associations(volume_qos, qos_val='ID', con_ssh=None,
                         auth_info=Tenant.get('admin')):
    """
    Get associated volume types for given volume qos spec
    Args:
        volume_qos:
        qos_val:
        con_ssh:
        auth_info:

    Returns (list): list of volume type names

    """
    key = 'qos_id' if qos_val.lower() == 'id' else 'name'

    associations = get_volume_qos_list(field='associations', con_ssh=con_ssh,
                                       auth_info=auth_info,
                                       **{key: volume_qos})[0]
    associations = [i.strip() for i in associations.split(sep=',')]

    LOG.info("Volume QoS {} associations: {}".format(volume_qos, associations))

    return associations


def is_volumes_pool_sufficient(min_size=40):
    """
    Check if cinder-volume-pool has sufficient space
    Args:
        min_size (int): Minimum requirement for cinder volume pool size in
        Gbs. Default 30G.

    Returns (bool):

    """
    con_ssh = ControllerClient.get_active_controller()
    lvs_pool = con_ssh.exec_sudo_cmd(
        cmd="lvs --units g | grep --color='never' cinder-volumes-pool")[1]
    # Sample output:
    # cinder-volumes-pool                         cinder-volumes twi-aotz--
    # 19.95g                          64.31  33.38
    #   volume-05fa416d-d37b-4d57-a6ff-ab4fe49deece cinder-volumes Vwi-a-tz--
    #   1.00g cinder-volumes-pool    64.16
    #   volume-1b04fa7f-b839-4cf9-a177-e676ec6cf9b7 cinder-volumes Vwi-a-tz--
    #   1.00g cinder-volumes-pool    64.16
    if lvs_pool:
        pool_size = float(
            lvs_pool.splitlines()[0].strip().split()[3].strip()[:-1].split(
                sep='<')[-1])
        return pool_size >= min_size

    # assume enough volumes in ceph:
    return True


def create_volume_snapshot(name, volume=None, description=None, force=False,
                           properties=None, remote_sources=None,
                           fail_ok=False, con_ssh=None, auth_info=None):
    """
    Create snapshot for an existing volume
    Args:
        name (str):
        volume (None):
        description (str|None):
        force (bool):
        properties (None|dict):
        remote_sources (None|dict):
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns (tuple):

    """
    arg_dict = {
        'volume': volume,
        'description': description,
        'force': force,
        'property': properties,
        'remote-source': remote_sources
    }

    arg_str = common.parse_args(arg_dict, repeat_arg=True)
    arg_str += ' {}'.format(name)

    vol = volume if volume else name
    LOG.info('Creating snapshot for volume: {}'.format(vol))
    code, output = cli.openstack('volume snapshot create', arg_str,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    table_ = table_parser.table(output)
    snap_shot_id = table_parser.get_value_two_col_table(table_, 'id')

    LOG.info(
        "Volume snapshot {} created for volume {}. Wait for it to become "
        "available".format(
            snap_shot_id, vol))
    wait_for_vol_snapshot_status(snap_shot_id, status='available',
                                 con_ssh=con_ssh, auth_info=auth_info)

    LOG.info("Volume snapshot {} created and READY for volume {}".format(
        snap_shot_id, vol))
    return 0, snap_shot_id


def import_volume(cinder_volume_backup, vol_id=None, con_ssh=None,
                  fail_ok=False, auth_info=Tenant.get('admin'),
                  retries=2):
    """
    Imports a cinder volume from a backup file located in /opt/backups
    folder. The backup file is expected in
    volume-<uuid>-<date>.tgz  format. Either volume_backup filename or vol_id
    must be provided
    Args:
        cinder_volume_backup(str):  the filename of the backup file
        vol_id (str): - is the uuid of the cinder volume to be imported
        con_ssh:
        fail_ok:
        auth_info:
        retries (int)

    Returns:

    """

    if not cinder_volume_backup and not vol_id:
        raise ValueError("Volume backup file name or vol_id must be provided.")

    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    controller_prompt = Prompt.CONTROLLER_0 + \
        r'|.*controller\-0\:/opt/backups\$'
    controller_prompt += r'|.*controller\-0.*backups.*\$'
    LOG.info('set prompt to:{}'.format(controller_prompt))
    vol_backup = cinder_volume_backup
    vol_id_ = vol_id
    cd_cmd = "cd /opt/backups"
    con_ssh.set_prompt(prompt=controller_prompt)

    con_ssh.exec_cmd(cd_cmd)

    if not cinder_volume_backup:
        # search backup file in /opt/backups
        search_str = "volume-" + vol_id_ + "*.tgz"
        cmd = "cd /opt/backups; ls {}".format(search_str)

        rc, output = con_ssh.exec_cmd(cmd)
        if rc == 0:
            vol_backup = output.split()[0]
        else:
            err_msg = "volume backup file not found in /opt/backups: {}".format(
                output)
            LOG.error(err_msg)
            if fail_ok:
                return -1, err_msg
            else:
                raise exceptions.CinderError(err_msg)
    if not vol_id_:
        vol_id_ = vol_backup[7:-20]

    # according to the user documents, the first time of 'cinder import' may
    # fail, in which case
    # we just have to try again
    for retry in range(retries if 2 <= retries <= 10 else 2):
        con_ssh.set_prompt(prompt=controller_prompt)
        rc, output = cli.cinder('import', vol_backup, ssh_client=con_ssh,
                                fail_ok=fail_ok, auth_info=auth_info)
        if rc == 1:
            LOG.warn(
                'Failed to import volume for the:{} time'.format(retry + 1))

        if wait_for_volume_status(volume=vol_id_,
                                  status=['available', 'in-use'],
                                  auth_info=auth_info,
                                  con_ssh=con_ssh, fail_ok=True):
            break
    else:
        err_msg = "Volume is imported, but not in available/in-use state."
        LOG.warning(err_msg)
        if fail_ok:
            return 2, vol_id_
        else:
            raise exceptions.CinderError(err_msg)

    return 0, "Volume {} is imported successfully".format(vol_id_)


def delete_backups(backup_ids=None, con_ssh=None, fail_ok=False,
                   auth_info=None):
    LOG.info('Deleting backups:{}'.format(backup_ids))

    if backup_ids is None:
        backup_ids = get_backup_ids(con_ssh=con_ssh, fail_ok=fail_ok,
                                    auth_info=auth_info)

    for backup_id in backup_ids:
        LOG.info('Deleting backup:{}'.format(backup_id))
        cli.cinder('backup-delete', backup_id, fail_ok=fail_ok,
                   auth_info=auth_info)


def export_free_volume_using_cinder_backup(vol_id=None, container='cinder',
                                           name='', con_ssh=None, fail_ok=False,
                                           auth_info=None,
                                           backup_file_path='/opt/backups'):
    LOG.info(
        'Exporing free volume using cinder-backup, volume-id:{}'.format(vol_id))
    if not name:
        name = 'free_vol_backup_' + str(vol_id)[0:2] + '_' + str(vol_id)[-5:]

    arg = '--container {} --name {} {}'.format(container, name, vol_id)
    output = table_parser.table(
        cli.cinder('backup-create', arg, ssh_client=con_ssh, fail_ok=fail_ok,
                   auth_info=auth_info)[1])

    backup_id = table_parser.get_value_two_col_table(output, 'id')
    backup_name = table_parser.get_value_two_col_table(output, 'name')
    volume_id = table_parser.get_value_two_col_table(output, 'volume_id')

    LOG.info(
        'TODO: backup_id:{}, backup_name:{}, volume_id:{}'.format(backup_id,
                                                                  backup_name,
                                                                  volume_id))

    assert backup_name == name and volume_id == vol_id

    wait_for_backup_ready(backup_id)

    msg = (
        'backup:{} reached "available" status, check if the files are '
        'gerated'.format(
            backup_id))
    LOG.info('OK,' + msg)
    code, output = con_ssh.exec_sudo_cmd(
        'ls -l {}/*{}*'.format(os.path.join(backup_file_path, container),
                               backup_id))

    if code != 0:
        con_ssh.exec_sudo_cmd(
            'ls -l {}/*'.format(os.path.join(backup_file_path, container)))

    assert 0 == code and output, 'backup became "available", but files are ' \
                                 'not generated'

    return backup_id


def wait_for_backup_ready(backup_id, timeout=900, interval=15, con_ssh=None,
                          fail_ok=False, auth_info=None):
    LOG.info(
        'Waiting for backup reaches "available" status, backup-id:{}'.format(
            backup_id))
    now = time.time()
    end = now + timeout

    while time.time() < end:
        time.sleep(interval)
        status = get_cinder_backup_status(backup_id, con_ssh=con_ssh,
                                          auth_info=auth_info)
        if status == 'available':
            break
    else:
        msg = 'backup did not reach status: "available" within {} ' \
              'seconds'.format(timeout)
        LOG.warning('Error:' + msg)
        if not fail_ok:
            assert False, msg
        return -1

    return 0


def export_busy_volume_using_cinder_backup(vol_id=None,
                                           container='cinder',
                                           name='',
                                           con_ssh=None,
                                           fail_ok=False,
                                           auth_info=None,
                                           backup_file_path='/opt/backups'
                                           ):
    LOG.info('TODO: exporting in-use volume using cinder-backup, vol:{}'.format(
        vol_id))
    if not name:
        name = 'inuse_vol_backup_' + vol_id[-4:]
    snp_id = create_volume_snapshot('snp_' + name, volume=vol_id,
                                    con_ssh=con_ssh,
                                    fail_ok=fail_ok,
                                    force=True, auth_info=auth_info)[1]
    arg = '--container {} --name {} --snapshot-id {} {}'.format(
        container, name, snp_id, vol_id)
    output = table_parser.table(cli.cinder('backup-create', arg,
                                           fail_ok=fail_ok,
                                           auth_info=auth_info)[1])

    backup_id = table_parser.get_value_two_col_table(output, 'id')
    backup_name = table_parser.get_value_two_col_table(output, 'name')
    volume_id = table_parser.get_value_two_col_table(output, 'volume_id')

    LOG.info(
        'TODO: backup_id:{}, backup_name:{}, volume_id:{}'.format(
            backup_id, backup_name, volume_id))

    assert backup_name == name and volume_id == vol_id

    wait_for_backup_ready(backup_id)

    msg = (
        'backup:{} reached "available" status, check if the files are '
        'gerated'.format(
            backup_id))
    LOG.info('OK,' + msg)
    code, output = con_ssh.exec_sudo_cmd(
        'ls -l {}/*{}*'.format(os.path.join(backup_file_path, container),
                               backup_id))

    if code != 0:
        con_ssh.exec_sudo_cmd(
            'ls -l {}/*'.format(os.path.join(backup_file_path, container)))

    assert 0 == code and output, 'backup became "available", but files are ' \
                                 'not generated'

    LOG.info(
        'TODO: successfully exported in-use volume using cinder-backup, '
        'vol:{}'.format(
            vol_id))

    return backup_id


def export_volumes_using_cinder_backup(vol_ids=None, delete_existing=True,
                                       con_ssh=None, fail_ok=False,
                                       auth_info=None,
                                       backup_file_path='/opt/backups'):
    if not vol_ids:
        LOG.warning('No volume IDs specified, skip the rest of test')
        return 0, []

    backup_ids = get_backup_ids(searching_status='', con_ssh=con_ssh,
                                fail_ok=fail_ok, auth_info=auth_info)

    if delete_existing and len(backup_ids) > 0:
        delete_backups(con_ssh=None, fail_ok=fail_ok, auth_info=auth_info)

    code = 0
    exported_volume_ids = []
    for vol_id in vol_ids:
        LOG.info('Backup volume: {}'.format(vol_id))
        volume_status = get_volume_show_values(
            vol_id, 'status', con_ssh=con_ssh)[0]
        if volume_status == 'available':
            code = export_free_volume_using_cinder_backup(
                vol_id=vol_id,
                con_ssh=con_ssh,
                fail_ok=fail_ok,
                auth_info=auth_info,
                backup_file_path=backup_file_path)

        elif volume_status == 'in-use':
            code = export_busy_volume_using_cinder_backup(
                vol_id=vol_id,
                con_ssh=con_ssh,
                fail_ok=fail_ok,
                auth_info=auth_info,
                backup_file_path=backup_file_path)

        exported_volume_ids.append(vol_id)

    LOG.info('Volumes backuped using cinder-backup:{}'.format(
        exported_volume_ids))
    return code, exported_volume_ids


def get_backup_ids(searching_status='available', con_ssh=None, fail_ok=False,
                   auth_info=None):
    if not auth_info:
        auth_info = Tenant.get('admin')

    table_ = table_parser.table(
        cli.cinder('backup-list', ssh_client=con_ssh, fail_ok=fail_ok,
                   auth_info=auth_info)[1])

    if searching_status and searching_status.strip():
        kwargs = {'Status': searching_status.strip()}
        table_ = table_parser.filter_table(table_, **kwargs)

    status = table_parser.get_values(table_, 'Status')
    backup_ids = table_parser.get_values(table_, 'ID')
    volume_ids = table_parser.get_values(table_, 'Volume ID')

    LOG.info('status:{}'.format(status))
    LOG.info('backup_ids:{}'.format(backup_ids))
    LOG.info('volume_ids:{}'.format(volume_ids))
    LOG.info('backup-ids:{}'.format(backup_ids))

    return backup_ids


def get_cinder_backup_status(backup_id, con_ssh=None, fail_ok=False,
                             auth_info=Tenant.get('admin')):
    states = table_parser.table(
        cli.cinder('backup-show', backup_id, ssh_client=con_ssh,
                   fail_ok=fail_ok, auth_info=auth_info)[1])
    return table_parser.get_value_two_col_table(states, 'status')


def export_volumes(vol_ids=None, con_ssh=None, fail_ok=False,
                   auth_info=Tenant.get('admin'), cinder_backup=False,
                   backup_file_path='/opt/backups'):
    """
    Exports cinder volume to controller's /opt/backups folder. The backup
    file is in
    volume-<uuid>-<date>.tgz  format.
    Args:
        vol_ids(list/str):  the list of volume ids to be exported, if none,
            all system volumes are exported
        con_ssh:
        fail_ok:
        auth_info:
        cinder_backup
        backup_file_path

    Returns:

    """
    if not vol_ids:
        vol_ids = get_volumes()
    elif isinstance(vol_ids, str):
        vol_ids = [vol_ids]

    if cinder_backup:
        return export_volumes_using_cinder_backup(
            vol_ids=vol_ids,
            con_ssh=con_ssh,
            fail_ok=fail_ok,
            auth_info=auth_info,
            backup_file_path=backup_file_path)
    volume_exported = []
    for vol_id in vol_ids:

        if get_volume_show_values(vol_id, 'status', con_ssh=con_ssh,
                                  auth_info=auth_info)[0] == 'available':
            # export available volume to ~/opt/backups
            LOG.tc_step("export available volume {} ".format(vol_id))
            code, out = cli.cinder('export', vol_id, ssh_client=con_ssh,
                                   fail_ok=fail_ok, auth_info=auth_info)

            if code > 0:
                return 1, out

            # wait for volume copy to complete
            if not wait_for_volume_status(vol_id, fail_ok=fail_ok,
                                          auth_info=auth_info, con_ssh=con_ssh):
                err_msg = "cinder volume failed to reach available status " \
                          "after export"
                LOG.warning(err_msg)
                return 2, vol_id

            LOG.info(
                "Exported 'Available' Volumes {} successfully ".format(vol_id))
            volume_exported.append(vol_id)

        # execute backup in-use volume command
        if get_volume_show_values(vol_id, 'status', auth_info=auth_info,
                                  con_ssh=con_ssh)[0] == 'in-use':
            LOG.tc_step("export in use volume {} ".format(vol_id))
            snapshot_name = 'snapshot_' + vol_id
            snap_shot_id = create_volume_snapshot(name=snapshot_name,
                                                  volume=vol_id,
                                                  con_ssh=con_ssh,
                                                  auth_info=auth_info)[1]
            LOG.info(
                "Volume snapshot {} created for volume {}".format(snap_shot_id,
                                                                  vol_id))

            # wait for volume copy to complete
            if not wait_for_vol_snapshot_status(snap_shot_id, fail_ok=fail_ok,
                                                auth_info=auth_info,
                                                con_ssh=con_ssh):
                err_msg = "cinder snapshot volume {} failed to reach " \
                          "available status after copy".format(snap_shot_id)
                LOG.warning(err_msg)
                return 3, err_msg

            found_snap = get_vol_snapshots(vol_id=vol_id, auth_info=auth_info,
                                           con_ssh=con_ssh)[0]
            LOG.info(
                "Matched Volume snapshot {} to volume {}".format(found_snap,
                                                                 vol_id))
            if found_snap not in snap_shot_id:
                err_msg = "cinder volume snapshot {} for volume {} not found " \
                          "after export".format(snap_shot_id, vol_id)
                LOG.warn(err_msg)
                if fail_ok:
                    LOG.warning(err_msg)
                    return 4, err_msg
                else:
                    raise exceptions.CinderError(err_msg)

            LOG.info(
                "Exporting in-use Volume snapshot {} ".format(snap_shot_id))
            cli.cinder('snapshot-export', snap_shot_id, ssh_client=con_ssh,
                       auth_info=auth_info)
            if not wait_for_vol_snapshot_status(snap_shot_id, fail_ok=fail_ok,
                                                auth_info=auth_info,
                                                con_ssh=con_ssh):
                err_msg = "cinder snapshot volume {} failed to reach " \
                          "available status after export".format(snap_shot_id)
                return 5, err_msg

            # delete the snapshot after export
            LOG.info(
                "Deleting snapshot Volume snapshot {} after export ".format(
                    snap_shot_id))
            cli.cinder('snapshot-delete', snap_shot_id, ssh_client=con_ssh,
                       auth_info=auth_info)

            LOG.info(
                "Exported 'in-use' Volumes {} successfully ".format(vol_id))
            volume_exported.append(vol_id)

    return 0, volume_exported


def get_lvm_usage(con_ssh):
    LOG.info('Getting usage of cinder-volumes')
    free, total, unit = 0, 0, 'g'
    pattern = r'(\d+(\.\d+)?)([gm])'
    code, output = con_ssh.exec_sudo_cmd('lvs')
    if 0 != code:
        LOG.warn('Failed to get usage of cinder-volumes')
    else:
        try:
            used = 0
            for line in output.strip().splitlines():
                fields = line.split()
                if fields[0] == 'cinder-volumes-pool':
                    total = re.search(pattern, fields[3], re.IGNORECASE)
                    unit = total.group(3)
                    total = float(total.group(1))
                elif fields[0].startswith('volume-'):
                    usage = re.search(pattern, fields[3], re.IGNORECASE)
                    used += float(usage.group(1))

            free = total - used

            LOG.info('lvm usage: free:{}, used:{}, total:{}'.format(free, used,
                                                                    total))
        except Exception:
            LOG.info('Wrong format:{}'.format(output))
            free = total = 0

    return free, total, unit
