#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import os
import re
import time
import json

from pytest import skip

from consts.auth import Tenant, HostLinuxUser
from consts.stx import GuestImages, ImageMetadata
from consts.proj_vars import ProjVar
from consts.timeout import ImageTimeout
from keywords import common, system_helper, host_helper
from testfixtures.fixture_resources import ResourceCleanup
from utils import table_parser, cli, exceptions
from utils.clients.ssh import ControllerClient, get_cli_client
from utils.tis_log import LOG


def get_images(long=False, images=None, field='id',
               auth_info=Tenant.get('admin'), con_ssh=None, strict=True,
               exclude=False, **kwargs):
    """
    Get a list of image id(s) that matches the criteria
    Args:
        long (bool)
        images (str|list): ids of images to filter from
        field(str|list|tuple): id or name
        auth_info (dict):
        con_ssh (SSHClient):
        strict (bool): match full string or substring for the value(s) given
        in kwargs.
            This is only applicable if kwargs key-val pair(s) are provided.
        exclude (bool): whether to exclude item containing the string/pattern
        in kwargs.
            e.g., search for images that don't contain 'raw'
        **kwargs: header-value pair(s) to filter out images from given image
        list. e.g., Status='active', Name='centos'

    Returns (list): list of image ids

    """
    args = '--long' if long else ''
    table_ = table_parser.table(
        cli.openstack('image list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if images:
        table_ = table_parser.filter_table(table_, ID=images)

    return table_parser.get_multi_values(table_, field, strict=strict,
                                         exclude=exclude, **kwargs)


def get_image_id_from_name(name=None, strict=False, fail_ok=True, con_ssh=None,
                           auth_info=None):
    """

    Args:
        name (list or str):
        strict:
        fail_ok (bool): whether to raise exception if no image found with
        provided name
        con_ssh:
        auth_info (dict:

    Returns:
        Return a random image_id that match the name. else return an empty
        string

    """
    if name is None:
        name = GuestImages.DEFAULT['guest']

    matching_images = get_images(name=name, auth_info=auth_info,
                                 con_ssh=con_ssh, strict=strict)
    if not matching_images:
        image_id = ''
        msg = "No existing image found with name: {}".format(name)
        LOG.warning(msg)
        if not fail_ok:
            raise exceptions.CommonError(msg)
    else:
        image_id = matching_images[0]
        if len(matching_images) > 1:
            LOG.warning('More than one glace image found with name {}. '
                        'Select {}.'.format(name, image_id))

    return image_id


def get_avail_image_space(con_ssh, path='/opt/cgcs'):
    """
    Get available disk space in GiB on given path which is where glance
    images are saved at
    Args:
        con_ssh:
        path (str)

    Returns (float): e.g., 9.2

    """
    size = con_ssh.exec_cmd("df {} | awk '{{print $4}}'".format(path),
                            fail_ok=False)[1]
    size = float(size.splitlines()[-1].strip()) / (1024 * 1024)
    return size


def is_image_storage_sufficient(img_file_path=None, guest_os=None,
                                min_diff=0.05, con_ssh=None,
                                image_host_ssh=None):
    """
    Check if glance image storage disk is sufficient to create new glance
    image from specified image
    Args:
        img_file_path (str): e.g., /home/sysadmin/images/tis-centos-guest.img
        guest_os (str): used if img_file_path is not provided. e,g.,
        ubuntu_14, ge_edge, cgcs-guest, etc
        min_diff: minimum difference required between available space and
        specifiec size. e.g., 0.1G
        con_ssh (SSHClient): tis active controller ssh client
        image_host_ssh (SSHClient): such as test server ssh where image file
        was stored

    Returns (bool):

    """
    if image_host_ssh is None:
        image_host_ssh = get_cli_client(central_region=True)
    file_size = get_image_size(img_file_path=img_file_path, guest_os=guest_os,
                               ssh_client=image_host_ssh)

    if con_ssh is None:
        name = 'RegionOne' if ProjVar.get_var('IS_DC') else None
        con_ssh = ControllerClient.get_active_controller(name=name)
    if 0 == con_ssh.exec_cmd('ceph df')[0]:
        # assume image storage for ceph is sufficient
        return True, file_size, None

    avail_size = get_avail_image_space(con_ssh=con_ssh)

    return avail_size - file_size >= min_diff, file_size, avail_size


def get_image_file_info(img_file_path=None, guest_os=None, ssh_client=None):
    """
    Get image file info as dictionary
    Args:
        img_file_path (str): e.g., /home/sysadmin/images/tis-centos-guest.img
        guest_os (str): has to be specified if img_file_path is unspecified.
        e.g., 'tis-centos-guest'
        ssh_client (SSHClient): e.g.,  test server ssh

    Returns (dict): image info dict.
    Examples:
        {
            "virtual-size": 688914432,
            "filename": "images/cgcs-guest.img",
            "format": "raw",
            "actual-size": 688918528,
            "dirty-flag": false
        }

    """
    if not img_file_path:
        if guest_os is None:
            raise ValueError(
                "Either img_file_path or guest_os has to be provided")
        else:
            img_file_info = GuestImages.IMAGE_FILES.get(guest_os, None)
            if not img_file_info:
                raise ValueError(
                    "Invalid guest_os provided. Choose from: {}".format(
                        GuestImages.IMAGE_FILES.keys()))
            # Assume ssh_client is test server client and image path is test
            # server path
            img_file_path = "{}/{}".format(
                GuestImages.DEFAULT['image_dir_file_server'], img_file_info[0])

    def _get_img_dict(ssh_):
        img_info = ssh_.exec_cmd("qemu-img info --output json {}".format(
            img_file_path), fail_ok=False)[1]
        return json.loads(img_info)

    if ssh_client is None:
        with host_helper.ssh_to_test_server() as ssh_client:
            img_dict = _get_img_dict(ssh_=ssh_client)
    else:
        img_dict = _get_img_dict(ssh_=ssh_client)

    LOG.info("Image {} info: {}".format(img_file_path, img_dict))
    return img_dict


def get_image_size(img_file_path=None, guest_os=None, virtual_size=False,
                   ssh_client=None):
    """
    Get image virtual or actual size in GB via qemu-img info
    Args:
        img_file_path (str): e.g., /home/sysadmin/images/tis-centos-guest.img
        guest_os (str): has to be specified if img_file_path is unspecified.
        e.g., 'tis-centos-guest'
        virtual_size:
        ssh_client:

    Returns (float): image size in GiB
    """
    key = "virtual-size" if virtual_size else "actual-size"
    img_size = get_image_file_info(img_file_path=img_file_path,
                                   guest_os=guest_os,
                                   ssh_client=ssh_client)[key]
    img_size = float(img_size) / (1024 * 1024 * 1024)
    return img_size


def get_avail_image_conversion_space(con_ssh=None):
    """
    Get available disk space in GB on /opt/img-conversions
    Args:
        con_ssh:

    Returns (float): e.g., 19.2

    """
    size = con_ssh.exec_cmd("df | grep '/opt/img-conversions' | "
                            "awk '{{print $4}}'")[1]
    size = float(size.strip()) / (1024 * 1024)
    return size


def is_image_conversion_sufficient(img_file_path=None, guest_os=None,
                                   min_diff=0.05, con_ssh=None,
                                   img_host_ssh=None):
    """
    Check if image conversion space is sufficient to convert given image to
    raw format
    Args:
        img_file_path (str): e.g., /home/sysadmin/images/tis-centos-guest.img
        guest_os (str): has to be specified if img_file_path is unspecified.
        e.g., 'tis-centos-guest'
        min_diff (int): in GB
        con_ssh:
        img_host_ssh

    Returns (bool):

    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    if not system_helper.get_storage_nodes(con_ssh=con_ssh):
        return True

    avail_size = get_avail_image_conversion_space(con_ssh=con_ssh)
    file_size = get_image_size(img_file_path=img_file_path, guest_os=guest_os,
                               virtual_size=True,
                               ssh_client=img_host_ssh)

    return avail_size - file_size >= min_diff


def ensure_image_storage_sufficient(guest_os, con_ssh=None):
    """
    Before image file is copied to tis, check if image storage is sufficient
    Args:
        guest_os:
        con_ssh:

    Returns:

    """
    with host_helper.ssh_to_test_server() as img_ssh:
        is_sufficient, image_file_size, avail_size = \
            is_image_storage_sufficient(guest_os=guest_os, con_ssh=con_ssh,
                                        image_host_ssh=img_ssh)
        if not is_sufficient:
            images_to_del = get_images(exclude=True,
                                       Name=GuestImages.DEFAULT['guest'],
                                       con_ssh=con_ssh)
            if images_to_del:
                LOG.info(
                    "Delete non-default images due to insufficient image "
                    "storage media to create required image")
                delete_images(images_to_del, check_first=False, con_ssh=con_ssh)
                if not is_image_storage_sufficient(guest_os=guest_os,
                                                   con_ssh=con_ssh,
                                                   image_host_ssh=img_ssh)[0]:
                    LOG.info(
                        "Insufficient image storage media to create {} image "
                        "even after deleting non-default "
                        "glance images".format(guest_os))
                    return False, image_file_size
            else:
                LOG.info(
                    "Insufficient image storage media to create {} "
                    "image".format(
                        guest_os))
                return False, image_file_size

        return True, image_file_size


def create_image(name=None, image_id=None, source_image_file=None, volume=None,
                 visibility='public', force=None,
                 store=None, disk_format=None, container_format=None,
                 min_disk=None, min_ram=None, tags=None,
                 protected=None, project=None, project_domain=None,
                 timeout=ImageTimeout.CREATE, con_ssh=None,
                 auth_info=Tenant.get('admin'), fail_ok=False,
                 ensure_sufficient_space=True, sys_con_for_dc=True,
                 cleanup=None, hw_vif_model=None, **properties):
    """
    Create an image with given criteria.

    Args:
        name (str): string to be included in image name
        image_id (str): id for the image to be created
        source_image_file (str): local image file to create image from.
        DefaultImage will be used if unset
        volume (str)
        disk_format (str): One of these: ami, ari, aki, vhd, vmdk, raw,
        qcow2, vdi, iso
        container_format (str):  One of these: ami, ari, aki, bare, ovf
        min_disk (int): Minimum size of disk needed to boot image (in gigabytes)
        min_ram (int):  Minimum amount of ram needed to boot image (in
        megabytes)
        visibility (str): public|private|shared|community
        protected (bool): Prevent image from being deleted.
        store (str): Store to upload image to
        force (bool)
        tags (str|tuple|list)
        project (str|None)
        project_domain (str|None)
        timeout (int): max seconds to wait for cli return
        con_ssh (SSHClient):
        auth_info (dict|None):
        fail_ok (bool):
        ensure_sufficient_space (bool)
        sys_con_for_dc (bool): create image on system controller if it's
        distributed cloud
        cleanup (str|None): add to teardown list. 'function', 'class',
        'module', 'session', or None
        hw_vif_model (None|str): if this is set, 'hw_vif_model' in properties
        will be overridden
        **properties: key=value pair(s) of properties to associate with the
            image

    Returns (tuple): (rtn_code(int), message(str))      # 1, 2 only
    applicable if fail_ok=True
        - (0, <id>, "Image <id> is created successfully")
        - (1, <id or ''>, <stderr>)     # openstack image create cli rejected
        - (2, <id>, "Image status is not active.")
    """

    # Use source image url if url is provided. Else use local img file.

    default_guest_img = GuestImages.IMAGE_FILES[GuestImages.DEFAULT['guest']][2]

    file_path = source_image_file
    if not file_path and not volume:
        img_dir = GuestImages.DEFAULT['image_dir']
        file_path = "{}/{}".format(img_dir, default_guest_img)

    if file_path:
        if file_path.startswith('~/'):
            file_path = file_path.replace('~', HostLinuxUser.get_home(), 1)
        file_path = os.path.normpath(file_path)
        if 'win' in file_path and 'os_type' not in properties:
            properties['os_type'] = 'windows'
        elif 'ge_edge' in file_path and 'hw_firmware_type' not in properties:
            properties['hw_firmware_type'] = 'uefi'

    if hw_vif_model:
        properties[ImageMetadata.VIF_MODEL] = hw_vif_model

    if sys_con_for_dc and ProjVar.get_var('IS_DC'):
        con_ssh = ControllerClient.get_active_controller('RegionOne')
        create_auth = Tenant.get(tenant_dictname=auth_info['tenant'],
                                 dc_region='SystemController').copy()
        image_host_ssh = get_cli_client(central_region=True)
    else:
        if not con_ssh:
            con_ssh = ControllerClient.get_active_controller()
        image_host_ssh = get_cli_client()
        create_auth = auth_info

    if ensure_sufficient_space:
        if not is_image_storage_sufficient(img_file_path=file_path,
                                           con_ssh=con_ssh,
                                           image_host_ssh=image_host_ssh)[0]:
            skip('Insufficient image storage for creating glance image '
                 'from {}'.format(file_path))

    source_str = file_path

    known_imgs = ['cgcs-guest', 'tis-centos-guest', 'ubuntu', 'cirros',
                  'opensuse', 'rhel', 'centos', 'win', 'ge_edge',
                  'vxworks', 'debian-8-m-agent']
    name = name if name else 'auto'
    for img_str in known_imgs:
        if img_str in name:
            break
        elif img_str in source_str:
            name = img_str + '_' + name
            break
    else:
        name_prefix = source_str.split(sep='/')[-1]
        name_prefix = name_prefix.split(sep='.')[0]
        name = name_prefix + '_' + name

    name = common.get_unique_name(name_str=name, existing_names=get_images(),
                                  resource_type='image')

    LOG.info("Creating glance image: {}".format(name))

    if not disk_format:
        if not source_image_file:
            # default tis-centos-guest image is raw
            disk_format = 'raw'
        else:
            disk_format = 'qcow2'

    args_dict = {
        '--id': image_id,
        '--store': store,
        '--disk-format': disk_format,
        '--container-format': container_format if container_format else 'bare',
        '--min-disk': min_disk,
        '--min-ram': min_ram,
        '--file': file_path,
        '--force': True if force else None,
        '--protected': True if protected else None,
        '--unprotected': True if protected is False else None,
        '--tag': tags,
        '--property': properties,
        '--project': project,
        '--project-domain': project_domain,
        '--volume': volume,
    }
    if visibility:
        args_dict['--{}'.format(visibility)] = True
    args_ = '{} {}'.format(
        common.parse_args(args_dict, repeat_arg=True, vals_sep=','), name)

    try:
        LOG.info("Creating image {} with args: {}".format(name, args_))
        code, output = cli.openstack('image create', args_, ssh_client=con_ssh,
                                     fail_ok=fail_ok, auth_info=create_auth,
                                     timeout=timeout)
    except:
        # This is added to help debugging image create failure in case of
        # insufficient space
        con_ssh.exec_cmd('df -h', fail_ok=True, get_exit_code=False)
        raise

    table_ = table_parser.table(output)
    actual_id = table_parser.get_value_two_col_table(table_, 'id')
    if cleanup and actual_id:
        ResourceCleanup.add('image', actual_id, scope=cleanup)

    if code > 1:
        return 1, actual_id, output

    in_active = wait_for_image_status(actual_id, con_ssh=con_ssh,
                                      auth_info=create_auth, fail_ok=fail_ok)
    if not in_active:
        return 2, actual_id, "Image status is not active."

    if image_id and image_id != actual_id:
        msg = "Actual image id - {} is different than requested id - {}.".\
            format(actual_id, image_id)
        if fail_ok:
            return 3, actual_id, msg
        raise exceptions.ImageError(msg)

    msg = "Image {} is created successfully".format(actual_id)
    LOG.info(msg)
    return 0, actual_id, msg


def wait_for_image_appear(image_id, auth_info=None, timeout=900, fail_ok=False):
    end_time = time.time() + timeout
    while time.time() < end_time:
        images = get_images(auth_info=auth_info)
        if image_id in images:
            return True

        time.sleep(20)

    if not fail_ok:
        raise exceptions.StorageError(
            "Glance image {} did not appear within {} seconds.".format(image_id,
                                                                       timeout))

    return False


def wait_for_image_status(image_id, status='active',
                          timeout=ImageTimeout.STATUS_CHANGE, check_interval=3,
                          fail_ok=True, con_ssh=None, auth_info=None):
    actual_status = None
    end_time = time.time() + timeout
    while time.time() < end_time:
        actual_status = get_image_values(image_id, fields='status',
                                         auth_info=auth_info,
                                         con_ssh=con_ssh)[0]
        if status.lower() == actual_status.lower():
            LOG.info("Image {} has reached status: {}".format(image_id, status))
            return True

        time.sleep(check_interval)

    else:
        msg = "Timed out waiting for image {} status to change to {}. Actual " \
              "status: {}".format(image_id, status, actual_status)
        if fail_ok:
            LOG.warning(msg)
            return False
        raise exceptions.TimeoutException(msg)


def _wait_for_images_deleted(images, timeout=ImageTimeout.STATUS_CHANGE,
                             fail_ok=True,
                             check_interval=3, con_ssh=None,
                             auth_info=Tenant.get('admin')):
    """
    check if a specific field still exist in a specified column of openstack
    image list

    Args:
        images (list|str):
        timeout (int):
        fail_ok (bool):
        check_interval (int):
        con_ssh:
        auth_info (dict):

    Returns (bool): Return True if the specific image_id is found within the
    timeout period. False otherwise

    """
    if isinstance(images, str):
        images = [images]

    imgs_to_check = list(images)
    imgs_deleted = []
    end_time = time.time() + timeout
    while time.time() < end_time:
        existing_imgs = get_images(con_ssh=con_ssh, auth_info=auth_info)
        for img in imgs_to_check:
            if img not in existing_imgs:
                imgs_to_check.remove(img)
                imgs_deleted.append(img)

        if not imgs_to_check:
            return True, tuple(imgs_deleted)

        time.sleep(check_interval)
    else:
        if fail_ok:
            return False, tuple(imgs_deleted)
        raise exceptions.TimeoutException(
            "Timed out waiting for all given images to be removed from "
            "openstack "
            "image list. Given images: {}. Images still exist: {}.".
            format(images, imgs_to_check))


def image_exists(image, image_val='ID', con_ssh=None,
                 auth_info=Tenant.get('admin')):
    """
    Args:
        image:
        image_val: Name or ID
        con_ssh:
        auth_info

    Returns (bool):

    """
    images = get_images(auth_info=auth_info, con_ssh=con_ssh, field=image_val)
    return image in images


def delete_images(images, timeout=ImageTimeout.DELETE, check_first=True,
                  fail_ok=False, con_ssh=None,
                  auth_info=Tenant.get('admin')):
    """
    Delete given images

    Args:
        images (list|str): ids of images to delete
        timeout (int): max time wait for cli to return, and max time wait for
        images to remove from openstack image list
        check_first (bool): whether to check if images exist before attempt
        to delete
        fail_ok (bool):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "None of the given image(s) exist on system. Do nothing.")
        (0, "image(s) deleted successfully")
        (1, <stderr>)    # if delete image cli returns stderr
        (2, "Delete image cli ran successfully but some image(s) <ids> did
        not disappear within <timeout> seconds")
    """
    if not images:
        return -1, "No image provided to delete"

    LOG.info("Deleting image(s): {}".format(images))
    if isinstance(images, str):
        images = [images]
    else:
        images = list(images)

    if check_first:
        existing_images = get_images(images=images, auth_info=auth_info,
                                     con_ssh=con_ssh)
        imgs_to_del = list(set(existing_images) & set(images))
        if not imgs_to_del:
            msg = "None of the given image(s) exist on system. Do nothing."
            LOG.info(msg)
            return -1, msg
    else:
        imgs_to_del = list(images)

    args_ = ' '.join(imgs_to_del)

    exit_code, cmd_output = cli.openstack('image delete', args_,
                                          ssh_client=con_ssh, fail_ok=fail_ok,
                                          auth_info=auth_info, timeout=timeout)
    if exit_code > 1:
        return 1, cmd_output

    LOG.info("Waiting for images to be removed from openstack image "
             "list: {}".format(imgs_to_del))
    all_deleted, images_deleted = _wait_for_images_deleted(imgs_to_del,
                                                           fail_ok=fail_ok,
                                                           con_ssh=con_ssh,
                                                           auth_info=auth_info,
                                                           timeout=timeout)

    if not all_deleted:
        images_undeleted = set(imgs_to_del) - set(images_deleted)
        msg = "Delete image cli ran successfully but some image(s) {} did " \
              "not disappear within {} seconds".format(images_undeleted,
                                                       timeout)
        return 2, msg

    LOG.info("image(s) are successfully deleted: {}".format(imgs_to_del))
    return 0, "image(s) deleted successfully"


def get_image_properties(image, property_keys, rtn_dict=False,
                         auth_info=Tenant.get('admin'), con_ssh=None):
    """

    Args:
        image (str): id of image
        property_keys (str|list\tuple): list of metadata key(s) to get value(
        s) for
        rtn_dict (bool): whether to return list or dict
        auth_info (dict): Admin by default
        con_ssh (SSHClient):

    Returns (dict|list): image metadata in a dictionary.
        Examples: {'hw_mem_page_size': small}
    """
    if isinstance(property_keys, str):
        property_keys = [property_keys]

    property_keys = [k.strip().lower().replace(':', '_').replace('-', '_') for k
                     in property_keys]
    properties = get_image_values(image, fields='properties',
                                  auth_info=auth_info, con_ssh=con_ssh)[0]

    if rtn_dict:
        return {k: properties.get(k) for k in property_keys}
    else:
        return [properties.get(k) for k in property_keys]


def get_image_values(image, fields, auth_info=Tenant.get('admin'), con_ssh=None,
                     fail_ok=False):
    """
    Get glance image values from openstack image show
    Args:
        image:
        fields:
        auth_info:
        con_ssh:
        fail_ok

    Returns (list):

    """
    if isinstance(fields, str):
        fields = (fields,)
    code, output = cli.openstack('image show', image, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return [None] * len(fields)

    table_ = table_parser.table(output)
    values = table_parser.get_multi_values_two_col_table(
        table_, fields, merge_lines=True, evaluate=True,
        dict_fields='properties')
    return values


def scp_guest_image(img_os='ubuntu_14', dest_dir=None, timeout=3600,
                    con_ssh=None):
    """

    Args:
        img_os (str): guest image os type. valid values: ubuntu, centos_7,
            centos_6
        dest_dir (str): where to save the downloaded image. Default is
            '~/images'
        timeout (int)
        con_ssh (SSHClient):

    Returns (str): full file name of downloaded image. e.g.,
    '~/images/ubuntu_14.qcow2'

    """
    valid_img_os_types = list(GuestImages.IMAGE_FILES.keys())

    if img_os not in valid_img_os_types:
        raise ValueError(
            "Invalid guest image OS type provided. Valid values: {}".format(
                valid_img_os_types))

    if not dest_dir:
        dest_dir = GuestImages.DEFAULT['image_dir']

    LOG.info("Downloading guest image from test server...")
    dest_name = GuestImages.IMAGE_FILES[img_os][2]
    ts_source_name = GuestImages.IMAGE_FILES[img_os][0]
    if con_ssh is None:
        con_ssh = get_cli_client(central_region=True)

    if ts_source_name:
        # img saved on test server. scp from test server
        source_path = '{}/{}'.format(
            GuestImages.DEFAULT['image_dir_file_server'], ts_source_name)
        dest_path = common.scp_from_test_server_to_user_file_dir(
            source_path=source_path, dest_dir=dest_dir,
            dest_name=dest_name, timeout=timeout, con_ssh=con_ssh)
    else:
        # scp from tis system if needed
        dest_path = '{}/{}'.format(dest_dir, dest_name)
        if ProjVar.get_var('REMOTE_CLI') and not con_ssh.file_exists(dest_path):
            tis_source_path = '{}/{}'.format(GuestImages.DEFAULT['image_dir'],
                                             dest_name)
            common.scp_from_active_controller_to_localhost(
                source_path=tis_source_path, dest_path=dest_path,
                timeout=timeout)

    if not con_ssh.file_exists(dest_path):
        raise exceptions.CommonError(
            "image {} does not exist after download".format(dest_path))

    LOG.info("{} image downloaded successfully and saved to {}".format(
        img_os, dest_path))
    return dest_path


def get_guest_image(guest_os, rm_image=True, check_disk=False, cleanup=None,
                    use_existing=True):
    """
    Get or create a glance image with given guest OS
    Args:
        guest_os (str): valid values: ubuntu_12, ubuntu_14, centos_6,
        centos_7, opensuse_11, tis-centos-guest,
                cgcs-guest, vxworks-guest, debian-8-m-agent
        rm_image (bool): whether or not to rm image from /home/sysadmin/images
        after creating glance image
        check_disk (bool): whether to check if image storage disk is
        sufficient to create new glance image
        cleanup (str|None)
        use_existing (bool): whether to use existing guest image if exists

    Returns (str): image_id

    """
    # TODO: temp workaround
    if guest_os in ['opensuse_12', 'win_2016', 'win_2012']:
        skip('Skip test with 20G+ virtual size image for now - CGTS-10776')

    nat_name = ProjVar.get_var('NATBOX').get('name')
    if nat_name == 'localhost':
        if re.search('win|rhel|opensuse', guest_os):
            skip("Skip tests with large images for vbox")

    LOG.info("Get or create a glance image with {} guest OS".format(guest_os))
    img_id = None
    if use_existing:
        img_id = get_image_id_from_name(guest_os, strict=True)

    if not img_id:
        con_ssh = None
        img_file_size = 0
        if check_disk:
            is_sufficient, img_file_size = ensure_image_storage_sufficient(
                guest_os=guest_os)
            if not is_sufficient:
                skip(
                    "Insufficient image storage space in /opt/cgcs/ to create "
                    "{} image".format(
                        guest_os))

        if guest_os == '{}-qcow2'.format(GuestImages.DEFAULT['guest']):
            # convert default img to qcow2 format if needed
            qcow2_img_path = '{}/{}'.format(GuestImages.DEFAULT['image_dir'],
                                            GuestImages.IMAGE_FILES[guest_os][
                                                2])
            con_ssh = ControllerClient.get_active_controller()
            if not con_ssh.file_exists(qcow2_img_path):
                raw_img_path = '{}/{}'.format(GuestImages.DEFAULT['image_dir'],
                                              GuestImages.IMAGE_FILES[
                                                  GuestImages.DEFAULT['guest']][
                                                  2])
                con_ssh.exec_cmd(
                    'qemu-img convert -f raw -O qcow2 {} {}'.format(
                        raw_img_path, qcow2_img_path),
                    fail_ok=False, expect_timeout=600)

        # copy non-default img from test server
        dest_dir = GuestImages.DEFAULT['image_dir']
        home_dir = HostLinuxUser.get_home()
        if check_disk and os.path.normpath(home_dir) in os.path.abspath(
                dest_dir):
            # Assume image file should not be present on system since large
            # image file should get removed
            if not con_ssh:
                con_ssh = ControllerClient.get_active_controller()
            avail_sysadmin_home = get_avail_image_space(con_ssh=con_ssh,
                                                        path=home_dir)
            if avail_sysadmin_home < img_file_size:
                skip("Insufficient space in {} for {} image to be copied "
                     "to".format(home_dir, guest_os))

        image_path = scp_guest_image(img_os=guest_os, dest_dir=dest_dir)

        try:
            disk_format, container_format = GuestImages.IMAGE_FILES[guest_os][
                                            3:5]
            img_id = create_image(name=guest_os, source_image_file=image_path,
                                  disk_format=disk_format,
                                  container_format=container_format,
                                  fail_ok=False, cleanup=cleanup)[1]
        finally:
            if rm_image and not re.search('cgcs-guest|tis-centos|ubuntu_14',
                                          guest_os):
                con_ssh = ControllerClient.get_active_controller()
                con_ssh.exec_cmd('rm -f {}'.format(image_path), fail_ok=True,
                                 get_exit_code=False)

    return img_id


def set_unset_image_vif_multiq(image, set_=True, fail_ok=False, con_ssh=None,
                               auth_info=Tenant.get('admin')):
    """
    Set or unset a glance image with multiple vif-Queues
    Args:
        image (str): name or id of a glance image
        set_ (bool): whether or not to set the  hw_vif_multiqueue_enabled
        fail_ok:
        con_ssh:
        auth_info:

    Returns (str): code, msg

    """

    if image is None:
        return 1, "Error:image_name not provided"
    if set_:
        cmd = 'image set '
    else:
        cmd = 'image unset '

    cmd += image
    cmd += ' --property'

    if set_:
        cmd += ' hw_vif_multiqueue_enabled=True'
    else:
        cmd += ' hw_vif_multiqueue_enabled'

    res, out = cli.openstack(cmd, ssh_client=con_ssh, fail_ok=fail_ok,
                             auth_info=auth_info)

    return res, out


def unset_image(image, properties=None, tags=None, con_ssh=None,
                auth_info=Tenant.get('admin')):
    """

    Args:
        image (str): image name or id
        properties (None|str|list|tuple): properties to unset
        tags (None|str|list|tuple): tags to unset
        con_ssh:
        auth_info:

    Returns:
    """
    args = []
    post_checks = {}
    if properties:
        if isinstance(properties, str):
            properties = [properties]
        for item in properties:
            args.append('--property {}'.format(item))
        post_checks['properties'] = properties

    if tags:
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            args.append('--tag {}'.format(tag))
        post_checks['tags'] = tags

    if not args:
        raise ValueError(
            "Nothing to unset. Please specify property or tag to unset")

    args = ' '.join(args) + ' {}'.format(image)
    code, out = cli.openstack('image unset', args, ssh_client=con_ssh,
                              fail_ok=True, auth_info=auth_info)
    if code > 0:
        return 1, out

    check_image_settings(image=image, check_dict=post_checks, unset=True,
                         con_ssh=con_ssh, auth_info=auth_info)
    msg = "Image {} is successfully unset".format(image)
    return 0, msg


def set_image(image, new_name=None, properties=None, min_disk=None,
              min_ram=None, container_format=None,
              disk_format=None, architecture=None, instance_id=None,
              kernel_id=None, os_distro=None,
              os_version=None, ramdisk_id=None, activate=None, project=None,
              project_domain=None, tags=None,
              protected=None, visibility=None, membership=None,
              hw_vif_model=None,
              con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Set image properties/metadata
    Args:
        image (str):
        new_name (str|None):
        properties (dict|None):
        hw_vif_model (str|None): override hw_vif_model in properties if any
        min_disk (int|str|None):
        min_ram (int|str|None):
        container_format (str|None):
        disk_format (str|None):
        architecture (str|None):
        instance_id (str|None):
        kernel_id (str|None):
        os_distro (str|None):
        os_version (str|None):
        ramdisk_id (str|None):
        activate (bool|None):
        project (str|None):
        project_domain (str|None):
        tags (list|tuple|None):
        protected (bool|None):
        visibility (str): valid values: 'public', 'private', 'community',
        'shared'
        membership (str): valid values: 'accept', 'reject', 'pending'
        con_ssh:
        auth_info:

    Returns (tupe):
        (0, Image <image> is successfully modified)
        (1, <stderr>)   - openstack image set is rejected

    """

    post_checks = {}
    args = []
    if protected is not None:
        if protected:
            args.append('--protected')
            post_check_val = True
        else:
            args.append('--unprocteced')
            post_check_val = False
        post_checks['protected'] = post_check_val

    if visibility is not None:
        valid_vals = ('public', 'private', 'community', 'shared')
        if visibility not in valid_vals:
            raise ValueError(
                "Invalid visibility specified. Valid options: {}".format(
                    valid_vals))
        args.append('--{}'.format(visibility))
        post_checks['visibility'] = visibility

    if activate is not None:
        if activate:
            args.append('--activate')
            post_check_val = 'active'
        else:
            args.append('--deactivate')
            post_check_val = 'deactivated'
        post_checks['status'] = post_check_val

    if membership is not None:
        valid_vals = ('accept', 'reject', 'pending')
        if membership not in valid_vals:
            raise ValueError(
                "Invalid membership specified. Valid options: {}".format(
                    valid_vals))
        args.append('--{}'.format(membership))
        # Unsure how to do post check

    if not properties:
        properties = {}
    if hw_vif_model:
        properties[ImageMetadata.VIF_MODEL] = hw_vif_model
    if properties:
        for key, val in properties.items():
            args.append('--property {}="{}"'.format(key, val))
            post_checks['properties'] = properties

    if tags:
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            args.append('--tag {}'.format(tag))
        post_checks['tags'] = list(tags)

    other_args = {
        '--name': (new_name, 'name'),
        '--min-disk': (min_disk, 'min_disk'),
        '--min-ram': (min_ram, 'min_ram'),
        '--container-format': (container_format, 'container_format'),
        '--disk-format': (disk_format, 'disk_format'),
        '--project': (project, 'owner'),  # assume project id will be given
        '--project-domain': (project_domain, None),  # Post check unhandled atm
        '--architecture': (architecture, None),
        '--instance-id': (instance_id, None),
        '--kernel-id': (kernel_id, None),
        '--os-distro': (os_distro, None),
        '--os-version': (os_version, None),
        '--ramdisk-id': (ramdisk_id, None),
    }

    for key, val in other_args.items():
        if val[0] is not None:
            args.append('{} {}'.format(key, val[0]))
            if val[1]:
                post_checks[val[1]] = val[0]

    args = ' '.join(args)
    if not args:
        raise ValueError("Nothing to set")

    args += ' {}'.format(image)
    code, out = cli.openstack('image set', args, ssh_client=con_ssh,
                              fail_ok=True, auth_info=auth_info)
    if code > 0:
        return 1, out

    check_image_settings(image=image, check_dict=post_checks, con_ssh=con_ssh,
                         auth_info=auth_info)
    msg = "Image {} is successfully modified".format(image)
    return 0, msg


def check_image_settings(image, check_dict, unset=False, con_ssh=None,
                         auth_info=Tenant.get('admin')):
    """
    Check image settings via openstack image show.
    Args:
        image (str):
        check_dict (dict): key should be the field;
            if unset, value should be a list or tuple, key should be properties
                and/or tags
            if set, value should be dict if key is properties or tags,
                otherwise value should normally be a str
        unset (bool): whether to check if given metadata are set or unset
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (None):

    """
    LOG.info("Checking image setting is as specified: {}".format(check_dict))

    post_tab = table_parser.table(
        cli.openstack('image show', image, ssh_client=con_ssh,
                      auth_info=auth_info)[1],
        combine_multiline_entry=True)

    for field, expt_val in check_dict.items():
        actual_val = table_parser.get_value_two_col_table(post_tab, field=field,
                                                          merge_lines=True)
        if field == 'properties':
            actual_vals = actual_val.split(', ')
            actual_vals = ((val.split('=')) for val in actual_vals)
            actual_dict = {k.strip(): v.strip() for k, v in actual_vals}
            if unset:
                for key in expt_val:
                    assert -1 == actual_dict.get(key, -1)
            else:
                for key, val in expt_val.items():
                    actual = actual_dict[key]
                    try:
                        actual = eval(actual)
                    except (NameError, SyntaxError):
                        pass
                    assert str(val) == str(actual), \
                        "Property {} is not as set. Expected: {}, actual: {}". \
                        format(key, val, actual_dict[key])
        elif field == 'tags':
            actual_vals = [val.strip() for val in actual_val.split(',')]
            if unset:
                assert not (set(expt_val) & set(actual_val)), \
                    "Expected to be unset: {}, actual: {}". \
                    format(expt_val, actual_vals)
            else:
                assert set(expt_val) <= set(actual_vals), \
                    "Expected tags: {}, actual: {}".format(
                    expt_val, actual_vals)
        else:
            if unset:
                LOG.warning("Unset flag ignored. Only property and tag "
                            "is valid for unset")
            assert str(expt_val) == str(actual_val), \
                "{} is not as set. Expected: {}, actual: {}". \
                format(field, expt_val, actual_val)
