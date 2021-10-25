#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import copy
import math
import os
import random
import re
import time
import ipaddress
import pexpect
from contextlib import contextmanager

from consts.auth import Tenant, TestFileServer, HostLinuxUser
from consts.stx import VMStatus, NovaCLIOutput, EXT_IP, ImageStatus, \
    VMNetwork, EventLogID, GuestImages, Networks, FlavorSpec, VimEventID
from consts.filepaths import VMPath, UserData, TestServerPath
from consts.proj_vars import ProjVar
from consts.timeout import VMTimeout, CMDTimeout
from utils import exceptions, cli, table_parser, multi_thread
from utils import local_host
from utils.clients.ssh import NATBoxClient, VMSSHClient, ControllerClient, \
    Prompt, get_cli_client
from utils.clients.local import LocalHostClient
from utils.guest_scripts.scripts import TisInitServiceScript
from utils.multi_thread import MThread, Events
from utils.tis_log import LOG
from keywords import network_helper, nova_helper, cinder_helper, host_helper, \
    glance_helper, common, system_helper, \
    storage_helper
from testfixtures.fixture_resources import ResourceCleanup
from testfixtures.recover_hosts import HostsToRecover


def set_vm(vm_id, name=None, state=None, con_ssh=None, auth_info=None,
           fail_ok=False, **properties):
    """
    Set vm with given parameters - name, state, and/or properties
    Args:
        vm_id:
        name:
        state:
        con_ssh:
        auth_info:
        fail_ok:
        **properties:

    Returns (tuple):
        (0, )

    """
    args_dict = {
        '--name': name,
        '--state': state.lower() if state else None,
        '--property': properties,
    }
    args = '{} {}'.format(common.parse_args(args_dict, repeat_arg=True), vm_id)
    LOG.info("Setting vm with args: {}".format(args))
    code, output = cli.openstack('server set', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "VM {} is set successfully.".format(vm_id)
    LOG.info(msg)
    return 0, msg


def unset_vm(vm_id, properties, con_ssh=None, auth_info=None, fail_ok=False):
    """
    Unset given properties for VM
    Args:
        vm_id:
        properties:
        con_ssh:
        auth_info:
        fail_ok:

    Returns (tuple):
        (1, <std_err>)      - cli rejected
        (0,  "VM <vm_id> properties unset successfully: <properties>")

    """
    if isinstance(properties, str):
        properties = (properties,)

    args = '{} {}'.format(
        common.parse_args({'--property': properties}, repeat_arg=True), vm_id)
    LOG.info("Unsetting vm {} properties: {}".format(vm_id, properties))
    code, output = cli.openstack('server unset', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "VM {} properties unset successfully: {}".format(vm_id, properties)
    LOG.info(msg)
    return 0, msg


def get_any_vms(count=None, con_ssh=None, auth_info=None, all_tenants=False,
                rtn_new=False):
    """
    Get a list of ids of any active vms.

    Args:
        count (int): number of vms ids to return. If None, all vms for
        specific tenant will be returned. If num of
        existing vm is less than count additional vm will be created to match
        the count
        con_ssh (SSHClient):
        auth_info (dict):
        all_tenants (bool): whether to get any vms from all tenants or just
        admin tenant if auth_info is set to Admin
        rtn_new (bool): whether to return an extra list containing only the
        newly created vms

    Returns (list):
        vms(list)  # rtn_new=False
        [vms(list), new_vms(list)] # rtn_new=True

    """
    vms = get_vms(con_ssh=con_ssh, auth_info=auth_info,
                  all_projects=all_tenants, Status='ACTIVE')
    if count is None:
        if rtn_new:
            vms = [vms, []]
        return vms
    diff = count - len(vms)
    if diff <= 0:
        vms = random.sample(vms, count)
        if rtn_new:
            vms = [vms, []]
        return vms

    new_vms = []
    for i in range(diff):
        new_vm = boot_vm(con_ssh=con_ssh, auth_info=auth_info)[1]
        vms.append(new_vm)
        new_vms.append(new_vm)

    if rtn_new:
        vms = [vms, new_vms]
    return vms


def create_image_from_vm(vm_id, image_name=None, wait=True,
                         expt_cinder_snapshot=None,
                         fail_ok=False, con_ssh=None, auth_info=None,
                         cleanup=None):
    """
    Create glance image from an existing vm
    Args:
        vm_id:
        image_name:
        wait:
        expt_cinder_snapshot (bool): if vm was booted from cinder volume,
        then a cinder snapshot is expected
        fail_ok:
        con_ssh:
        auth_info:
        cleanup (None|str): valid scopes: function, class, module, session

    Returns (tuple):

    """
    LOG.info("Creating image from vm {}".format(vm_id))
    args_dict = {'--name': image_name, '--wait': wait}
    args = '{} {}'.format(common.parse_args(args_dict), vm_id)
    code, out = cli.openstack('server image create', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)

    table_ = table_parser.table(out)
    image_id = table_parser.get_value_two_col_table(table_, 'id')
    cinder_snapshot_id = None
    if cleanup and image_id:
        ResourceCleanup.add('image', image_id, scope=cleanup)

    if code > 0:
        return 1, out, cinder_snapshot_id

    post_name = table_parser.get_value_two_col_table(table_, 'name')
    if image_name and image_name != post_name:
        raise exceptions.NovaError(
            "Create image does not expected name. Actual {}, expected: "
            "{}".format(post_name, image_name))

    LOG.info(
        "Wait for created image {} to reach active state".format(post_name))
    glance_helper.wait_for_image_status(image_id, status=ImageStatus.ACTIVE,
                                        con_ssh=con_ssh, auth_info=auth_info)

    image_size = table_parser.get_value_two_col_table(table_, 'size')
    if str(image_size) == '0' or expt_cinder_snapshot:
        cinder_snapshotname = "snapshot for {}".format(post_name)
        vol_snapshots = cinder_helper.get_vol_snapshots(
            name=cinder_snapshotname)
        if not vol_snapshots:
            raise exceptions.CinderError(
                "cinder snapshot expected, but was not found: {}".format(
                    cinder_snapshotname))
        cinder_snapshot_id = vol_snapshots[0]
        if cleanup:
            ResourceCleanup.add('vol_snapshot', cinder_snapshot_id)

    LOG.info("glance image {} successfully created from vm {}".format(post_name,
                                                                      vm_id))
    return 0, image_id, cinder_snapshot_id


def add_security_group(vm_id, security_group, fail_ok=False, con_ssh=None,
                       auth_info=None):
    """
    Add given security group to vm
    Args:
        vm_id:
        security_group:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):

    """
    LOG.info("Adding security group {} to vm {}".format(security_group, vm_id))
    args = '{} {}'.format(vm_id, security_group)
    code, output = cli.openstack('server add security group', args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = "Security group {} added to VM {} successfully".format(security_group,
                                                                 vm_id)
    LOG.info(msg)
    return 0, msg


def wait_for_vol_attach(vm_id, vol_id, timeout=VMTimeout.VOL_ATTACH,
                        con_ssh=None, auth_info=None, fail_ok=False):
    """
    Wait for volume attachment appear in openstack server show as well as
    opentstack volume show
    Args:
        vm_id:
        vol_id:
        timeout:
        con_ssh:
        auth_info:
        fail_ok:

    Returns (bool):

    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        vols_attached = get_vm_volumes(vm_id=vm_id, con_ssh=con_ssh,
                                       auth_info=auth_info)
        if vol_id in vols_attached:
            cinder_helper.wait_for_volume_status(vol_id, status='in-use',
                                                 timeout=120, fail_ok=False,
                                                 con_ssh=con_ssh,
                                                 auth_info=auth_info)
            return True
        time.sleep(5)
    else:
        msg = "Volume {} is not shown in nova show {} in {} seconds".format(
            vol_id, vm_id, timeout)
        LOG.warning(msg)
        if not fail_ok:
            raise exceptions.VMError(msg)
        return False


def attach_vol_to_vm(vm_id, vol_id=None, device=None, mount=False, con_ssh=None,
                     auth_info=None, fail_ok=False,
                     cleanup=None):
    """
    Attach a volume to VM
    Args:
        vm_id (str):
        vol_id (str|None): volume to attach. When None, a non-bootable volume
        will be created to attach to given vm
        device (str|None): whether to specify --device in cmd
        mount (bool): if True, login to vm and attempt to mount the device
        after attached. Best effort only.
        con_ssh:
        auth_info:
        fail_ok:
        cleanup:

    Returns:

    """
    if not vol_id:
        vol_id = \
            cinder_helper.create_volume(bootable=False, auth_info=auth_info,
                                        con_ssh=con_ssh, cleanup=cleanup)[1]

    LOG.info("Attaching volume {} to vm {}".format(vol_id, vm_id))
    args = '{}{} {}'.format('--device {} '.format(device) if device else '',
                            vm_id, vol_id)
    code, output = cli.openstack('server add volume', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    LOG.info(
        "Waiting for attached volume to appear in openstack server show and "
        "volume show")
    wait_for_vol_attach(vm_id=vm_id, vol_id=vol_id, con_ssh=con_ssh,
                        auth_info=auth_info)

    if mount:
        LOG.info("Mount attached volume {} to vm {}".format(vol_id, vm_id))
        guest = get_vm_image_name(vm_id)
        if not (guest and 'cgcs-guest' in guest):
            attached_devs = get_vm_volume_attachments(vm_id=vm_id,
                                                      field='device',
                                                      vol_id=vol_id,
                                                      auth_info=auth_info,
                                                      con_ssh=con_ssh)
            device_name = attached_devs[0]
            device = device_name.split('/')[-1]
            LOG.info(
                "Volume {} is attached to VM {} as {}".format(vol_id, vm_id,
                                                              device_name))
            mount_attached_volume(vm_id, device, vm_image_name=guest)

    return 0, vol_id


def is_attached_volume_mounted(vm_id, rootfs, vm_image_name=None, vm_ssh=None):
    """
    Checks if an attached volume is mounted in VM
    Args:
        vm_id (str): - the vm uuid where the volume is attached to
        rootfs (str) - the device name of the attached volume like vda, vdb,
        vdc, ....
        vm_image_name (str): - the  guest image the vm is booted with
        vm_ssh (VMSSHClient): ssh client session to vm
    Returns: bool

    """

    if vm_image_name is None:
        vm_image_name = get_vm_image_name(vm_id)

    cmd = "mount | grep {} |  wc -l".format(rootfs)
    mounted_msg = "Filesystem /dev/{} is mounted: {}".format(rootfs, vm_id)
    not_mount_msg = "Filesystem /dev/{} is not mounted: {}".format(rootfs,
                                                                   vm_id)
    if vm_ssh:
        cmd_output = vm_ssh.exec_sudo_cmd(cmd)[1]
        if cmd_output != '0':
            LOG.info(mounted_msg)
            return True
        LOG.info(not_mount_msg)
        return False

    with ssh_to_vm_from_natbox(vm_id, vm_image_name=vm_image_name) as vm_ssh:

        cmd_output = vm_ssh.exec_sudo_cmd(cmd)[1]
        if cmd_output != '0':
            LOG.info(mounted_msg)
            return True
        LOG.info(not_mount_msg)
        return False


def get_vm_volume_attachments(vm_id, vol_id=None, field='device', con_ssh=None,
                              auth_info=Tenant.get('admin')):
    """
    Get volume attachments for given vm
    Args:
        vm_id:
        vol_id:
        field:
        con_ssh:
        auth_info:

    Returns (list):

    """
    # No replacement in openstack client
    table_ = table_parser.table(
        cli.nova('volume-attachments', vm_id, ssh_client=con_ssh,
                 auth_info=auth_info)[1])
    return table_parser.get_values(table_, field, **{'volume id': vol_id})


def mount_attached_volume(vm_id, rootfs, vm_image_name=None):
    """
    Mounts an attached volume on VM
    Args:
        vm_id (str): - the vm uuid where the volume is attached to
        rootfs (str) - the device name of the attached volume like vda, vdb,
        vdc, ....
        vm_image_name (str): - the  guest image the vm is booted with

    Returns: bool

    """
    wait_for_vm_pingable_from_natbox(vm_id)
    if vm_image_name is None:
        vm_image_name = get_vm_image_name(vm_id)

    with ssh_to_vm_from_natbox(vm_id, vm_image_name=vm_image_name) as vm_ssh:

        if not is_attached_volume_mounted(vm_id, rootfs,
                                          vm_image_name=vm_image_name,
                                          vm_ssh=vm_ssh):
            LOG.info("Creating ext4 file system on /dev/{} ".format(rootfs))
            cmd = "mkfs -t ext4 /dev/{}".format(rootfs)
            rc, output = vm_ssh.exec_cmd(cmd)
            if rc != 0:
                msg = "Failed to create filesystem on /dev/{} for vm " \
                      "{}: {}".format(rootfs, vm_id, output)
                LOG.warning(msg)
                return False
            LOG.info("Mounting /dev/{} to /mnt/volume".format(rootfs))
            cmd = "test -e /mnt/volume"
            rc, output = vm_ssh.exec_cmd(cmd)
            mount_cmd = ''
            if rc == 1:
                mount_cmd += "mkdir -p /mnt/volume; mount /dev/{} " \
                             "/mnt/volume".format(rootfs)
            else:
                mount_cmd += "mount /dev/{} /mnt/volume".format(rootfs)

            rc, output = vm_ssh.exec_cmd(mount_cmd)
            if rc != 0:
                msg = "Failed to mount /dev/{} for vm {}: {}".format(rootfs,
                                                                     vm_id,
                                                                     output)
                LOG.warning(msg)
                return False

            LOG.info(
                "Adding /dev/{} mounting point in /etc/fstab".format(rootfs))
            cmd = "echo \"/dev/{} /mnt/volume ext4  defaults 0 0\" >> " \
                  "/etc/fstab".format(rootfs)

            rc, output = vm_ssh.exec_cmd(cmd)
            if rc != 0:
                msg = "Failed to add /dev/{} mount point to /etc/fstab for " \
                      "vm {}: {}".format(rootfs, vm_id, output)
                LOG.warning(msg)

            LOG.info(
                "/dev/{} is mounted to /mnt/volume for vm {}".format(rootfs,
                                                                     vm_id))
            return True
        else:
            LOG.info(
                "/dev/{} is already mounted to /mnt/volume for vm {}".format(
                    rootfs, vm_id))
            return True


def get_vm_devices_via_virsh(vm_id, con_ssh=None):
    """
    Get vm disks in dict format via 'virsh domblklist <instance_name>'
    Args:
        vm_id (str):
        con_ssh:

    Returns (dict): vm disks per type.
    Examples:
    {'root_img': {'vda': '/dev/nova-local/a746beb9-08e4-4b08-af2a
    -000c8ca72851_disk'},
     'attached_vol': {'vdb': '/dev/disk/by-path/ip-192.168.205.106:3260-iscsi
     -iqn.2010-10.org.openstack:volume-...'},
     'swap': {},
     'eph': {}}

    """
    vm_host = get_vm_host(vm_id=vm_id, con_ssh=con_ssh)
    inst_name = get_vm_instance_name(vm_id=vm_id, con_ssh=con_ssh)

    with host_helper.ssh_to_host(vm_host, con_ssh=con_ssh) as host_ssh:
        output = host_ssh.exec_sudo_cmd('virsh domblklist {}'.format(inst_name),
                                        fail_ok=False)[1]
        disk_lines = output.split('-------------------------------\n', 1)[
            -1].splitlines()

        disks = {}
        root_line = disk_lines.pop(0)
        root_dev, root_source = root_line.split()
        if re.search('openstack:volume|cinder-volumes|/dev/sd', root_source):
            disk_type = 'root_vol'
        else:
            disk_type = 'root_img'
        disks[disk_type] = {root_dev: root_source}
        LOG.info("Root disk: {}".format(disks))

        disks.update({'eph': {}, 'swap': {}, 'attached_vol': {}})
        for line in disk_lines:
            dev, source = line.split()
            if re.search('disk.swap', source):
                disk_type = 'swap'
            elif re.search('openstack:volume|cinder-volumes|/dev/sd', source):
                disk_type = 'attached_vol'
            elif re.search('disk.eph|disk.local', source):
                disk_type = 'eph'
            else:
                raise exceptions.CommonError(
                    "Unknown disk in virsh: {}. Automation update "
                    "required.".format(
                        line))
            disks[disk_type][dev] = source

    LOG.info("disks for vm {}: {}".format(vm_id, disks))
    return disks


def get_vm_boot_volume_via_virsh(vm_id, con_ssh=None):
    """
    Get cinder volume id where the vm is booted from via virsh cmd.
    Args:
        vm_id (str):
        con_ssh (SSHClient):

    Returns (str|None): vol_id or None if vm is not booted from cinder volume

    """
    disks = get_vm_devices_via_virsh(vm_id=vm_id, con_ssh=con_ssh)
    root_vol = disks.get('root_vol', {})
    if not root_vol:
        LOG.info("VM is not booted from volume. Return None")
        return

    root_vol = list(root_vol.values())[0]
    root_vol = re.findall('openstack:volume-(.*)-lun', root_vol)[0]
    LOG.info("vm {} is booted from cinder volume {}".format(vm_id, root_vol))
    return root_vol


def auto_mount_vm_devices(vm_id, devices, guest_os=None, check_first=True,
                          vm_ssh=None):
    """
    Mount and auto mount devices on vm
    Args:
        vm_id (str): - the vm uuid where the volume is attached to
        devices (str|list) - the device name(s). such as vdc or [vda, vdb]
        guest_os (str): - the guest image the vm is booted with. such as
        tis-centos-guest
        check_first (bool): where to check if the device is already mounted
        and auto mounted before mount and automount
        vm_ssh (VMSSHClient):
    """
    if isinstance(devices, str):
        devices = [devices]

    def _auto_mount(vm_ssh_):
        _mounts = []
        for disk in devices:
            fs = '/dev/{}'.format(disk)
            mount_on, fs_type = storage_helper.mount_partition(
                ssh_client=vm_ssh_, disk=disk, partition=fs)
            storage_helper.auto_mount_fs(ssh_client=vm_ssh_, fs=fs,
                                         mount_on=mount_on, fs_type=fs_type,
                                         check_first=check_first)
            _mounts.append(mount_on)
        return _mounts

    if vm_ssh:
        mounts = _auto_mount(vm_ssh_=vm_ssh)
    else:
        with ssh_to_vm_from_natbox(vm_id, vm_image_name=guest_os) as vm_ssh:
            mounts = _auto_mount(vm_ssh_=vm_ssh)

    return mounts


def touch_files(vm_id, file_dirs, file_name=None, content=None, guest_os=None):
    """
    touch files from vm in specified dirs,and adds same content to all
    touched files.
    Args:
        vm_id (str):
        file_dirs (list): e.g., ['/', '/mnt/vdb']
        file_name (str|None): defaults to 'test_file.txt' if set to None
        content (str|None): defaults to "I'm a test file" if set to None
        guest_os (str|None): default guest assumed to set to None

    Returns (tuple): (<file_paths_for_touched_files>, <file_content>)

    """
    if not file_name:
        file_name = 'test_file.txt'
    if not content:
        content = "I'm a test file"

    if isinstance(file_dirs, str):
        file_dirs = [file_dirs]
    file_paths = []
    with ssh_to_vm_from_natbox(vm_id=vm_id, vm_image_name=guest_os) as vm_ssh:
        for file_dir in file_dirs:
            file_path = "{}/{}".format(file_dir, file_name)
            file_path = file_path.replace('//', '/')
            vm_ssh.exec_sudo_cmd(
                'mkdir -p {}; touch {}'.format(file_dir, file_path),
                fail_ok=False)
            time.sleep(3)
            vm_ssh.exec_sudo_cmd('echo "{}" >> {}'.format(content, file_path),
                                 fail_ok=False)
            output = \
                vm_ssh.exec_sudo_cmd('cat {}'.format(file_path),
                                     fail_ok=False)[1]
            # TO DELETE: Debugging purpose only
            vm_ssh.exec_sudo_cmd('mount | grep vd')
            assert content in output, "Expected content {} is not in {}. " \
                                      "Actual content: {}". \
                format(content, file_path, output)
            file_paths.append(file_path)

        vm_ssh.exec_sudo_cmd('sync')
    return file_paths, content


def auto_mount_vm_disks(vm_id, disks=None, guest_os=None):
    """
    Auto mount non-root vm disks and return all the mount points including
    root dir
    Args:
        vm_id (str):
        disks (dict|None): disks returned by  get_vm_devices_via_virsh()
        guest_os (str|None): when None, default guest is assumed.

    Returns (list): list of mount points. e.g., ['/', '/mnt/vdb']

    """
    if not disks:
        disks_to_check = get_vm_devices_via_virsh(vm_id=vm_id)
    else:
        disks_to_check = copy.deepcopy(disks)

    root_disk = disks_to_check.pop('root_vol', {})
    if not root_disk:
        disks_to_check.pop('root_img')

    # add root dir
    mounted_on = ['/']
    devs_to_mount = []
    for val in disks_to_check.values():
        devs_to_mount += list(val.keys())

    LOG.info("Devices to mount: {}".format(devs_to_mount))
    if devs_to_mount:
        mounted_on += auto_mount_vm_devices(vm_id=vm_id, devices=devs_to_mount,
                                            guest_os=guest_os)
    else:
        LOG.info("No non-root disks to mount for vm {}".format(vm_id))

    return mounted_on


vif_map = {
    'e1000': 'normal',
    'rt18139': 'normal',
    'virtio': 'normal',
    'avp': 'normal',
    'pci-sriov': 'direct',
    'pci-passthrough': 'direct-physical'}


def _convert_vnics(nics, con_ssh, auth_info, cleanup):
    """
    Conversion from wrs vif-model to upstream implementation
    Args:
        nics (list|tuple|dict):
        con_ssh
        auth_info
        cleanup (None|str)

    Returns (list):

    """
    converted_nics = []
    for nic in nics:
        nic = dict(nic)  # Do not modify original nic param
        if 'vif-model' in nic:
            vif_model = nic.pop('vif-model')
            if vif_model:
                vnic_type = vif_map[vif_model]
                vif_model_ = vif_model if (
                            system_helper.is_avs() and vnic_type == 'normal')\
                    else None
                if 'port-id' in nic:
                    port_id = nic['port-id']
                    current_vnic_type, current_vif_model = \
                        network_helper.get_port_values(
                            port=port_id,
                            fields=('binding_vnic_type', 'binding_profile'),
                            con_ssh=con_ssh,
                            auth_info=auth_info)
                    if current_vnic_type != vnic_type or (
                            vif_model_ and vif_model_ not in current_vif_model):
                        network_helper.set_port(port_id, vnic_type=vnic_type,
                                                con_ssh=con_ssh,
                                                auth_info=auth_info,
                                                wrs_vif=vif_model_)
                else:
                    net_id = nic.pop('net-id')
                    port_name = common.get_unique_name(
                        'port_{}'.format(vif_model))
                    port_id = network_helper.create_port(net_id, name=port_name,
                                                         wrs_vif=vif_model_,
                                                         vnic_type=vnic_type,
                                                         con_ssh=con_ssh,
                                                         auth_info=auth_info,
                                                         cleanup=cleanup)[1]
                    nic['port-id'] = port_id
        converted_nics.append(nic)

    return converted_nics

def boot_vm_openstack(name=None, flavor=None, block_device_mapping=None,
                      source=None, source_id=None, image_id=None,
                      image_property=None, security_groups=None, key_name=None,
                      inject_file=None, user_data=None, avail_zone=None,
                      nics=None, network=None, port=None, hint=None,
                      config_drive=False, min_count=None, max_count=None,
                      reuse_vol=False, guest_os='', wait=True,
                      fail_ok=False, auth_info=None, con_ssh=None, cleanup=None,
                      **properties):
    """
    Boot a vm with given parameters using opnstack
    Args:
        name (str): New server name
        flavor (str): Create server with this flavor (name or ID)
        block_device_mapping (str): Create a block device on the server.
          Block device mapping in the format
            <dev-name>=<id>:<type>:<size(GB)>:<delete-on-terminate>
              <dev-name>: block device name, like: vdb, xvdc (required)
              <id>: Name or ID of the volume, volume snapshot or image (required)
              <type>: volume, snapshot or image; default: volume (optional)
              <size(GB)>: volume size if create from image or snapshot (optional)
              <delete-on-terminate>: true or false; default: false (optional)
        source (str): 'image', 'volume', 'snapshot'
        source_id (str): id of the specified source. such as volume_id, image_id, or snapshot_id
        image_id (str): id of glance image. Will not be used if source is image and source_id is
          specified
        image_property (str): <key=value> Image property to be matched
        security_groups (str|list|tuple): Security group/groups
          to assign to this server (name or ID)
        key_name (str): Keypair to inject into this server (optional extension)
        inject_file (str|list|tuple): File/Files to inject into image before boot
        user_data (str|list): User data file to serve from the metadata server
        avail_zone (str): Select an availability zone for the server
        nics (list|tuple): Create NIC's on the server.
          each nic:
            <net-id=net-uuid,v4-fixed-ip=ip-addr,v6-fixed-ip=ip-addr, port-id=port-uuid,auto,none>,
              <vif-model=model,vif-pci-address=pci-address>
            Examples: [{'net-id': <net_id1>, 'vif-model': <vif1>},
                       {'net-id': <net_id2>, 'vif-model': <vif2>}, ...]
            Notes: valid vif-models:
              virtio, avp, e1000, pci-passthrough, pci-sriov, rtl8139, ne2k_pci, pcnet
        network (str|list|tuple): Create a NIC on the server and connect it to network.
          This is a wrapper for the ‘–nic net-id=<network>’ parameter that provides simple syntax
          for the standard use case of connecting a new server to a given network.
          For more advanced use cases, refer to the ‘–nic’ parameter.
        port (str|list|tuple): Create a NIC on the server and connect it to port.
          This is a wrapper for the ‘–nic port-id=<port>’ parameter that provides simple syntax
          for the standard use case of connecting a new server to a given port.
          For more advanced use cases, refer to the ‘–nic’ parameter.
        hint (dict): key/value pair(s) sent to scheduler for custom use, such as
          group=<server_group_id>
        config_drive (<config-drive-volume>|True): Use specified volume as the config drive,
          or ‘True’ to use an ephemeral drive
        min_count (int): Minimum number of servers to launch (default=1)
        max_count (int): Maximum number of servers to launch (default=1)
        reuse_vol (bool): whether or not to reuse the existing volume (default False)
        guest_os (str): Valid values: 'cgcs-guest', 'ubuntu_14', 'centos_6', 'centos_7', etc.
            This will be overriden by image_id if specified.
        wait (bool): Wait for build to complete (default True)
        fail_ok (bool):
        auth_info:
        con_ssh:
        cleanup (str|None): valid values: 'module', 'session', 'function', 'class',
          vm (and volume) will be deleted as part of teardown

    Returns (tuple): (rtn_code(int), new_vm_id_if_any(str), message(str),
    new_vol_id_if_any(str))
        (0, vm_id, 'VM is booted successfully')   # vm is created
        successfully and in Active state.
        (1, vm_id, <stderr>)      # boot vm cli command failed, but vm is
        still booted
        (2, vm_id, "VM boot started, check skipped (wait={}).")   # boot vm cli
        accepted, but vm building is not
            100% completed. Only applicable when wait=False
        (3, vm_id, "VM <uuid> did not reach ACTIVE state within <seconds>. VM
        status: <status>")
            # vm is not in Active state after created.
        (4, '', <stderr>): create vm cli command failed, vm is not booted

    """
    # Prechecks
    valid_cleanups = (None, 'function', 'class', 'module', 'session')
    if cleanup not in valid_cleanups:
        raise ValueError(
            "Invalid scope provided. Choose from: {}".format(valid_cleanups))

    if user_data is None and guest_os and not re.search(
            GuestImages.TIS_GUEST_PATTERN, guest_os):
        # create userdata cloud init file to run right after vm
        # initialization to get ip on interfaces other than eth0.
        user_data = _create_cloud_init_if_conf(guest_os, nics_num=len(nics))

    if user_data and user_data.startswith('~'):
        user_data = user_data.replace('~', HostLinuxUser.get_home(), 1)

    if inject_file and inject_file.startswith('~'):
        inject_file = inject_file.replace('~', HostLinuxUser.get_home(), 1)

    if guest_os == 'vxworks':
        LOG.tc_step("Add HPET Timer extra spec to flavor")
        extra_specs = {FlavorSpec.HPET_TIMER: 'True'}
        properties.update(extra_specs)

    LOG.info("Processing boot_vm_openstack args...")
    # Handle mandatory arg - name
    tenant = common.get_tenant_name(auth_info=auth_info)
    if name is None:
        name = 'vm'
    name = "{}-{}".format(tenant, name)
    name = common.get_unique_name(name, resource_type='vm')

    # Handle mandatory arg - key_name
    key_name = key_name if key_name is not None else get_default_keypair(
        auth_info=auth_info, con_ssh=con_ssh)

    # Handle mandatory arg - flavor
    if flavor is None:
        flavor = nova_helper.get_basic_flavor(auth_info=auth_info,
                                              con_ssh=con_ssh,
                                              guest_os=guest_os)

    # Handle mandatory arg - nics
    if not nics:
        mgmt_net_id = network_helper.get_mgmt_net_id(auth_info=auth_info,
                                                     con_ssh=con_ssh)
        if not mgmt_net_id:
            raise exceptions.NeutronError("Cannot find management network")
        nics = [{'net-id': mgmt_net_id}]

        if 'edge' not in guest_os and 'vxworks' not in guest_os:
            tenant_net_id = network_helper.get_tenant_net_id(
                auth_info=auth_info, con_ssh=con_ssh)
            if tenant_net_id:
                nics.append({'net-id': tenant_net_id})

    if isinstance(nics, dict):
        nics = [nics]
    nics = _convert_vnics(nics, con_ssh=con_ssh, auth_info=auth_info,
                          cleanup=cleanup)

    # Handle mandatory arg - boot source
    volume_id = snapshot_id = image = None
    if source is None:
        if min_count is None and max_count is None:
            source = 'volume'
        else:
            source = 'image'

    elif source.lower() == 'snapshot' and not block_device_mapping:
        snapshot_id = source_id
        if not snapshot_id:
            snapshot_id = cinder_helper.get_vol_snapshots(
                auth_info=auth_info, con_ssh=con_ssh)
            if not snapshot_id:
                raise ValueError(
                    "snapshot id is required to boot vm; however no "
                    "snapshot exists on the system.")
            snapshot_id = snapshot_id[0]
        block_device_mapping = {"vdb": "{}:snapshot".format(snapshot_id)}
        vol_size, vol_id = cinder_helper.get_volume_snapshot_values(snapshot_id, ["size", "volume_id"])
        img_id = cinder_helper.get_volume_show_values(vol_id, "volume_image_metadata")[0]["image_id"]
        image = img_id
        if vol_size:
            block_device_mapping["vdb"] = "{}:{}".format(block_device_mapping["vdb"], vol_size)
    elif source.lower() == 'volume':
        if source_id:
            volume_id = source_id
        else:
            vol_name = 'vol-' + name
            if reuse_vol:
                volume_id = cinder_helper.get_any_volume(
                    new_name=vol_name,
                    auth_info=auth_info,
                    con_ssh=con_ssh,
                    cleanup=cleanup)
            else:
                volume_id = cinder_helper.create_volume(
                    name=vol_name,
                    source_id=image_id,
                    auth_info=auth_info,
                    con_ssh=con_ssh,
                    guest_image=guest_os,
                    cleanup=cleanup)[1]
    elif source.lower() == 'image':
        # image property is not compatible with image
        if not image_property:
            image = source_id if source_id else image_id
            if not image:
                img_name = guest_os if guest_os else GuestImages.DEFAULT['guest']
                image = glance_helper.get_image_id_from_name(img_name,
                                                             strict=True,
                                                             fail_ok=False)

    # create cmd
    non_repeat_args = {'--flavor': flavor,
                       '--block-device-mapping': block_device_mapping,
                       '--image': image,
                       '--image_property': image_property,
                       '--volume': volume_id,
                       '--min-count': str(min_count) if min_count is not None else None,
                       '--max-count': str(max_count) if max_count is not None else None,
                       '--key-name': key_name,
                       '--user-data': user_data,
                       '--availability_zone': avail_zone,
                       '--config-drive': str(config_drive) if config_drive else None,
                       '--wait': wait,
                       }
    non_repeat_args = common.parse_args(non_repeat_args, repeat_arg=False,
                                        vals_sep=',')

    repeat_args = {
        '--nic': nics,
        '--network': network,
        '--port': port,
        '--file': inject_file,
        '--security-groups': security_groups,
        '--hint': hint,
        '--property': properties
    }
    repeat_args = common.parse_args(repeat_args, repeat_arg=True, vals_sep=',')

    pre_boot_vms = []
    if not (min_count is None and max_count is None):
        name_str = name + '-'
        pre_boot_vms = get_vms(auth_info=auth_info, con_ssh=con_ssh,
                               strict=False, name=name_str)

    args_ = ' '.join([non_repeat_args, repeat_args, name])
    LOG.info("Booting VM {} with args: {}".format(name, args_))
    exitcode, output = cli.openstack('server create', positional_args=args_,
                                     ssh_client=con_ssh, fail_ok=True,
                                     auth_info=auth_info,
                                     timeout=VMTimeout.BOOT_VM)

    if min_count is None and max_count is None:
        table_ = table_parser.table(output)
        vm_id = table_parser.get_value_two_col_table(table_, 'id')
        if cleanup and vm_id:
            ResourceCleanup.add('vm', vm_id, scope=cleanup, del_vm_vols=False)
            # if source="snapshot":
            #     ResourceCleanup.add('snapshot', snapshot_id, scope=cleanup, del_vm_vols=False)

        if exitcode == 1:
            if vm_id:
                # print out vm show for debugging purpose
                cli.openstack('server show', vm_id, ssh_client=con_ssh,
                              auth_info=Tenant.get('admin'))
            if not fail_ok:
                raise exceptions.VMOperationFailed(output)

            if vm_id:
                return 1, vm_id, output  # vm_id = '' if cli is rejected
                # without vm created
            return 4, '', output

        LOG.info("Post action check...")
        vm_status = get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh,
                                      auth_info=auth_info)[0]
        if wait:
            if vm_status != VMStatus.ACTIVE:
                message = "VM did not reach {} state: {}".format(VMStatus.ACTIVE, vm_status)
                if fail_ok:
                    LOG.warning(message)
                    return 2, vm_id, message
                else:
                    raise exceptions.VMPostCheckFailed(message)
        else:
            LOG.info("VM {} started to create, \
                     check skipped because of wait argument wait={}, \
                     vm status is: {}".format(vm_id, wait, vm_status))
            return 2, vm_id, "VM boot started, \
                              check skipped (wait={}), \
                              vm status is: {}".format(wait, vm_status)
        LOG.info("VM {} is booted successfully.".format(vm_id))
        return 0, vm_id, 'VM is booted successfully'
    else:
        name_str = name + '-'
        post_boot_vms = get_vms(auth_info=auth_info, con_ssh=con_ssh,
                                strict=False, name=name_str)
        vm_ids = list(set(post_boot_vms) - set(pre_boot_vms))
        if cleanup and vm_ids:
            ResourceCleanup.add('vm', vm_ids, scope=cleanup, del_vm_vols=False)

        if exitcode == 1:
            return 1, vm_ids, output


        for instance_id in vm_ids:
            vm_status = get_vm_values(instance_id, 'status', strict=True, con_ssh=con_ssh,
                                      auth_info=auth_info)[0]
            if wait:
                if vm_status != VMStatus.ACTIVE:
                    msg = "VMs failed to reach {} state: {}".format(VMStatus.ACTIVE, vm_status)
                    if fail_ok:
                        LOG.warning(msg)
                        return 3, vm_ids, msg
            else:
                LOG.warning("VM {} started to create, \
                            check skipped because of wait argument wait={}, \
                            vm status is: {}".format(vm_id, wait, vm_status))
        LOG.info("VMs booted successfully: {}".format(vm_ids))
        return 0, vm_ids, "VMs are booted successfully"


def boot_vm(name=None, flavor=None, source=None, source_id=None, image_id=None,
            min_count=None, nics=None, hint=None,
            max_count=None, key_name=None, swap=None, ephemeral=None,
            user_data=None, block_device=None,
            block_device_mapping=None, security_groups=None, vm_host=None,
            avail_zone=None, file=None,
            config_drive=False, meta=None, tags=None,
            fail_ok=False, auth_info=None, con_ssh=None, reuse_vol=False,
            guest_os='', poll=True, cleanup=None):
    """
    Boot a vm with given parameters
    Args:
        name (str):
        flavor (str):
        source (str): 'image', 'volume', 'snapshot', or 'block_device'
        source_id (str): id of the specified source. such as volume_id,
        image_id, or snapshot_id
        image_id (str): id of glance image. Will not be used if source is
        image and source_id is specified
        min_count (int):
        max_count (int):
        key_name (str):
        swap (int|None):
        ephemeral (int):
        user_data (str|list):
        vm_host (str): which host to place the vm
        avail_zone (str): availability zone for vm host, Possible values:
        'nova', 'stxauto', etc
        block_device (dict|list|tuple): dist or list of dict, each dictionary
        is a block device.
            e.g, {'source': 'volume', 'volume_id': xxxx, ...}
        block_device_mapping (str):  Block device mapping in the format
        '<dev-name>=<id>:<type>:<size(GB)>:<delete-on-
                                terminate>'.
        auth_info (dict):
        con_ssh (SSHClient):
        security_groups (str|list|tuple): add nova boot option
        --security-groups $(sec_group_name)
        nics (list): nics to be created for the vm
            each nic: <net-id=net-uuid,net-name=network-name,
            v4-fixed-ip=ip-addr,v6-fixed-ip=ip-addr,
                        port-id=port-uuid,vif-model=model>,
                        vif-pci-address=pci-address>
            Examples: [{'net-id': <net_id1>, 'vif-model': <vif1>}, {'net-id':
            <net_id2>, 'vif-model': <vif2>}, ...]
            Notes: valid vif-models:
                virtio, avp, e1000, pci-passthrough, pci-sriov, rtl8139,
                ne2k_pci, pcnet

        hint (dict): key/value pair(s) sent to scheduler for custom use. such
        as group=<server_group_id>
        file (str): <dst-path=src-path> To store files from local <src-path>
        to <dst-path> on the new server.
        config_drive (bool): To enable config drive.
        meta (dict): key/value pairs for vm meta data. e.g.,
        {'sw:wrs:recovery_priority': 1, ...}
        tags (None|str|tuple|list)
        fail_ok (bool):
        reuse_vol (bool): whether or not to reuse the existing volume
        guest_os (str): Valid values: 'cgcs-guest', 'ubuntu_14', 'centos_6',
        'centos_7', etc.
            This will be overriden by image_id if specified.
        poll (bool):
        cleanup (str|None): valid values: 'module', 'session', 'function',
        'class', vm (and volume) will be deleted as
            part of teardown

    Returns (tuple): (rtn_code(int), new_vm_id_if_any(str), message(str),
    new_vol_id_if_any(str))
        (0, vm_id, 'VM is booted successfully')   # vm is created
        successfully and in Active state.
        (1, vm_id, <stderr>)      # boot vm cli command failed, but vm is
        still booted
        (2, vm_id, "VM building is not 100% complete.")   # boot vm cli
        accepted, but vm building is not
            100% completed. Only applicable when poll=True
        (3, vm_id, "VM <uuid> did not reach ACTIVE state within <seconds>. VM
        status: <status>")
            # vm is not in Active state after created.
        (4, '', <stderr>): create vm cli command failed, vm is not booted

    """
    valid_cleanups = (None, 'function', 'class', 'module', 'session')
    if cleanup not in valid_cleanups:
        raise ValueError(
            "Invalid scope provided. Choose from: {}".format(valid_cleanups))

    LOG.info("Processing boot_vm args...")
    # Handle mandatory arg - name
    tenant = common.get_tenant_name(auth_info=auth_info)
    if name is None:
        name = 'vm'
    name = "{}-{}".format(tenant, name)
    name = common.get_unique_name(name, resource_type='vm')

    # Handle mandatory arg - key_name
    key_name = key_name if key_name is not None else get_default_keypair(
        auth_info=auth_info, con_ssh=con_ssh)

    # Handle mandatory arg - flavor
    if flavor is None:
        flavor = nova_helper.get_basic_flavor(auth_info=auth_info,
                                              con_ssh=con_ssh,
                                              guest_os=guest_os)

    if guest_os == 'vxworks':
        LOG.tc_step("Add HPET Timer extra spec to flavor")
        extra_specs = {FlavorSpec.HPET_TIMER: 'True'}
        nova_helper.set_flavor(flavor=flavor, **extra_specs)

    # Handle mandatory arg - nics
    if not nics:
        mgmt_net_id = network_helper.get_mgmt_net_id(auth_info=auth_info,
                                                     con_ssh=con_ssh)
        if not mgmt_net_id:
            raise exceptions.NeutronError("Cannot find management network")
        nics = [{'net-id': mgmt_net_id}]

        if 'edge' not in guest_os and 'vxworks' not in guest_os:
            tenant_net_id = network_helper.get_tenant_net_id(
                auth_info=auth_info, con_ssh=con_ssh)
            if tenant_net_id:
                nics.append({'net-id': tenant_net_id})

    if isinstance(nics, dict):
        nics = [nics]
    nics = _convert_vnics(nics, con_ssh=con_ssh, auth_info=auth_info,
                          cleanup=cleanup)

    # Handle mandatory arg - boot source
    volume_id = snapshot_id = image = None
    if source != 'block_device':
        if source is None:
            if min_count is None and max_count is None:
                source = 'volume'
            else:
                source = 'image'

        if source.lower() == 'volume':
            if source_id:
                volume_id = source_id
            else:
                vol_name = 'vol-' + name
                if reuse_vol:
                    volume_id = cinder_helper.get_any_volume(
                        new_name=vol_name,
                        auth_info=auth_info,
                        con_ssh=con_ssh,
                        cleanup=cleanup)
                else:
                    volume_id = cinder_helper.create_volume(
                        name=vol_name,
                        source_id=image_id,
                        auth_info=auth_info,
                        con_ssh=con_ssh,
                        guest_image=guest_os,
                        cleanup=cleanup)[1]

        elif source.lower() == 'image':
            image = source_id if source_id else image_id
            if not image:
                img_name = guest_os if guest_os else GuestImages.DEFAULT[
                    'guest']
                image = glance_helper.get_image_id_from_name(img_name,
                                                             strict=True,
                                                             fail_ok=False)

        elif source.lower() == 'snapshot':
            snapshot_id = source_id
            if not snapshot_id:
                snapshot_id = cinder_helper.get_vol_snapshots(
                    auth_info=auth_info, con_ssh=con_ssh)
                if not snapshot_id:
                    raise ValueError(
                        "snapshot id is required to boot vm; however no "
                        "snapshot exists on the system.")
                snapshot_id = snapshot_id[0]

    if vm_host and not avail_zone:
        avail_zone = 'nova'
    if avail_zone and vm_host:
        avail_zone = '{}:{}'.format(avail_zone, vm_host)

    if user_data is None and guest_os and not re.search(
            GuestImages.TIS_GUEST_PATTERN, guest_os):
        # create userdata cloud init file to run right after vm
        # initialization to get ip on interfaces other than eth0.
        user_data = _create_cloud_init_if_conf(guest_os, nics_num=len(nics))

    if user_data and user_data.startswith('~'):
        user_data = user_data.replace('~', HostLinuxUser.get_home(), 1)

    if file and file.startswith('~'):
        file = file.replace('~', HostLinuxUser.get_home(), 1)

    # create cmd
    non_repeat_args = {'--flavor': flavor,
                       '--image': image,
                       '--boot-volume': volume_id,
                       '--snapshot': snapshot_id,
                       '--min-count': str(
                           min_count) if min_count is not None else None,
                       '--max-count': str(
                           max_count) if max_count is not None else None,
                       '--key-name': key_name,
                       '--swap': swap,
                       '--user-data': user_data,
                       '--ephemeral': ephemeral,
                       '--availability-zone': avail_zone,
                       '--file': file,
                       '--config-drive': str(
                           config_drive) if config_drive else None,
                       '--block-device-mapping': block_device_mapping,
                       '--security-groups': security_groups,
                       '--tags': tags,
                       '--poll': poll,
                       }
    non_repeat_args = common.parse_args(non_repeat_args, repeat_arg=False,
                                        vals_sep=',')

    repeat_args = {
        '--meta': meta,
        '--nic': nics,
        '--hint': hint,
        '--block-device': block_device,
    }
    repeat_args = common.parse_args(repeat_args, repeat_arg=True, vals_sep=',')

    pre_boot_vms = []
    if not (min_count is None and max_count is None):
        name_str = name + '-'
        pre_boot_vms = get_vms(auth_info=auth_info, con_ssh=con_ssh,
                               strict=False, name=name_str)

    args_ = ' '.join([non_repeat_args, repeat_args, name])
    LOG.info("Booting VM {} with args: {}".format(name, args_))
    exitcode, output = cli.nova('boot', positional_args=args_,
                                ssh_client=con_ssh, fail_ok=True,
                                auth_info=auth_info,
                                timeout=VMTimeout.BOOT_VM)

    tmout = VMTimeout.STATUS_CHANGE
    if min_count is None and max_count is None:
        table_ = table_parser.table(output)
        vm_id = table_parser.get_value_two_col_table(table_, 'id')
        if cleanup and vm_id:
            ResourceCleanup.add('vm', vm_id, scope=cleanup, del_vm_vols=False)

        if exitcode == 1:
            if vm_id:
                # print out vm show for debugging purpose
                cli.openstack('server show', vm_id, ssh_client=con_ssh,
                              auth_info=Tenant.get('admin'))
            if not fail_ok:
                raise exceptions.VMOperationFailed(output)

            if vm_id:
                return 1, vm_id, output  # vm_id = '' if cli is rejected
                # without vm created
            return 4, '', output

        LOG.info("Post action check...")
        if poll and "100% complete" not in output:
            message = "VM building is not 100% complete."
            if fail_ok:
                LOG.warning(message)
                return 2, vm_id, "VM building is not 100% complete."
            else:
                raise exceptions.VMOperationFailed(message)

        if not wait_for_vm_status(vm_id=vm_id, status=VMStatus.ACTIVE,
                                  timeout=tmout, con_ssh=con_ssh,
                                  auth_info=auth_info, fail_ok=True):
            vm_status = \
                get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh,
                              auth_info=auth_info)[0]
            message = "VM {} did not reach ACTIVE state within {}. VM " \
                      "status: {}".format(vm_id, tmout, vm_status)
            if fail_ok:
                LOG.warning(message)
                return 3, vm_id, message
            else:
                raise exceptions.VMPostCheckFailed(message)

        LOG.info("VM {} is booted successfully.".format(vm_id))

        return 0, vm_id, 'VM is booted successfully'

    else:
        name_str = name + '-'
        post_boot_vms = get_vms(auth_info=auth_info, con_ssh=con_ssh,
                                strict=False, name=name_str)
        vm_ids = list(set(post_boot_vms) - set(pre_boot_vms))
        if cleanup and vm_ids:
            ResourceCleanup.add('vm', vm_ids, scope=cleanup, del_vm_vols=False)

        if exitcode == 1:
            return 1, vm_ids, output

        result, vms_in_state, vms_failed_to_reach_state = wait_for_vms_values(
            vm_ids, fail_ok=True, timeout=tmout,
            con_ssh=con_ssh,
            auth_info=Tenant.get('admin'))
        if not result:
            msg = "VMs failed to reach ACTIVE state: {}".format(
                vms_failed_to_reach_state)
            if fail_ok:
                LOG.warning(msg=msg)
                return 3, vm_ids, msg

        LOG.info("VMs booted successfully: {}".format(vm_ids))
        return 0, vm_ids, "VMs are booted successfully"


def wait_for_vm_pingable_from_natbox(vm_id, timeout=200, fail_ok=False,
                                     con_ssh=None, use_fip=False):
    """
    Wait for ping vm from natbox succeeds.

    Args:
        vm_id (str): id of the vm to ping
        timeout (int): max retry time for pinging vm
        fail_ok (bool): whether to raise exception if vm cannot be ping'd
        successfully from natbox within timeout
        con_ssh (SSHClient): TiS server ssh handle
        use_fip (bool): whether or not to ping floating ip only if any

    Returns (bool): True if ping vm succeeded, False otherwise.

    """
    ping_end_time = time.time() + timeout
    while time.time() < ping_end_time:
        if ping_vms_from_natbox(vm_ids=vm_id, fail_ok=True, con_ssh=con_ssh,
                                num_pings=3, use_fip=use_fip)[0]:
            # give it sometime to settle after vm booted and became pingable
            time.sleep(5)
            return True
    else:
        msg = "Ping from NatBox to vm {} failed for {} seconds.".format(vm_id,
                                                                        timeout)
        if fail_ok:
            LOG.warning(msg)
            return False
        else:
            time_stamp = common.get_date_in_format(ssh_client=con_ssh,
                                                   date_format='%Y%m%d_%H-%M')
            f_path = '{}/{}-{}'.format(ProjVar.get_var('PING_FAILURE_DIR'),
                                       time_stamp, ProjVar.get_var('TEST_NAME'))
            common.write_to_file(f_path,
                                 "=================={}===============\n".format(
                                     msg))
            ProjVar.set_var(PING_FAILURE=True)
            get_console_logs(vm_ids=vm_id, sep_file=f_path)
            network_helper.collect_networking_info(vms=vm_id, sep_file=f_path,
                                                   time_stamp=time_stamp)
            raise exceptions.VMNetworkError(msg)


def __merge_dict(base_dict, merge_dict):
    # identical to {**base_dict, **merge_dict} in python3.6+
    d = dict(base_dict)  # id() will be different, making a copy
    for k in merge_dict:
        d[k] = merge_dict[k]
    return d


def get_default_keypair(auth_info=None, con_ssh=None):
    """
    Get keypair for specific tenant.

    Args:
        auth_info (dict): If None, default tenant will be used.
        con_ssh (SSHClient):

    Returns (str): key name

    """
    if auth_info is None:
        auth_info = Tenant.get_primary()

    keypair_name = auth_info['nova_keypair']
    existing_keypairs = nova_helper.get_keypairs(name=keypair_name,
                                                 con_ssh=con_ssh,
                                                 auth_info=auth_info)
    if existing_keypairs:
        return existing_keypairs[0]

    # Assume that public key file already exists since it should have been
    # set up in session config.
    # In the case of public key file does not exist, there should be existing
    # nova keypair, so it should not
    # reach this step. Config done via setups.setup_keypair()
    keyfile_stx_final = ProjVar.get_var('STX_KEYFILE_SYS_HOME')
    public_key_stx = '{}.pub'.format(keyfile_stx_final)
    LOG.info("Create nova keypair {} using public key {}".format(
        keypair_name, public_key_stx))
    nova_helper.create_keypair(keypair_name, public_key=public_key_stx,
                               auth_info=auth_info, con_ssh=con_ssh)

    return keypair_name


def live_migrate_vm(vm_id, destination_host='', con_ssh=None,
                    block_migrate=None, force=None, fail_ok=False,
                    auth_info=Tenant.get('admin')):
    """

    Args:
        vm_id (str):
        destination_host (str): such as compute-0, compute-1
        con_ssh (SSHClient):
        block_migrate (bool): whether to add '--block-migrate' to command
        force (None|bool): force live migrate
        fail_ok (bool): if fail_ok, return a numerical number to indicate the
        execution status
                One exception is if the live-migration command exit_code > 1,
                which indicating the command itself may
                be incorrect. In this case CLICommandFailed exception will be
                thrown regardless of the fail_ok flag.
        auth_info (dict):

    Returns (tuple): (return_code (int), error_msg_if_migration_rejected (str))
        (0, 'Live migration is successful.'):
            live migration succeeded and post migration checking passed
        (1, <cli stderr>):  # This scenario is changed to host did not change
        as excepted
            live migration request rejected as expected. e.g., no available
            destination host,
            or live migrate a vm with block migration
        (2, <cli stderr>): live migration request rejected due to unknown
        reason.
        (3, 'Post action check failed: VM is in ERROR state.'):
            live migration command executed successfully, but VM is in Error
            state after migration
        (4, 'Post action check failed: VM is not in original state.'):
            live migration command executed successfully, but VM is not in
            before-migration-state
        (5, 'Post action check failed: VM host did not change!'):   (this
        scenario is removed from Newton)
            live migration command executed successfully, but VM is still on
            the same host after migration
        (6, <cli_stderr>) This happens when vote_note_to_migrate is set for
        vm, or pci device is used in vm, etc

    For the first two scenarios, results will be returned regardless of the
    fail_ok flag.
    For scenarios other than the first two, returns are only applicable if
    fail_ok=True

    Examples:
        1) If a test case is meant to test live migration with a specific
        flavor which would block the migration, the
        following call can be made:

         return_code, msg = live_migrate_vm(vm_id, fail_ok=True)
         expected_err_str = "your error string"
         assert return_code in [1, 2]
         assert expected_err_str in msg

        2) For a test that needs to live migrate

    """
    optional_arg = ''

    if block_migrate:
        optional_arg += '--block-migrate'

    if force:
        optional_arg += '--force'

    before_host = get_vm_host(vm_id, con_ssh=con_ssh)
    before_status = get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh,
                                  auth_info=Tenant.get('admin'))[0]
    if not before_status == VMStatus.ACTIVE:
        LOG.warning("Non-active VM status before live migrate: {}".format(
            before_status))

    extra_str = ''
    if not destination_host == '':
        extra_str = ' to ' + destination_host
    positional_args = ' '.join(
        [optional_arg.strip(), str(vm_id), destination_host]).strip()
    LOG.info(
        "Live migrating VM {} from {}{} started.".format(vm_id, before_host,
                                                         extra_str))
    LOG.info("nova live-migration {}".format(positional_args))
    # auto host/block migration selection unavailable in openstack client
    exit_code, output = cli.nova('live-migration',
                                 positional_args=positional_args,
                                 ssh_client=con_ssh, fail_ok=fail_ok,
                                 auth_info=auth_info)

    if exit_code == 1:
        return 6, output

    LOG.info("Waiting for VM status change to {} with best effort".format(
        VMStatus.MIGRATING))
    in_mig_state = wait_for_vm_status(vm_id, status=VMStatus.MIGRATING,
                                      timeout=60, fail_ok=True)
    if not in_mig_state:
        LOG.warning(
            "VM did not reach {} state after triggering live-migration".format(
                VMStatus.MIGRATING))

    LOG.info("Waiting for VM status change to original state {}".format(
        before_status))
    end_time = time.time() + VMTimeout.LIVE_MIGRATE_COMPLETE
    while time.time() < end_time:
        time.sleep(2)
        status = get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh,
                               auth_info=Tenant.get('admin'))[0]
        if status == before_status:
            LOG.info("Live migrate vm {} completed".format(vm_id))
            break
        elif status == VMStatus.ERROR:
            if fail_ok:
                return 3, "Post action check failed: VM is in ERROR state."
            nova_helper.get_migration_list_table(con_ssh=con_ssh,
                                                 auth_info=auth_info)
            raise exceptions.VMPostCheckFailed(
                "VM {} is in {} state after live migration. Original state "
                "before live migration is: {}".format(vm_id, VMStatus.ERROR,
                                                      before_status))
    else:
        if fail_ok:
            return 4, "Post action check failed: VM is not in original state."
        else:
            nova_helper.get_migration_list_table(con_ssh=con_ssh,
                                                 auth_info=auth_info)
            raise exceptions.TimeoutException(
                "VM {} did not reach original state within {} seconds after "
                "live migration".format(vm_id, VMTimeout.LIVE_MIGRATE_COMPLETE))

    after_host = before_host
    for i in range(3):
        after_host = get_vm_host(vm_id, con_ssh=con_ssh)
        if after_host != before_host:
            break
        time.sleep(3)

    if before_host == after_host:
        LOG.warning(
            "Live migration of vm {} failed. Checking if this is expected "
            "failure...".format(
                vm_id))
        if _is_live_migration_allowed(vm_id, vm_host=before_host,
                                      block_migrate=block_migrate) and \
                (destination_host or get_dest_host_for_live_migrate(vm_id)):
            if fail_ok:
                return 1, "Unknown live migration failure"
            else:
                nova_helper.get_migration_list_table(con_ssh=con_ssh,
                                                     auth_info=auth_info)
                raise exceptions.VMPostCheckFailed(
                    "Unexpected failure of live migration!")
        else:
            LOG.debug(
                "System does not allow live migrating vm {} as "
                "expected.".format(
                    vm_id))
            return 2, "Live migration failed as expected"

    LOG.info(
        "VM {} successfully migrated from {} to {}".format(vm_id, before_host,
                                                           after_host))
    return 0, "Live migration is successful."


def _is_live_migration_allowed(vm_id, vm_host, con_ssh=None,
                               block_migrate=None):
    vm_info = VMInfo.get_vm_info(vm_id, con_ssh=con_ssh)
    storage_backing = vm_info.get_storage_type()
    if not storage_backing:
        storage_backing = host_helper.get_host_instance_backing(host=vm_host,
                                                                con_ssh=con_ssh)

    vm_boot_from = vm_info.boot_info['type']

    if storage_backing == 'local_image':
        if block_migrate and vm_boot_from == 'volume' and not \
                vm_info.has_local_disks():
            LOG.warning(
                "Live block migration is not supported for boot-from-volume "
                "vm with local_image storage")
            return False
        return True

    elif storage_backing == 'local_lvm':
        if (not block_migrate) and vm_boot_from == 'volume' and not \
                vm_info.has_local_disks():
            return True
        else:
            LOG.warning(
                "Live (block) migration is not supported for local_lvm vm "
                "with localdisk")
            return False

    else:
        # remote backend
        if block_migrate:
            LOG.warning(
                "Live block migration is not supported for vm with remote "
                "storage")
            return False
        else:
            return True


def get_dest_host_for_live_migrate(vm_id, con_ssh=None):
    """
    Check whether a destination host exists with following criteria:
    Criteria:
        1) host has same storage backing as the vm
        2) host is unlocked
        3) different than current host
    Args:
        vm_id (str):
        con_ssh (SSHClient):

    Returns (str): hostname for the first host found. Or '' if no proper host
    found
    """
    vm_info = VMInfo.get_vm_info(vm_id, con_ssh=con_ssh)
    vm_storage_backing = vm_info.get_storage_type()
    current_host = vm_info.get_host_name()
    if not vm_storage_backing:
        vm_storage_backing = host_helper.get_host_instance_backing(
            host=current_host, con_ssh=con_ssh)
    candidate_hosts = host_helper.get_hosts_in_storage_backing(
        storage_backing=vm_storage_backing, con_ssh=con_ssh)

    hosts_table_ = table_parser.table(cli.system('host-list')[1])
    for host in candidate_hosts:
        if not host == current_host:
            host_state = table_parser.get_values(hosts_table_, 'administrative',
                                                 hostname=host)[0]
            if host_state == 'unlocked':
                LOG.debug(
                    "At least one host - {} is available for live migrating "
                    "vm {}".format(
                        host, vm_id))
                return host

    LOG.warning("No valid host found for live migrating vm {}".format(vm_id))
    return ''


def cold_migrate_vm(vm_id, revert=False, con_ssh=None, fail_ok=False,
                    auth_info=Tenant.get('admin')):
    """
    Cold migrate a vm and confirm/revert
    Args:
        vm_id (str): vm to cold migrate
        revert (bool): False to confirm resize, True to revert
        con_ssh (SSHClient):
        fail_ok (bool): True if fail ok. Default to False, ie., throws
            exception upon cold migration fail.
        auth_info (dict):

    Returns (tuple): (rtn_code, message)
        (0, success_msg) # Cold migration and confirm/revert succeeded. VM is
            back to original state or Active state.
        (1, <stderr>) # cold migration cli rejected
        # (2, <stderr>) # Cold migration cli command rejected. <stderr> is
            the err message returned by cli cmd.
        (3, <stdout>) # Cold migration cli accepted, but not finished.
            <stdout> is the output of cli cmd.
        (4, timeout_message] # Cold migration command ran successfully,
            but timed out waiting for VM to reach
            'Verify Resize' state or Error state.
        (5, err_msg) # Cold migration command ran successfully, but VM is in
            Error state.
        (6, err_msg) # Cold migration command ran successfully, and resize
            confirm/revert performed. But VM is not in
            Active state after confirm/revert.
        (7, err_msg) # Cold migration and resize confirm/revert ran
            successfully and vm in active state. But host for vm
            is not as expected. i.e., still the same host after confirm
            resize, or different host after revert resize.
        (8, <stderr>) # Confirm/Revert resize cli rejected

    """
    before_host = get_vm_host(vm_id, con_ssh=con_ssh)
    before_status = \
        get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh)[0]
    if not before_status == VMStatus.ACTIVE:
        LOG.warning("Non-active VM status before cold migrate: {}".format(
            before_status))

    LOG.info("Cold migrating VM {} from {}...".format(vm_id, before_host))
    exitcode, output = cli.nova('migrate --poll', vm_id, ssh_client=con_ssh,
                                fail_ok=fail_ok, auth_info=auth_info,
                                timeout=VMTimeout.COLD_MIGRATE_CONFIRM)

    if exitcode == 1:
        return 1, output

    LOG.info(
        "Waiting for VM status change to {}".format(VMStatus.VERIFY_RESIZE))
    vm_status = wait_for_vm_status(vm_id=vm_id,
                                   status=[VMStatus.VERIFY_RESIZE,
                                           VMStatus.ERROR],
                                   timeout=300,
                                   fail_ok=fail_ok, con_ssh=con_ssh)

    if vm_status is None:
        return 4, 'Timed out waiting for Error or Verify_Resize status for ' \
                  'VM {}'.format(vm_id)

    verify_resize_str = 'Revert' if revert else 'Confirm'
    if vm_status == VMStatus.VERIFY_RESIZE:
        LOG.info("{}ing resize..".format(verify_resize_str))
        res, out = _confirm_or_revert_resize(vm=vm_id, revert=revert,
                                             fail_ok=fail_ok, con_ssh=con_ssh)
        if res > 0:
            return 8, out

    elif vm_status == VMStatus.ERROR:
        err_msg = "VM {} in Error state after cold migrate. {} resize is not " \
                  "reached.".format(vm_id, verify_resize_str)
        if fail_ok:
            return 5, err_msg
        nova_helper.get_migration_list_table(con_ssh=con_ssh,
                                             auth_info=auth_info)
        raise exceptions.VMPostCheckFailed(err_msg)

    post_confirm_state = wait_for_vm_status(
        vm_id, status=VMStatus.ACTIVE,
        timeout=VMTimeout.COLD_MIGRATE_CONFIRM, fail_ok=fail_ok,
        con_ssh=con_ssh)

    if post_confirm_state is None:
        err_msg = "VM {} is not in Active state after {} Resize".format(
            vm_id, verify_resize_str)
        return 6, err_msg

    # Process results
    after_host = get_vm_host(vm_id, con_ssh=con_ssh)
    host_changed = before_host != after_host
    host_change_str = "changed" if host_changed else "did not change"
    operation_ok = not host_changed if revert else host_changed

    if not operation_ok:
        err_msg = (
            "VM {} host {} after {} Resize. Before host: {}. After host: {}".
            format(vm_id, host_change_str, verify_resize_str, before_host,
                   after_host))
        if fail_ok:
            return 7, err_msg
        nova_helper.get_migration_list_table(con_ssh=con_ssh,
                                             auth_info=auth_info)
        raise exceptions.VMPostCheckFailed(err_msg)

    success_msg = "VM {} successfully cold migrated and {}ed Resize.".format(
        vm_id, verify_resize_str)
    LOG.info(success_msg)
    return 0, success_msg


def resize_vm(vm_id, flavor_id, revert=False, con_ssh=None, fail_ok=False,
              auth_info=Tenant.get('admin')):
    """
    Resize vm to given flavor

    Args:
        vm_id (str):
        flavor_id (str): flavor to resize to
        revert (bool): True to revert resize, else confirm resize
        con_ssh (SSHClient):
        fail_ok (bool):
        auth_info (dict):

    Returns (tuple): (rtn_code, msg)
        (0, "VM <vm_id> successfully resized and confirmed/reverted.")
        (1, <std_err>)  # resize cli rejected
        (2, "Timed out waiting for Error or Verify_Resize status for VM
            <vm_id>")
        (3, "VM <vm_id> in Error state after resizing. VERIFY_RESIZE is not
            reached.")
        (4, "VM <vm_id> is not in Active state after confirm/revert Resize")
        (5, "Flavor is changed after revert resizing.")
        (6, "VM flavor is not changed to expected after resizing.")
    """
    before_flavor = get_vm_flavor(vm_id, con_ssh=con_ssh)
    before_status = \
        get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh)[0]
    if not before_status == VMStatus.ACTIVE:
        LOG.warning("Non-active VM status before cold migrate: {}".format(
            before_status))

    LOG.info("Resizing VM {} to flavor {}...".format(vm_id, flavor_id))
    args = '--wait --flavor {} {}'.format(flavor_id, vm_id)
    exitcode, output = cli.openstack('server resize', args, ssh_client=con_ssh,
                                     fail_ok=fail_ok, auth_info=auth_info,
                                     timeout=VMTimeout.COLD_MIGRATE_CONFIRM)
    if exitcode > 0:
        return 1, output

    LOG.info(
        "Waiting for VM status change to {}".format(VMStatus.VERIFY_RESIZE))
    vm_status = wait_for_vm_status(vm_id=vm_id,
                                   status=[VMStatus.VERIFY_RESIZE,
                                           VMStatus.ERROR],
                                   fail_ok=fail_ok,
                                   timeout=300, con_ssh=con_ssh)

    if vm_status is None:
        err_msg = 'Timed out waiting for Error or Verify_Resize status for ' \
                  'VM {}'.format(vm_id)
        LOG.error(err_msg)
        return 2, err_msg

    verify_resize_str = 'Revert' if revert else 'Confirm'
    if vm_status == VMStatus.VERIFY_RESIZE:
        LOG.info("{}ing resize..".format(verify_resize_str))
        _confirm_or_revert_resize(vm=vm_id, revert=revert, con_ssh=con_ssh)

    elif vm_status == VMStatus.ERROR:
        err_msg = "VM {} in Error state after resizing. {} is not " \
                  "reached.".format(vm_id, VMStatus.VERIFY_RESIZE)
        if fail_ok:
            LOG.error(err_msg)
            return 3, err_msg
        raise exceptions.VMPostCheckFailed(err_msg)

    post_confirm_state = wait_for_vm_status(
        vm_id, status=VMStatus.ACTIVE, timeout=VMTimeout.COLD_MIGRATE_CONFIRM,
        fail_ok=fail_ok, con_ssh=con_ssh)

    if post_confirm_state is None:
        err_msg = "VM {} is not in Active state after {} Resize".format(
            vm_id, verify_resize_str)
        LOG.error(err_msg)
        return 4, err_msg

    after_flavor = get_vm_flavor(vm_id)
    if revert and after_flavor != before_flavor:
        err_msg = "Flavor is changed after revert resizing. Before flavor: " \
                  "{}, after flavor: {}".format(before_flavor, after_flavor)
        if fail_ok:
            LOG.error(err_msg)
            return 5, err_msg
        raise exceptions.VMPostCheckFailed(err_msg)

    if not revert and after_flavor != flavor_id:
        err_msg = "VM flavor {} is not changed to expected after resizing. " \
                  "Before flavor: {}, after flavor: {}".\
            format(flavor_id, before_flavor, after_flavor)
        if fail_ok:
            LOG.error(err_msg)
            return 6, err_msg
        raise exceptions.VMPostCheckFailed(err_msg)

    success_msg = "VM {} successfully resized and {}ed.".format(
        vm_id, verify_resize_str)
    LOG.info(success_msg)
    return 0, success_msg


def wait_for_vm_values(vm_id, timeout=VMTimeout.STATUS_CHANGE, check_interval=3,
                       fail_ok=True, strict=True,
                       regex=False, con_ssh=None, auth_info=None, **kwargs):
    """
    Wait for vm to reach given states.

    Args:
        vm_id (str): vm id
        timeout (int): in seconds
        check_interval (int): in seconds
        fail_ok (bool): whether to return result or raise exception when vm
        did not reach expected value(s).
        strict (bool): whether to perform strict search(match) for the value(s)
            For regular string: if True, match the whole string; if False,
            find any substring match
            For regex: if True, match from start of the value string; if
            False, search anywhere of the value string
        regex (bool): whether to use regex to find matching value(s)
        con_ssh (SSHClient):
        auth_info (dict):
        **kwargs: field/value pair(s) to identify the waiting criteria.

    Returns (tuple): (result(bool), actual_vals(dict))

    """
    if not kwargs:
        raise ValueError("No field/value pair is passed via kwargs")
    LOG.info("Waiting for vm to reach state(s): {}".format(kwargs))

    fields_to_check = list(kwargs.keys())
    results = {}
    end_time = time.time() + timeout
    while time.time() < end_time:
        actual_vals = get_vm_values(vm_id=vm_id, con_ssh=con_ssh,
                                    auth_info=auth_info,
                                    fields=fields_to_check)
        for i in range(len(fields_to_check)):
            field = fields_to_check[i]
            expt_vals = kwargs[field]
            actual_val = actual_vals[i]
            results[field] = actual_val
            if not isinstance(expt_vals, list):
                expt_vals = [expt_vals]
            for expt_val in expt_vals:
                if regex:
                    match_found = re.match(expt_val,
                                           actual_val) if strict else re.search(
                        expt_val, actual_val)
                else:
                    match_found = expt_val == actual_val if strict else \
                        expt_val in actual_val

                if match_found:
                    fields_to_check.remove(field)

                if not fields_to_check:
                    LOG.info("VM has reached states: {}".format(results))
                    return True, results

        time.sleep(check_interval)

    msg = "VM {} did not reach expected states within timeout. Actual state(" \
          "s): {}".format(vm_id, results)
    if fail_ok:
        LOG.warning(msg)
        return False, results
    else:
        raise exceptions.VMTimeout(msg)


def wait_for_vm_status(vm_id, status=VMStatus.ACTIVE,
                       timeout=VMTimeout.STATUS_CHANGE, check_interval=3,
                       fail_ok=False,
                       con_ssh=None, auth_info=Tenant.get('admin')):
    """

    Args:
        vm_id:
        status (list|str):
        timeout:
        check_interval:
        fail_ok (bool):
        con_ssh:
        auth_info:

    Returns: The Status of the vm_id depend on what Status it is looking for

    """
    end_time = time.time() + timeout
    if isinstance(status, str):
        status = [status]

    current_status = get_vm_values(vm_id, 'status', strict=True,
                                   con_ssh=con_ssh, auth_info=auth_info)[0]
    while time.time() < end_time:
        for expected_status in status:
            if current_status == expected_status:
                LOG.info("VM status has reached {}".format(expected_status))
                return expected_status

        time.sleep(check_interval)
        current_status = get_vm_values(vm_id, 'status', strict=True,
                                       con_ssh=con_ssh, auth_info=auth_info)[0]

    err_msg = "Timed out waiting for vm status: {}. Actual vm status: " \
              "{}".format(status, current_status)
    if fail_ok:
        LOG.warning(err_msg)
        return None
    else:
        raise exceptions.VMTimeout(err_msg)


def _confirm_or_revert_resize(vm, revert=False, con_ssh=None, fail_ok=False):
    args = '--revert' if revert else '--confirm'
    args = '{} {}'.format(args, vm)
    return cli.openstack('server resize', args, ssh_client=con_ssh,
                         fail_ok=fail_ok, auth_info=Tenant.get('admin'))


def _get_vms_ips(vm_ids, net_types='mgmt', exclude_nets=None, con_ssh=None,
                 vshell=False):
    if isinstance(net_types, str):
        net_types = [net_types]

    if isinstance(vm_ids, str):
        vm_ids = [vm_ids]

    valid_net_types = ['mgmt', 'data', 'internal', 'external']
    if not set(net_types) <= set(valid_net_types):
        raise ValueError(
            "Invalid net type(s) provided. Valid net_types: {}. net_types "
            "given: {}".
            format(valid_net_types, net_types))

    vms_ips = []
    vshell_ips_dict = dict(data=[], internal=[])
    if 'mgmt' in net_types:
        mgmt_ips = network_helper.get_mgmt_ips_for_vms(
            vms=vm_ids, con_ssh=con_ssh, exclude_nets=exclude_nets)
        if not mgmt_ips:
            raise exceptions.VMNetworkError(
                "Management net ip is not found for vms {}".format(vm_ids))
        vms_ips += mgmt_ips

    if 'external' in net_types:
        ext_ips = network_helper.get_external_ips_for_vms(
            vms=vm_ids, con_ssh=con_ssh, exclude_nets=exclude_nets)
        if not ext_ips:
            raise exceptions.VMNetworkError(
                "No external network ip found for vms {}".format(vm_ids))
        vms_ips += ext_ips

    if 'data' in net_types:
        data_ips = network_helper.get_tenant_ips_for_vms(
            vms=vm_ids, con_ssh=con_ssh, exclude_nets=exclude_nets)
        if not data_ips:
            raise exceptions.VMNetworkError(
                "Data network ip is not found for vms {}".format(vm_ids))
        if vshell:
            vshell_ips_dict['data'] = data_ips
        else:
            vms_ips += data_ips

    if 'internal' in net_types:
        internal_ips = network_helper.get_internal_ips_for_vms(
            vms=vm_ids, con_ssh=con_ssh, exclude_nets=exclude_nets)
        if not internal_ips:
            raise exceptions.VMNetworkError(
                "Internal net ip is not found for vms {}".format(vm_ids))
        if vshell:
            vshell_ips_dict['internal'] = internal_ips
        else:
            vms_ips += internal_ips

    return vms_ips, vshell_ips_dict


def _ping_vms(ssh_client, vm_ids=None, con_ssh=None, num_pings=5, timeout=15,
              fail_ok=False, net_types='mgmt', retry=3,
              retry_interval=3, vshell=False, sep_file=None,
              source_net_types=None):
    """

    Args:
        vm_ids (list|str): list of vms to ping
        ssh_client (SSHClient): ping from this ssh client. Usually a natbox'
        ssh client or another vm's ssh client
        con_ssh (SSHClient): active controller ssh client to run cli command
            to get all the management ips
        num_pings (int): number of pings to send
        timeout (int): timeout waiting for response of ping messages in seconds
        fail_ok (bool): Whether it's okay to have 100% packet loss rate.
        sep_file (str|None)
        net_types (str|list|tuple)
        source_net_types (str|list|tuple|None):
            vshell specific
            None:   use the same net_type s as the target IPs'
            str:    use the specified net_type for all target IPs
            tuple:  (net_type_data, net_type_internal)
                use net_type_data for data IPs
                use net_type_internal for internal IPs
            list:   same as tuple

    Returns (tuple): (res (bool), packet_loss_dict (dict))
        Packet loss rate dictionary format:
        {
         ip1: packet_loss_percentile1,
         ip2: packet_loss_percentile2,
         ...
        }

    """
    vms_ips, vshell_ips_dict = _get_vms_ips(vm_ids=vm_ids, net_types=net_types,
                                            con_ssh=con_ssh, vshell=vshell)

    res_bool = False
    res_dict = {}
    for i in range(retry + 1):
        for ip in vms_ips:
            packet_loss_rate = network_helper.ping_server(
                server=ip, ssh_client=ssh_client, num_pings=num_pings,
                timeout=timeout, fail_ok=True, vshell=False)[0]
            res_dict[ip] = packet_loss_rate

        for net_type, vshell_ips in vshell_ips_dict.items():

            if source_net_types is None:
                pass
            elif isinstance(source_net_types, str):
                net_type = source_net_types
            else:
                net_type_data, net_type_internal = source_net_types
                if net_type == 'data':
                    net_type = net_type_data
                elif net_type == 'internal':
                    net_type = net_type_internal
                else:
                    raise ValueError(net_type)

            for vshell_ip in vshell_ips:
                packet_loss_rate = network_helper.ping_server(
                    server=vshell_ip, ssh_client=ssh_client,
                    num_pings=num_pings, timeout=timeout, fail_ok=True,
                    vshell=True, net_type=net_type)[0]
                res_dict[vshell_ip] = packet_loss_rate

        res_bool = not any(loss_rate == 100 for loss_rate in res_dict.values())
        if res_bool:
            LOG.info(
                "Ping successful from {}: {}".format(ssh_client.host, res_dict))
            return res_bool, res_dict

        if i < retry:
            LOG.info("Retry in {} seconds".format(retry_interval))
            time.sleep(retry_interval)

    if not res_dict:
        raise ValueError("Ping res dict contains no result.")

    err_msg = "Ping unsuccessful from vm (logged in via {}): {}".format(
        ssh_client.host, res_dict)
    if fail_ok:
        LOG.info(err_msg)
        return res_bool, res_dict
    else:
        if sep_file:
            msg = "==========================Ping unsuccessful from vm to " \
                  "vms===================="
            common.write_to_file(
                sep_file,
                content="{}\nLogged into vm via {}. Result: {}".format(
                    msg, ssh_client.host, res_dict))
        raise exceptions.VMNetworkError(err_msg)


def configure_vm_vifs_on_same_net(vm_id, vm_ips=None, ports=None,
                                  vm_prompt=None, restart_service=True,
                                  reboot=False):
    """
    Configure vm routes if the vm has multiple vifs on same network.
    Args:
        vm_id (str):
        vm_ips (str|list): ips for specific vifs. Only works if vifs are up
        with ips assigned
        ports (list of dict): vm ports to configure.
        vm_prompt (None|str)
        restart_service
        reboot

    Returns:

    """

    if isinstance(vm_ips, str):
        vm_ips = [vm_ips]

    vnics_info = {}
    if ports:
        LOG.info("Get vm interfaces' mac and ip addressess")
        if isinstance(ports, str):
            ports = [ports]
        vm_interfaces_table = table_parser.table(
            cli.openstack('port list', '--server {}'.format(vm_id))[1])
        vm_interfaces_dict = table_parser.row_dict_table(
            table_=vm_interfaces_table, key_header='ID')
        for i in range(len(ports)):
            port_id = ports[i]
            vif_info = vm_interfaces_dict[port_id]
            vif_ip = vif_info['fixed ip addresses']
            if vif_ip and 'ip_address' in vif_ip:
                vif_ip = \
                    re.findall("ip_address='(.*)'", vif_ip.split(sep=',')[0])[0]
            else:
                if not vm_ips:
                    raise ValueError(
                        "vm_ips for matching vnics has to be provided for "
                        "ports without ip address "
                        "listed in neutron port-list")
                vif_ip = vm_ips[i]
            cidr = vif_ip.rsplit('.', maxsplit=1)[0] + '.0/24'
            vif_mac = vif_info['mac address']
            vnics_info[vif_mac] = (cidr, vif_ip)

    LOG.info("Configure vm routes if the vm has multiple vifs on same network.")
    with ssh_to_vm_from_natbox(vm_id=vm_id, prompt=vm_prompt) as vm_ssh:
        vifs_to_conf = {}
        if not ports:
            extra_grep = '| grep --color=never -E "{}"'.format(
                '|'.join(vm_ips)) if vm_ips else ''
            kernel_routes = vm_ssh.exec_cmd(
                'ip route | grep --color=never "proto kernel" {}'.format(
                    extra_grep))[1]
            cidr_dict = {}
            for line in kernel_routes.splitlines():
                found = re.findall(
                    r'^(.*/\d+)\sdev\s(.*)\sproto kernel.*\ssrc\s(.*)$', line)
                cidr, dev_name, dev_ip = found[0]
                if cidr not in cidr_dict:
                    cidr_dict[cidr] = []
                cidr_dict[cidr].append((dev_name, dev_ip))

            for cidr_, val in cidr_dict.items():
                if not vm_ips:
                    val = val[1:]
                for eth_info in val:
                    dev_name, dev_ip = eth_info
                    vifs_to_conf[dev_name] = \
                        (cidr_, dev_ip, 'stxauto_{}'.format(dev_name))

            if not vifs_to_conf:
                LOG.info(
                    "Did not find multiple vifs on same subnet. Do nothing.")

        else:
            for mac_addr in vnics_info:
                dev_name = network_helper.get_eth_for_mac(vm_ssh,
                                                          mac_addr=mac_addr)
                cidr_, dev_ip = vnics_info[mac_addr]
                vifs_to_conf[dev_name] = (
                    cidr_, dev_ip, 'stxauto_{}'.format(dev_name))

        used_tables = vm_ssh.exec_cmd(
            'grep --color=never -E "^[0-9]" {}'.format(VMPath.RT_TABLES))[1]
        used_tables = [int(re.split(r'[\s\t]', line_)[0].strip()) for line_ in
                       used_tables.splitlines()]

        start_range = 110
        for eth_name, eth_info in vifs_to_conf.items():
            cidr_, vif_ip, table_name = eth_info
            exiting_tab = vm_ssh.exec_cmd(
                'grep --color=never {} {}'.format(table_name,
                                                  VMPath.RT_TABLES))[1]
            if not exiting_tab:
                for i in range(start_range, 250):
                    if i not in used_tables:
                        LOG.info(
                            "Append new routing table {} to rt_tables".
                            format(table_name))
                        vm_ssh.exec_sudo_cmd(
                            'echo "{} {}" >> {}'.format(i, table_name,
                                                        VMPath.RT_TABLES))
                        start_range = i + 1
                        break
                else:
                    raise ValueError(
                        "Unable to get a valid table number to create route "
                        "for {}".format(eth_name))

            LOG.info(
                "Update arp_filter, arp_announce, route and rule scripts for "
                "vm {} {}".format(vm_id, eth_name))
            vm_ssh.exec_sudo_cmd(
                'echo 2 > {}'.format(VMPath.ETH_ARP_ANNOUNCE.format(eth_name)))
            vm_ssh.exec_sudo_cmd(
                'echo 1 > {}'.format(VMPath.ETH_ARP_FILTER.format(eth_name)))
            route = '{} dev {} proto kernel scope link src {} table {}'.format(
                cidr_, eth_name, vif_ip, table_name)
            vm_ssh.exec_sudo_cmd('echo "{}" > {}'.format(
                route, VMPath.ETH_RT_SCRIPT.format(eth_name)))
            rule = 'table {} from {}'.format(table_name, vif_ip)
            vm_ssh.exec_sudo_cmd('echo "{}" > {}'.format(
                rule, VMPath.ETH_RULE_SCRIPT.format(eth_name)))

        if restart_service and not reboot:
            LOG.info("Restart network service after configure vm routes")
            vm_ssh.exec_sudo_cmd('systemctl restart network',
                                 expect_timeout=120, get_exit_code=False)
            # vm_ssh.exec_cmd('ip addr')

    if reboot:
        LOG.info("Reboot vm after configure vm routes")
        reboot_vm(vm_id=vm_id)


def cleanup_routes_for_vifs(vm_id, vm_ips, rm_ifcfg=True, restart_service=True,
                            reboot=False):
    """
    Cleanup the configured routes for specified vif(s). This is needed when a
    vif is detached from a vm.

    Args:
        vm_id:
        vm_ips:
        rm_ifcfg
        restart_service
        reboot

    Returns:

    """
    with ssh_to_vm_from_natbox(vm_id=vm_id) as vm_ssh:

        if isinstance(vm_ips, str):
            vm_ips = [vm_ips]

        for vm_ip in vm_ips:
            LOG.info("Clean up route for dev with ip {}".format(vm_ip))
            route = vm_ssh.exec_sudo_cmd(
                'grep --color=never {} {}'.format(
                    vm_ip, VMPath.ETH_RT_SCRIPT.format('*')))[1]
            if not route:
                continue

            pattern = '(.*) dev (.*) proto kernel .* src {} table (.*)'.format(
                vm_ip)
            found = re.findall(pattern, route)
            if found:
                cidr, eth_name, table_name = found[0]
                LOG.info(
                    "Update arp_filter, arp_announce, route and rule scripts "
                    "for vm {} {}".format(vm_id, eth_name))
                # vm_ssh.exec_sudo_cmd('rm -f {}'.format(
                # VMPath.ETH_ARP_ANNOUNCE.format(eth_name)))
                # vm_ssh.exec_sudo_cmd('rm -f {}'.format(
                # VMPath.ETH_ARP_FILTER.format(eth_name)))
                vm_ssh.exec_sudo_cmd(
                    'rm -f {}'.format(VMPath.ETH_RULE_SCRIPT.format(eth_name)))
                vm_ssh.exec_sudo_cmd(
                    'rm -f {}'.format(VMPath.ETH_RT_SCRIPT.format(eth_name)))
                vm_ssh.exec_sudo_cmd("sed -n -i '/{}/!p' {}".format(
                    table_name, VMPath.RT_TABLES))

                if rm_ifcfg:
                    vm_ssh.exec_sudo_cmd('rm -f {}'.format(
                        VMPath.ETH_PATH_CENTOS.format(eth_name)))

        if restart_service and not reboot:
            LOG.info("Restart network service")
            vm_ssh.exec_sudo_cmd('systemctl restart network',
                                 get_exit_code=False, expect_timeout=60)

    if reboot:
        reboot_vm(vm_id=vm_id)


def ping_vms_from_natbox(vm_ids=None, natbox_client=None, con_ssh=None,
                         num_pings=5, timeout=30, fail_ok=False,
                         use_fip=False, retry=0):
    """

    Args:
        vm_ids: vms to ping. If None, all vms will be ping'd.
        con_ssh (SSHClient): active controller client to retrieve the vm info
        natbox_client (NATBoxClient): ping vms from this client
        num_pings (int): number of pings to send
        timeout (int): timeout waiting for response of ping messages in seconds
        fail_ok (bool): When False, test will stop right away if one ping
        failed. When True, test will continue to ping
            the rest of the vms and return results even if pinging one vm
            failed.
        use_fip (bool): Whether to ping floating ip only if a vm has more
        than one management ips
        retry (int): number of times to retry if ping fails

    Returns (tuple): (res (bool), packet_loss_dict (dict))
        Packet loss rate dictionary format:
        {
         ip1: packet_loss_percentile1,
         ip2: packet_loss_percentile2,
         ...
        }
    """
    if isinstance(vm_ids, str):
        vm_ids = [vm_ids]

    if not natbox_client:
        natbox_client = NATBoxClient.get_natbox_client()

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    net_type = 'external' if use_fip else 'mgmt'
    res_bool, res_dict = _ping_vms(ssh_client=natbox_client, vm_ids=vm_ids,
                                   con_ssh=con_ssh, num_pings=num_pings,
                                   timeout=timeout, fail_ok=True,
                                   net_types=net_type, retry=retry,
                                   vshell=False)
    if not res_bool and not fail_ok:
        msg = "==================Ping vm(s) from NatBox failed - Collecting " \
              "extra information==============="
        LOG.error(msg)
        time_stamp = common.get_date_in_format(ssh_client=con_ssh,
                                               date_format='%Y%m%d_%H-%M')
        f_path = '{}/{}-{}'.format(ProjVar.get_var('PING_FAILURE_DIR'),
                                   time_stamp, ProjVar.get_var("TEST_NAME"))
        common.write_to_file(file_path=f_path,
                             content="\n{}\nResult(s): {}\n".format(msg,
                                                                    res_dict))
        ProjVar.set_var(PING_FAILURE=True)
        get_console_logs(vm_ids=vm_ids, sep_file=f_path)
        network_helper.collect_networking_info(vms=vm_ids, sep_file=f_path,
                                               time_stamp=time_stamp,
                                               con_ssh=con_ssh)
        raise exceptions.VMNetworkError(
            "Ping failed from NatBox. Details: {}".format(res_dict))

    return res_bool, res_dict


def get_console_logs(vm_ids, length=None, con_ssh=None, sep_file=None):
    """
    Get console logs for given vm(s)
    Args:
        vm_ids (str|list):
        length (int|None): how many lines to tail
        con_ssh:
        sep_file (str|None): write vm console logs to given sep_file if
            specified.

    Returns (dict): {<vm1_id>: <vm1_console>, <vm2_id>: <vm2_console>, ...}
    """
    if isinstance(vm_ids, str):
        vm_ids = [vm_ids]

    vm_ids = list(set(vm_ids))
    console_logs = {}
    args = '--lines={} '.format(length) if length else ''
    content = ''
    for vm_id in vm_ids:
        vm_args = '{}{}'.format(args, vm_id)
        output = cli.openstack('console log show', vm_args, ssh_client=con_ssh,
                               auth_info=Tenant.get('admin'))[1]
        console_logs[vm_id] = output
        content += "\n#### Console log for vm {} ####\n{}\n".format(vm_id,
                                                                    output)

    if sep_file:
        common.write_to_file(sep_file, content=content)

    return console_logs


def ping_vms_from_vm(to_vms=None, from_vm=None, user=None, password=None,
                     prompt=None, con_ssh=None, natbox_client=None,
                     num_pings=5, timeout=120, fail_ok=False, from_vm_ip=None,
                     from_fip=False, net_types='mgmt',
                     retry=3, retry_interval=5, vshell=False,
                     source_net_types=None):
    """

    Args:
        from_vm (str):
        to_vms (str|list|None):
        user (str):
        password (str):
        prompt (str):
        con_ssh (SSHClient):
        natbox_client (SSHClient):
        num_pings (int):
        timeout (int): max number of seconds to wait for ssh connection to
            from_vm
        fail_ok (bool):  When False, test will stop right away if one ping
            failed. When True, test will continue to ping
            the rest of the vms and return results even if pinging one vm
            failed.
        from_vm_ip (str): vm ip to ssh to if given. from_fip flag will be
            considered only if from_vm_ip=None
        from_fip (bool): whether to ssh to vm's floating ip if it has
            floating ip associated with it
        net_types (list|str|tuple): 'mgmt', 'data', or 'internal'
        retry (int): number of times to retry
        retry_interval (int): seconds to wait between each retries
        vshell (bool): whether to ping vms' data interface through internal
            interface.
            Usage: when set to True, use 'vshell ping --count 3
            <other_vm_data_ip> <internal_if_id>'
                - dpdk vms should be booted from lab_setup scripts
        source_net_types (str|list|tuple|None):
            vshell specific
            None:   use the same net_type s as the target IPs'
            str:    use the specified net_type for all target IPs
            tuple:  (net_type_data, net_type_internal)
                use net_type_data for data IPs
                use net_type_internal for internal IPs
            list:   same as tuple

    Returns (tuple):
        A tuple in form: (res (bool), packet_loss_dict (dict))

        Packet loss rate dictionary format:
        {
         ip1: packet_loss_percentile1,
         ip2: packet_loss_percentile2,
         ...
        }

    """
    if isinstance(net_types, str):
        net_types = [net_types]

    if from_vm is None or to_vms is None:
        vms_ips = network_helper.get_mgmt_ips_for_vms(con_ssh=con_ssh,
                                                      rtn_dict=True)
        if not vms_ips:
            raise exceptions.NeutronError("No management ip found for any vms")

        vms_ids = list(vms_ips.keys())
        if from_vm is None:
            from_vm = random.choice(vms_ids)
        if to_vms is None:
            to_vms = vms_ids

    if isinstance(to_vms, str):
        to_vms = [to_vms]

    if not isinstance(from_vm, str):
        raise ValueError("from_vm is not a string: {}".format(from_vm))

    assert from_vm and to_vms, "from_vm: {}, to_vms: {}".format(from_vm, to_vms)

    time_stamp = common.get_date_in_format(ssh_client=con_ssh,
                                           date_format='%Y%m%d_%H-%M')
    f_path = '{}/{}-{}'.format(ProjVar.get_var('PING_FAILURE_DIR'), time_stamp,
                               ProjVar.get_var('TEST_NAME'))
    try:
        with ssh_to_vm_from_natbox(vm_id=from_vm, username=user,
                                   password=password,
                                   natbox_client=natbox_client,
                                   prompt=prompt, con_ssh=con_ssh,
                                   vm_ip=from_vm_ip, use_fip=from_fip,
                                   retry_timeout=300) as from_vm_ssh:
            res = _ping_vms(ssh_client=from_vm_ssh, vm_ids=to_vms,
                            con_ssh=con_ssh, num_pings=num_pings,
                            timeout=timeout, fail_ok=fail_ok,
                            net_types=net_types, retry=retry,
                            retry_interval=retry_interval, vshell=vshell,
                            sep_file=f_path,
                            source_net_types=source_net_types)
            return res

    except (exceptions.TiSError, pexpect.ExceptionPexpect):
        ProjVar.set_var(PING_FAILURE=True)
        collect_to_vms = False if list(to_vms) == [from_vm] else True
        get_console_logs(vm_ids=from_vm, length=20, sep_file=f_path)
        if collect_to_vms:
            get_console_logs(vm_ids=to_vms, sep_file=f_path)
        network_helper.collect_networking_info(vms=to_vms, sep_file=f_path,
                                               time_stamp=time_stamp)
        try:
            LOG.warning(
                "Ping vm(s) from vm failed - Attempt to ssh to from_vm and "
                "collect vm networking info")
            with ssh_to_vm_from_natbox(vm_id=from_vm, username=user,
                                       password=password,
                                       natbox_client=natbox_client,
                                       prompt=prompt, con_ssh=con_ssh,
                                       vm_ip=from_vm_ip,
                                       use_fip=from_fip) as from_vm_ssh:
                _collect_vm_networking_info(vm_ssh=from_vm_ssh, sep_file=f_path,
                                            vm_id=from_vm)

            if collect_to_vms:
                LOG.warning(
                    "Ping vm(s) from vm failed - Attempt to ssh to to_vms and "
                    "collect vm networking info")
                for vm_ in to_vms:
                    with ssh_to_vm_from_natbox(vm_, retry=False,
                                               con_ssh=con_ssh) as to_ssh:
                        _collect_vm_networking_info(to_ssh, sep_file=f_path,
                                                    vm_id=vm_)
        except (exceptions.TiSError, pexpect.ExceptionPexpect):
            pass

        raise


def _collect_vm_networking_info(vm_ssh, sep_file=None, vm_id=None):
    vm = vm_id if vm_id else ''
    content = '#### VM network info collected when logged into vm {}via {} ' \
              '####'.format(vm, vm_ssh.host)
    for cmd in ('ip addr', 'ip neigh', 'ip route'):
        output = vm_ssh.exec_cmd(cmd, get_exit_code=False)[1]
        content += '\nSent: {}\nOutput:\n{}\n'.format(cmd, output)

    if sep_file:
        common.write_to_file(sep_file, content=content)


def ping_ext_from_vm(from_vm, ext_ip=None, user=None, password=None,
                     prompt=None, con_ssh=None, natbox_client=None,
                     num_pings=5, timeout=30, fail_ok=False, vm_ip=None,
                     use_fip=False):
    if ext_ip is None:
        ext_ip = EXT_IP

    with ssh_to_vm_from_natbox(vm_id=from_vm, username=user, password=password,
                               natbox_client=natbox_client,
                               prompt=prompt, con_ssh=con_ssh, vm_ip=vm_ip,
                               use_fip=use_fip) as from_vm_ssh:
        from_vm_ssh.exec_cmd('ip addr', get_exit_code=False)
        return network_helper.ping_server(ext_ip, ssh_client=from_vm_ssh,
                                          num_pings=num_pings,
                                          timeout=timeout, fail_ok=fail_ok)[0]


def scp_to_vm_from_natbox(vm_id, source_file, dest_file, timeout=60,
                          validate=True, natbox_client=None, sha1sum=None):
    """
    scp a file to a vm from natbox
    the file must be located in the natbox
    the natbox must has connectivity to the VM

    Args:
        vm_id (str): vm to scp to
        source_file (str): full pathname to the source file
        dest_file (str): destination full pathname in the VM
        timeout (int): scp timeout
        validate (bool): verify src and dest sha1sum
        natbox_client (NATBoxClient|None):
        sha1sum (str|None): validates the source file prior to operation,
        or None, only checked if validate=True

    Returns (None):

    """
    if natbox_client is None:
        natbox_client = NATBoxClient.get_natbox_client()

    LOG.info("scp-ing from {} to VM {}".format(natbox_client.host, vm_id))

    tmp_loc = '/tmp'
    fname = os.path.basename(os.path.normpath(source_file))

    # ensure source file exists
    natbox_client.exec_cmd('test -f {}'.format(source_file), fail_ok=False)

    # calculate sha1sum
    src_sha1 = None
    if validate:
        src_sha1 = natbox_client.exec_cmd('sha1sum {}'.format(source_file),
                                          fail_ok=False)[1]
        src_sha1 = src_sha1.split(' ')[0]
        LOG.info("src: {}, sha1sum: {}".format(source_file, src_sha1))
        if sha1sum is not None and src_sha1 != sha1sum:
            raise ValueError(
                "src sha1sum validation failed {} != {}".format(src_sha1,
                                                                sha1sum))

    with ssh_to_vm_from_natbox(vm_id) as vm_ssh:
        vm_ssh.exec_cmd('mkdir -p {}'.format(tmp_loc))
        vm_ssh.scp_on_dest(natbox_client.user, natbox_client.host, source_file,
                           '/'.join([tmp_loc, fname]), natbox_client.password,
                           timeout=timeout)

        # `mv $s $d` fails if $s == $d
        if os.path.normpath(os.path.join(tmp_loc, fname)) != os.path.normpath(
                dest_file):
            vm_ssh.exec_sudo_cmd(
                'mv -f {} {}'.format('/'.join([tmp_loc, fname]), dest_file),
                fail_ok=False)

        # ensure destination file exists
        vm_ssh.exec_sudo_cmd('test -f {}'.format(dest_file), fail_ok=False)

        # validation
        if validate:
            dest_sha1 = vm_ssh.exec_sudo_cmd(
                'sha1sum {}'.format(dest_file), fail_ok=False)[1]
            dest_sha1 = dest_sha1.split(' ')[0]
            LOG.info("dst: {}, sha1sum: {}".format(dest_file, dest_sha1))
            if src_sha1 != dest_sha1:
                raise ValueError(
                    "dst sha1sum validation failed {} != {}".format(src_sha1,
                                                                    dest_sha1))
            LOG.info("scp completed successfully")


def scp_to_vm(vm_id, source_file, dest_file, timeout=60, validate=True,
              source_ssh=None, natbox_client=None):
    """
    scp a file from any SSHClient to a VM
    since not all SSHClient's has connectivity to the VM, this function scps
    the source file to natbox first

    Args:
        vm_id (str): vm to scp to
        source_file (str): full pathname to the source file
        dest_file (str): destination path in the VM
        timeout (int): scp timeout
        validate (bool): verify src and dest sha1sum
        source_ssh (SSHClient|None): the source ssh session, or None to use
        'localhost'
        natbox_client (NATBoxClient|None):

    Returns (None):

    """
    if not natbox_client:
        natbox_client = NATBoxClient.get_natbox_client()

    close_source = False
    if not source_ssh:
        source_ssh = LocalHostClient()
        source_ssh.connect()
        close_source = True

    try:
        # scp-ing from natbox, forward the call
        if source_ssh.host == natbox_client.host:
            return scp_to_vm_from_natbox(vm_id, source_file, dest_file, timeout,
                                         validate, natbox_client=natbox_client)

        LOG.info("scp-ing from {} to natbox {}".format(source_ssh.host,
                                                       natbox_client.host))
        tmp_loc = '~'
        fname = os.path.basename(os.path.normpath(source_file))

        # ensure source file exists
        source_ssh.exec_cmd('test -f {}'.format(source_file), fail_ok=False)

        # calculate sha1sum
        if validate:
            src_sha1 = source_ssh.exec_cmd('sha1sum {}'.format(source_file),
                                           fail_ok=False)[1]
            src_sha1 = src_sha1.split(' ')[0]
            LOG.info("src: {}, sha1sum: {}".format(source_file, src_sha1))
        else:
            src_sha1 = None

        # scp to natbox
        # natbox_client.exec_cmd('mkdir -p {}'.format(tmp_loc))
        source_ssh.scp_on_source(
            source_file, natbox_client.user, natbox_client.host, tmp_loc,
            natbox_client.password, timeout=timeout)

        return scp_to_vm_from_natbox(
            vm_id, '/'.join([tmp_loc, fname]), dest_file, timeout, validate,
            natbox_client=natbox_client, sha1sum=src_sha1)

    finally:
        if close_source:
            source_ssh.close()


@contextmanager
def ssh_to_vm_from_natbox(vm_id, vm_image_name=None, username=None,
                          password=None, prompt=None,
                          timeout=VMTimeout.SSH_LOGIN, natbox_client=None,
                          con_ssh=None, vm_ip=None,
                          vm_ext_port=None, use_fip=False, retry=True,
                          retry_timeout=120, close_ssh=True,
                          auth_info=Tenant.get('admin')):
    """
    ssh to a vm from natbox.

    Args:
        vm_id (str): vm to ssh to
        vm_image_name (str): such as cgcs-guest, tis-centos-guest, ubuntu_14
        username (str):
        password (str):
        prompt (str):
        timeout (int):
        natbox_client (NATBoxClient):
        con_ssh (SSHClient): ssh connection to TiS active controller
        vm_ip (str): ssh to this ip from NatBox if given
        vm_ext_port (str): port forwarding rule external port. If given this
        port will be used. vm_ip must be external
            router ip address.
        use_fip (bool): Whether to ssh to floating ip if a vm has one
            associated. Not applicable if vm_ip is given.
        retry (bool): whether or not to retry if fails to connect
        retry_timeout (int): max time to retry
        close_ssh
        auth_info (dict|None)

    Yields (VMSSHClient):
        ssh client of the vm

    Examples:
        with ssh_to_vm_from_natbox(vm_id=<id>) as vm_ssh:
            vm_ssh.exec_cmd(cmd)

    """
    if vm_image_name is None:
        vm_image_name = get_vm_image_name(vm_id=vm_id, con_ssh=con_ssh,
                                          auth_info=auth_info).strip().lower()

    if vm_ip is None:
        if use_fip:
            vm_ip = network_helper.get_external_ips_for_vms(
                vms=vm_id, con_ssh=con_ssh, auth_info=auth_info)[0]
        else:
            vm_ip = network_helper.get_mgmt_ips_for_vms(
                vms=vm_id, con_ssh=con_ssh, auth_info=auth_info)[0]

    if not natbox_client:
        natbox_client = NATBoxClient.get_natbox_client()

    try:
        vm_ssh = VMSSHClient(natbox_client=natbox_client, vm_ip=vm_ip,
                             vm_ext_port=vm_ext_port,
                             vm_img_name=vm_image_name, user=username,
                             password=password, prompt=prompt,
                             timeout=timeout, retry=retry,
                             retry_timeout=retry_timeout)

    except (exceptions.TiSError, pexpect.ExceptionPexpect):
        LOG.warning(
            'Failed to ssh to VM {}! Collecting vm console log'.format(vm_id))
        get_console_logs(vm_ids=vm_id)
        raise

    try:
        yield vm_ssh
    finally:
        if close_ssh:
            vm_ssh.close()


def get_vm_pid(instance_name, host_ssh):
    """
    Get instance pid on its host.

    Args:
        instance_name: instance name of a vm
        host_ssh: ssh for the host of the given instance

    Returns (str): pid of a instance on its host

    """
    code, vm_pid = host_ssh.exec_sudo_cmd(
        "ps aux | grep --color='never' {} | grep -v grep | awk '{{print $2}}'".
        format(instance_name))
    if code != 0:
        raise exceptions.SSHExecCommandFailed(
            "Failed to get pid for vm: {}".format(instance_name))

    if not vm_pid:
        LOG.warning("PID for {} is not found on host!".format(instance_name))

    return vm_pid


class VMInfo:
    """
    class for storing and retrieving information for specific VM using
    openstack admin.

    Notes: Do not use this class for vm actions, such as boot, delete,
    migrate, etc as these actions should be done by
    tenants.
    """
    __instances = {}
    active_controller_ssh = None

    def __init__(self, vm_id, con_ssh=None, auth_info=Tenant.get('admin')):
        """

        Args:
            vm_id:
            con_ssh: floating controller ssh for the system

        Returns:

        """
        if con_ssh is None:
            con_ssh = ControllerClient.get_active_controller()
        VMInfo.active_controller_ssh = con_ssh
        self.vm_id = vm_id
        self.con_ssh = con_ssh
        self.auth_info = auth_info
        self.initial_table_ = table_parser.table(
            cli.openstack('server show', vm_id, ssh_client=con_ssh,
                          auth_info=self.auth_info, timeout=60)[1])
        self.table_ = self.initial_table_
        self.name = table_parser.get_value_two_col_table(self.initial_table_,
                                                         'name', strict=True)
        self.tenant_id = table_parser.get_value_two_col_table(
            self.initial_table_, 'project_id')
        self.user_id = table_parser.get_value_two_col_table(self.initial_table_,
                                                            'user_id')
        self.boot_info = self.__get_boot_info()
        self.flavor_table = None
        VMInfo.__instances[
            vm_id] = self  # add instance to class variable for tracking

    def refresh_table(self):
        self.table_ = table_parser.table(
            cli.openstack('server show', self.vm_id, ssh_client=self.con_ssh,
                          auth_info=self.auth_info, timeout=60)[1])

    def get_host_name(self):
        self.refresh_table()
        return table_parser.get_value_two_col_table(table_=self.table_,
                                                    field=':host', strict=False)

    def get_flavor_id(self):
        """

        Returns: (dict) {'name': flavor_name, 'id': flavor_id}

        """
        flavor = table_parser.get_value_two_col_table(self.table_, 'flavor')
        flavor_id = re.findall(r'\((.*)\)', flavor)[0]
        return flavor_id

    def refresh_flavor_table(self):
        flavor_id = self.get_flavor_id()
        self.flavor_table = table_parser.table(
            cli.openstack('flavor show', flavor_id, ssh_client=self.con_ssh,
                          auth_info=Tenant.get('admin'))[1])
        return self.flavor_table

    def __get_boot_info(self):
        return _get_boot_info(table_=self.table_, vm_id=self.vm_id,
                              auth_info=self.auth_info,
                              con_ssh=self.con_ssh)

    def get_storage_type(self):
        table_ = self.flavor_table
        if not table_:
            table_ = self.refresh_flavor_table()
        extra_specs = table_parser.get_value_two_col_table(table_, 'properties',
                                                           merge_lines=True)
        extra_specs = table_parser.convert_value_to_dict(value=extra_specs)
        return extra_specs.get(FlavorSpec.STORAGE_BACKING, None)

    def has_local_disks(self):
        if self.boot_info['type'] == 'image':
            return True

        table_ = self.flavor_table
        if not table_:
            table_ = self.refresh_flavor_table()
        swap = table_parser.get_value_two_col_table(table_, 'swap')
        ephemeral = table_parser.get_value_two_col_table(table_, 'ephemeral',
                                                         strict=False)
        return bool(swap or int(ephemeral))

    @classmethod
    def get_vms_info(cls):
        return tuple(cls.__instances)

    @classmethod
    def get_vm_info(cls, vm_id, con_ssh=None):
        if vm_id not in cls.__instances:
            if vm_id in get_all_vms(con_ssh=con_ssh):
                return cls(vm_id, con_ssh)
            else:
                raise exceptions.VMError(
                    "VM with id {} does not exist!".format(vm_id))
        instance = cls.__instances[vm_id]
        instance.refresh_table()
        return instance

    @classmethod
    def remove_instance(cls, vm_id):
        cls.__instances.pop(vm_id, default="No instance found")


def delete_vms(vms=None, delete_volumes=True, check_first=True,
               timeout=VMTimeout.DELETE, fail_ok=False,
               stop_first=True, con_ssh=None, auth_info=Tenant.get('admin'),
               remove_cleanup=None):
    """
    Delete given vm(s) (and attached volume(s)). If None vms given, all vms
    on the system will be deleted.

    Args:
        vms (list|str): list of vm ids to be deleted. If string input,
            assume only one vm id is provided.
        check_first (bool): Whether to check if given vm(s) exist on system
            before attempt to delete
        timeout (int): Max time to wait for delete cli finish and wait for
            vms actually disappear from system
        delete_volumes (bool): delete attached volume(s) if set to True
        fail_ok (bool):
        stop_first (bool): whether to stop active vm(s) first before
            deleting. Best effort only
        con_ssh (SSHClient):
        auth_info (dict):
        remove_cleanup (None|str): remove from vm cleanup list if deleted
            successfully

    Returns (tuple): (rtn_code(int), msg(str))  # rtn_code 1,2,3 only returns
    when fail_ok=True
        (-1, 'No vm(s) to delete.')     # "Empty vm list/string provided and
            no vm exist on system.
        (-1, 'None of the given vm(s) exists on system.')
        (0, "VM(s) deleted successfully.")
        (1, <stderr>)   # delete vm(s) cli returns stderr, some or all vms
            failed to delete.
        (2, "VMs deletion cmd all accepted, but some vms still exist after
            deletion")

    """
    existing_vms = None
    if not vms:
        vms = get_vms(con_ssh=con_ssh, auth_info=auth_info, all_projects=True,
                      long=False)
        existing_vms = list(vms)
    elif isinstance(vms, str):
        vms = [vms]

    vms = [vm for vm in vms if vm]
    if not vms:
        LOG.warning(
            "Empty vm list/string provided and no vm exist on system. Do "
            "Nothing")
        return -1, 'No vm(s) to delete.'

    if check_first:
        if existing_vms is None:
            existing_vms = get_vms(con_ssh=con_ssh, auth_info=auth_info,
                                   all_projects=True, long=False)

        vms = list(set(vms) & set(existing_vms))
        if not vms:
            LOG.info("None given vms exist on system. Do nothing")
            return -1, 'None of the given vm(s) exists on system.'

    if stop_first:  # best effort only
        active_vms = get_vms(vms=vms, auth_info=auth_info, con_ssh=con_ssh,
                             all_projects=True,
                             Status=VMStatus.ACTIVE)
        if active_vms:
            stop_vms(active_vms, fail_ok=True, con_ssh=con_ssh,
                     auth_info=auth_info)

    vols_to_del = []
    if delete_volumes:
        vols_to_del = cinder_helper.get_volumes_attached_to_vms(
            vms=vms, auth_info=auth_info, con_ssh=con_ssh)

    LOG.info("Deleting vm(s): {}".format(vms))
    vms_accepted = []
    deletion_err = ''
    for vm in vms:
        # Deleting vm one by one due to the cmd will stop if a failure is
        # encountered, causing no attempt to delete
        # other vms
        code, output = cli.openstack('server delete', vm, ssh_client=con_ssh,
                                     fail_ok=True, auth_info=auth_info,
                                     timeout=timeout)
        if code > 0:
            deletion_err += '{}\n'.format(output)
        else:
            vms_accepted.append(vm)

    # check if vms are actually removed from nova list
    all_deleted, vms_undeleted = _wait_for_vms_deleted(vms_accepted,
                                                       fail_ok=True,
                                                       auth_info=auth_info,
                                                       timeout=timeout,
                                                       con_ssh=con_ssh)
    if remove_cleanup:
        vms_deleted = list(set(vms_accepted) - set(vms_undeleted))
        ResourceCleanup.remove('vm', vms_deleted, scope=remove_cleanup,
                               del_vm_vols=False)

    # Delete volumes results will not be returned. Best effort only.
    if delete_volumes:
        res = cinder_helper.delete_volumes(vols_to_del, fail_ok=True,
                                           auth_info=auth_info,
                                           con_ssh=con_ssh)[0]
        if res == 0 and remove_cleanup:
            ResourceCleanup.remove('volume', vols_to_del, scope=remove_cleanup)

    # Process returns
    if deletion_err:
        LOG.warning(deletion_err)
        if fail_ok:
            return 1, deletion_err
        raise exceptions.CLIRejected(deletion_err)

    if vms_undeleted:
        msg = 'VM(s) still exsit after deletion: {}'.format(vms_undeleted)
        LOG.warning(msg)
        if fail_ok:
            return 2, msg
        raise exceptions.VMPostCheckFailed(msg)

    LOG.info("VM(s) deleted successfully: {}".format(vms))
    return 0, "VM(s) deleted successfully."


def _wait_for_vms_deleted(vms, timeout=VMTimeout.DELETE, fail_ok=True,
                          check_interval=3, con_ssh=None,
                          auth_info=Tenant.get('admin')):
    """
    Wait for specific vm to be removed from nova list

    Args:
        vms (str|list): list of vms' ids
        timeout (int): in seconds
        fail_ok (bool):
        check_interval (int):
        con_ssh (SSHClient|None):
        auth_info (dict|None):

    Returns (tuple): (result(bool), vms_failed_to_delete(list))

    """
    if isinstance(vms, str):
        vms = [vms]

    vms_to_check = list(vms)
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            vms_to_check = get_vms(vms=vms_to_check, con_ssh=con_ssh,
                                   auth_info=auth_info)
        except exceptions.CLIRejected:
            pass

        if not vms_to_check:
            return True, []
        time.sleep(check_interval)

    if fail_ok:
        return False, vms_to_check
    raise exceptions.VMPostCheckFailed(
        "Some vm(s) are not removed from nova list within {} seconds: {}".
        format(timeout, vms_to_check))


def wait_for_vms_values(vms, header='Status', value=VMStatus.ACTIVE,
                        timeout=VMTimeout.STATUS_CHANGE, fail_ok=True,
                        check_interval=3, con_ssh=None,
                        auth_info=Tenant.get('admin')):
    """
    Wait for specific vms to reach any of the given state(s) in openstack
    server list

    Args:
        vms (str|list): id(s) of vms to check
        header (str): target header in nova list
        value (str|list): expected value(s)
        timeout (int): in seconds
        fail_ok (bool):
        check_interval (int):
        con_ssh (SSHClient|None):
        auth_info (dict|None):

    Returns (list): [result(bool), vms_in_state(dict),
    vms_failed_to_reach_state(dict)]

    """
    if isinstance(vms, str):
        vms = [vms]

    if isinstance(value, str):
        value = [value]

    res_fail = res_pass = None
    end_time = time.time() + timeout
    while time.time() < end_time:
        res_pass = {}
        res_fail = {}
        vms_values = get_vms(vms=vms, con_ssh=con_ssh, auth_info=auth_info,
                             field=header)
        for i in range(len(vms)):
            vm = vms[i]
            vm_value = vms_values[i]
            if vm_value in value:
                res_pass[vm] = vm_value
            else:
                res_fail[vm] = vm_value

        if not res_fail:
            return True, res_pass, res_fail

        time.sleep(check_interval)

    fail_msg = "Some vm(s) did not reach given status from nova list within " \
               "{} seconds: {}".format(timeout, res_fail)
    if fail_ok:
        LOG.warning(fail_msg)
        return False, res_pass, res_fail
    raise exceptions.VMPostCheckFailed(fail_msg)


def set_vm_state(vm_id, check_first=False, error_state=True, fail_ok=False,
                 auth_info=Tenant.get('admin'),
                 con_ssh=None):
    """
    Set vm state to error or active via nova reset-state.

    Args:
        vm_id:
        check_first:
        error_state:
        fail_ok:
        auth_info:
        con_ssh:

    Returns (tuple):

    """
    expt_vm_status = VMStatus.ERROR if error_state else VMStatus.ACTIVE
    LOG.info("Setting vm {} state to: {}".format(vm_id, expt_vm_status))

    if check_first:
        pre_vm_status = get_vm_values(vm_id, fields='status', con_ssh=con_ssh,
                                      auth_info=auth_info)[0]
        if pre_vm_status.lower() == expt_vm_status.lower():
            msg = "VM {} already in {} state. Do nothing.".format(vm_id,
                                                                  pre_vm_status)
            LOG.info(msg)
            return -1, msg

    code, out = set_vm(vm_id=vm_id, state=expt_vm_status, con_ssh=con_ssh,
                       auth_info=auth_info, fail_ok=fail_ok)
    if code > 0:
        return 1, out

    result = wait_for_vm_status(vm_id, expt_vm_status, fail_ok=fail_ok)
    if result is None:
        msg = "VM {} did not reach expected state - {} after " \
              "reset-state.".format(vm_id, expt_vm_status)
        LOG.warning(msg)
        return 2, msg

    msg = "VM state is successfully set to: {}".format(expt_vm_status)
    LOG.info(msg)
    return 0, msg


def reboot_vm(vm_id, hard=False, fail_ok=False, con_ssh=None, auth_info=None,
              cli_timeout=CMDTimeout.REBOOT_VM,
              reboot_timeout=VMTimeout.REBOOT):
    """
    reboot vm via openstack server reboot
    Args:
        vm_id:
        hard (bool): hard or soft reboot
        fail_ok:
        con_ssh:
        auth_info:
        cli_timeout:
        reboot_timeout:

    Returns (tuple):

    """
    vm_status = get_vm_status(vm_id, con_ssh=con_ssh)
    if not vm_status.lower() == 'active':
        LOG.warning(
            "VM is not in active state before rebooting. VM status: {}".format(
                vm_status))

    extra_arg = '--hard ' if hard else ''
    arg = "{}{}".format(extra_arg, vm_id)

    date_format = "%Y%m%d %T"
    start_time = common.get_date_in_format(date_format=date_format)
    code, output = cli.openstack('server reboot', arg, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info,
                                 timeout=cli_timeout)
    if code > 0:
        return 1, output

    # expt_reboot = VMStatus.HARD_REBOOT if hard else VMStatus.SOFT_REBOOT
    # _wait_for_vm_status(vm_id, expt_reboot, check_interval=0, fail_ok=False)
    LOG.info("Wait for vm reboot events to appear in fm event-list")
    expt_reason = 'hard-reboot' if hard else 'soft-reboot'
    system_helper.wait_for_events(
        timeout=30, num=10, entity_instance_id=vm_id,
        start=start_time, fail_ok=False, strict=False,
        **{'Event Log ID': EventLogID.REBOOT_VM_ISSUED,
           'Reason Text': expt_reason})

    system_helper.wait_for_events(
        timeout=reboot_timeout, num=10, entity_instance_id=vm_id,
        start=start_time, fail_ok=False,
        **{'Event Log ID': EventLogID.REBOOT_VM_COMPLETE})

    LOG.info("Check vm status from nova show")
    actual_status = wait_for_vm_status(vm_id,
                                       [VMStatus.ACTIVE, VMStatus.ERROR],
                                       fail_ok=fail_ok, con_ssh=con_ssh,
                                       timeout=30)
    if not actual_status:
        msg = "VM {} did not reach active state after reboot.".format(vm_id)
        LOG.warning(msg)
        return 2, msg

    if actual_status.lower() == VMStatus.ERROR.lower():
        msg = "VM is in error state after reboot."
        if fail_ok:
            LOG.warning(msg)
            return 3, msg
        raise exceptions.VMPostCheckFailed(msg)

    succ_msg = "VM rebooted successfully."
    LOG.info(succ_msg)
    return 0, succ_msg


def __perform_vm_action(vm_id, action, expt_status,
                        timeout=VMTimeout.STATUS_CHANGE, fail_ok=False,
                        con_ssh=None,
                        auth_info=None):
    LOG.info("{} vm {} begins...".format(action, vm_id))
    code, output = cli.nova(action, vm_id, ssh_client=con_ssh, fail_ok=fail_ok,
                            auth_info=auth_info, timeout=120)

    if code == 1:
        return 1, output

    actual_status = wait_for_vm_status(vm_id, [expt_status, VMStatus.ERROR],
                                       fail_ok=fail_ok, con_ssh=con_ssh,
                                       timeout=timeout)

    if not actual_status:
        msg = "VM {} did not reach expected state {} after {}.".format(
            vm_id, expt_status, action)
        LOG.warning(msg)
        return 2, msg

    if actual_status.lower() == VMStatus.ERROR.lower():
        msg = "VM is in error state after {}.".format(action)
        if fail_ok:
            LOG.warning(msg)
            return 3, msg
        raise exceptions.VMPostCheckFailed(msg)

    succ_msg = "{} VM succeeded.".format(action)
    LOG.info(succ_msg)
    return 0, succ_msg


def suspend_vm(vm_id, timeout=VMTimeout.STATUS_CHANGE, fail_ok=False,
               con_ssh=None, auth_info=None):
    return __perform_vm_action(vm_id, 'suspend', VMStatus.SUSPENDED,
                               timeout=timeout, fail_ok=fail_ok,
                               con_ssh=con_ssh, auth_info=auth_info)


def resume_vm(vm_id, timeout=VMTimeout.STATUS_CHANGE, fail_ok=False,
              con_ssh=None, auth_info=None):
    return __perform_vm_action(vm_id, 'resume', VMStatus.ACTIVE,
                               timeout=timeout, fail_ok=fail_ok,
                               con_ssh=con_ssh,
                               auth_info=auth_info)


def pause_vm(vm_id, timeout=VMTimeout.PAUSE, fail_ok=False, con_ssh=None,
             auth_info=None):
    return __perform_vm_action(vm_id, 'pause', VMStatus.PAUSED, timeout=timeout,
                               fail_ok=fail_ok, con_ssh=con_ssh,
                               auth_info=auth_info)


def unpause_vm(vm_id, timeout=VMTimeout.STATUS_CHANGE, fail_ok=False,
               con_ssh=None, auth_info=None):
    return __perform_vm_action(vm_id, 'unpause', VMStatus.ACTIVE,
                               timeout=timeout, fail_ok=fail_ok,
                               con_ssh=con_ssh,
                               auth_info=auth_info)


def stop_vms(vms, timeout=VMTimeout.STATUS_CHANGE, fail_ok=False, con_ssh=None,
             auth_info=None):
    return _start_or_stop_vms(vms, 'stop', VMStatus.STOPPED, timeout,
                              check_interval=1, fail_ok=fail_ok,
                              con_ssh=con_ssh, auth_info=auth_info)


def start_vms(vms, timeout=VMTimeout.STATUS_CHANGE, fail_ok=False, con_ssh=None,
              auth_info=None):
    return _start_or_stop_vms(vms, 'start', VMStatus.ACTIVE, timeout,
                              check_interval=1, fail_ok=fail_ok,
                              con_ssh=con_ssh, auth_info=auth_info)


def _start_or_stop_vms(vms, action, expt_status,
                       timeout=VMTimeout.STATUS_CHANGE, check_interval=3,
                       fail_ok=False,
                       con_ssh=None, auth_info=None):
    LOG.info("{}ing vms {}...".format(action, vms))
    action = action.lower()
    if isinstance(vms, str):
        vms = [vms]

    # Not using openstack client due to stop will be aborted at first
    # failure, without continue processing other vms
    code, output = cli.nova(action, ' '.join(vms), ssh_client=con_ssh,
                            fail_ok=fail_ok, auth_info=auth_info)

    vms_to_check = list(vms)
    if code == 1:
        vms_to_check = re.findall(
            NovaCLIOutput.VM_ACTION_ACCEPTED.format(action), output)
        if not vms_to_check:
            return 1, output

    res_bool, res_pass, res_fail = wait_for_vms_values(
        vms_to_check, 'Status', [expt_status, VMStatus.ERROR],
        fail_ok=fail_ok, check_interval=check_interval, con_ssh=con_ssh,
        timeout=timeout)

    if not res_bool:
        msg = "Some VM(s) did not reach expected state(s) - {}. Actual " \
              "states: {}".format(expt_status, res_fail)
        LOG.warning(msg)
        return 2, msg

    error_vms = [vm_id for vm_id in vms_to_check if
                 res_pass[vm_id].lower() == VMStatus.ERROR.lower()]
    if error_vms:
        msg = "Some VM(s) in error state after {}: {}".format(action, error_vms)
        if fail_ok:
            LOG.warning(msg)
            return 3, msg
        raise exceptions.VMPostCheckFailed(msg)

    succ_msg = "Action {} performed successfully on vms.".format(action)
    LOG.info(succ_msg)
    return 0, succ_msg


def rebuild_vm(vm_id, image_id=None, new_name=None, preserve_ephemeral=None,
               fail_ok=False, con_ssh=None,
               auth_info=Tenant.get('admin'), **metadata):
    if image_id is None:
        image_id = glance_helper.get_image_id_from_name(
            GuestImages.DEFAULT['guest'], strict=True)

    args = '{} {}'.format(vm_id, image_id)

    if new_name:
        args += ' --name {}'.format(new_name)

    if preserve_ephemeral:
        args += ' --preserve-ephemeral'

    for key, value in metadata.items():
        args += ' --meta {}={}'.format(key, value)

    LOG.info("Rebuilding vm {}".format(vm_id))
    # Some features such as trusted image cert not available with openstack
    # client
    code, output = cli.nova('rebuild', args, ssh_client=con_ssh,
                            fail_ok=fail_ok, auth_info=auth_info)
    if code == 1:
        return code, output

    LOG.info("Check vm status after vm rebuild")
    wait_for_vm_status(vm_id, status=VMStatus.ACTIVE, fail_ok=fail_ok,
                       con_ssh=con_ssh)
    actual_status = wait_for_vm_status(vm_id, [VMStatus.ACTIVE, VMStatus.ERROR],
                                       fail_ok=fail_ok, con_ssh=con_ssh,
                                       timeout=VMTimeout.REBUILD)

    if not actual_status:
        msg = "VM {} did not reach active state after rebuild.".format(vm_id)
        LOG.warning(msg)
        return 2, msg

    if actual_status.lower() == VMStatus.ERROR.lower():
        msg = "VM is in error state after rebuild."
        if fail_ok:
            LOG.warning(msg)
            return 3, msg
        raise exceptions.VMPostCheckFailed(msg)

    succ_msg = "VM rebuilded successfully."
    LOG.info(succ_msg)
    return 0, succ_msg


def get_vm_numa_nodes_via_ps(vm_id=None, instance_name=None, host=None,
                             con_ssh=None, auth_info=Tenant.get('admin'),
                             per_vcpu=False):
    """
    Get numa nodes VM is currently on
    Args:
        vm_id:
        instance_name:
        host:
        con_ssh:
        auth_info:
        per_vcpu (bool): if True, return per vcpu, e.g., if vcpu=0,1,2,
            returned list will have same length [0,1,0]

    Returns (list): e.g., [0], [0, 1]

    """
    if not instance_name or not host:
        if not vm_id:
            raise ValueError('vm_id has to be provided')
        instance_name, host = get_vm_values(vm_id,
                                            fields=[":instance_name", ":host"],
                                            strict=False, con_ssh=con_ssh,
                                            auth_info=auth_info)

    with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
        vcpu_cpu_map = get_vcpu_cpu_map(instance_names=instance_name,
                                        host_ssh=host_ssh, con_ssh=con_ssh)[
            instance_name]
        cpus = []
        for i in range(len(vcpu_cpu_map)):
            cpus.append(vcpu_cpu_map[i])

        cpu_non_dup = sorted(list(set(cpus)))
        grep_str = ' '.join(
            ['-e "processor.*: {}$"'.format(cpu) for cpu in cpu_non_dup])
        cmd = 'cat /proc/cpuinfo | grep -A 10 {} | grep --color=never ' \
              '"physical id"'.format(grep_str)
        physical_ids = host_ssh.exec_cmd(cmd, fail_ok=False)[1].splitlines()
        physical_ids = [int(proc.split(sep=':')[-1].strip()) for proc in
                        physical_ids if 'physical' in proc]
        if per_vcpu:
            physical_ids = [physical_ids[cpu_non_dup.index(cpu)] for cpu in
                            cpus]

    return physical_ids


def get_vm_host_and_numa_nodes(vm_id, con_ssh=None, per_vcpu=False):
    """
    Get vm host and numa nodes used for the vm on the host
    Args:
        vm_id (str):
        con_ssh (SSHClient):
        per_vcpu (bool): if True, return numa nodes per vcpu, e.g., vcpu=0,1,
            2, returned list can be: [0,1,0]

    Returns (tuple): (<vm_hostname> (str), <numa_nodes> (list of integers))

    """
    instance_name, host = get_vm_values(vm_id,
                                        fields=[":instance_name", ":host"],
                                        strict=False)
    actual_node_vals = get_vm_numa_nodes_via_ps(vm_id=vm_id,
                                                instance_name=instance_name,
                                                host=host, con_ssh=con_ssh,
                                                per_vcpu=per_vcpu)

    return host, actual_node_vals


def perform_action_on_vm(vm_id, action, auth_info=Tenant.get('admin'),
                         con_ssh=None, **kwargs):
    """
    Perform action on a given vm.

    Args:
        vm_id (str):
        action (str): action to perform on vm. Valid_actions: 'start',
        'stop', 'suspend', 'resume', 'pause', 'unpause',
        'reboot', 'live_migrate', or 'cold_migrate'
        auth_info (dict):
        con_ssh (SSHClient):
        **kwargs: extra params to pass to action function,
        e.g.destination_host='compute-0' when action is live_migrate

    Returns (None):

    """
    action_function_map = {
        'start': start_vms,
        'stop': stop_vms,
        'suspend': suspend_vm,
        'resume': resume_vm,
        'pause': pause_vm,
        'unpause': unpause_vm,
        'reboot': reboot_vm,
        'rebuild': rebuild_vm,
        'live_migrate': live_migrate_vm,
        'cold_migrate': cold_migrate_vm,
        'cold_mig_revert': cold_migrate_vm,
    }
    if not vm_id:
        raise ValueError("vm id is not provided.")

    valid_actions = list(action_function_map.keys())
    action = action.lower().replace(' ', '_')
    if action not in valid_actions:
        raise ValueError(
            "Invalid action provided: {}. Valid actions: {}".format(
                action, valid_actions))

    if action == 'cold_mig_revert':
        kwargs['revert'] = True

    return action_function_map[action](vm_id, con_ssh=con_ssh,
                                       auth_info=auth_info, **kwargs)


def get_vm_nics_info(vm_id, network=None, vnic_type=None, rtn_dict=False):
    """
    Get vm nics info
    Args:
        vm_id:
        network:
        vnic_type:
        rtn_dict:

    Returns (list of dict|dict of dict):
    list or dict (port as key) of port_info_dict. Each port_info_dict
    contains following info:
        {
            'port_id': <port_id>,
            'network': <net_name>,
            'network_id': <net_id>,
            'vnic_type': <vnic_type>,
            'mac_address': <mac_address>,
            'subnet_id': <subnet_id>,
            'subnet_cidr': <subnet_cidr>
        }

    """
    vm_ports, vm_macs, vm_ips_info = network_helper.get_ports(
        server=vm_id, network=network,
        field=('ID', 'MAC Address', 'Fixed IP Addresses'))
    vm_subnets = []
    vm_ips = []
    for ip_info in vm_ips_info:
        ip_info = ip_info[0]
        vm_ips.append(ip_info.get('ip_address'))
        vm_subnets.append(ip_info.get('subnet_id'))

    indexes = list(range(len(vm_ports)))
    vnic_types = []
    vm_net_ids = []
    for port in vm_ports:
        port_vnic_type, port_net_id = network_helper.get_port_values(
            port=port, fields=('binding_vnic_type', 'network_id'))
        vnic_types.append(port_vnic_type)
        vm_net_ids.append(port_net_id)
        if vnic_type and vnic_type != port_vnic_type:
            indexes.remove(list(vm_ports).index(port))

    vm_net_names = []
    ids_, names_, = network_helper.get_networks(field=('ID', 'Name'),
                                                strict=False)
    for net_id in vm_net_ids:
        vm_net_names.append(names_[ids_.index(net_id)])

    res_dict = {}
    res = []
    for i in indexes:
        port_dict = {
            'port_id': vm_ports[i],
            'network': vm_net_names[i],
            'network_id': vm_net_ids[i],
            'vnic_type': vnic_types[i],
            'mac_address': vm_macs[i],
            'ip_address': vm_ips[i]
        }
        if rtn_dict:
            res_dict[vm_ports[i]] = port_dict
        else:
            res.append(port_dict)

    return res_dict if rtn_dict else res


def get_vm_interfaces_via_virsh(vm_id, con_ssh=None):
    """

    Args:
        vm_id:
        con_ssh:

    Returns (list of tuple):
        [(mac_0, vif_model_0)...]

    """
    vm_host = get_vm_host(vm_id=vm_id, con_ssh=con_ssh)
    inst_name = get_vm_instance_name(vm_id=vm_id, con_ssh=con_ssh)

    vm_ifs = []
    with host_helper.ssh_to_host(vm_host, con_ssh=con_ssh) as host_ssh:
        output = host_ssh.exec_sudo_cmd('virsh domiflist {}'.format(inst_name),
                                        fail_ok=False)[1]
        if_lines = output.split('-------------------------------\n', 1)[
            -1].splitlines()
        for line in if_lines:
            if not line.strip():
                continue

            interface, type_, source, model, mac = line.split()
            vm_ifs.append((mac, model))

    return vm_ifs


def add_vlan_for_vm_pcipt_interfaces(vm_id, net_seg_id, retry=3,
                                     init_conf=False):
    """
    Add vlan for vm pci-passthrough interface and restart networking service.
    Do nothing if expected vlan interface already exists in 'ip addr'.

    Args:
        vm_id (str):
        net_seg_id (int|str|dict): such as 1792
        retry (int): max number of times to reboot vm to try to recover it
            from non-exit
        init_conf (bool): To workaround upstream bug where mac changes after
            migrate or resize https://bugs.launchpad.net/nova/+bug/1617429

    Returns: None

    Raises: VMNetworkError if vlan interface is not found in 'ip addr' after
    adding

    Notes:
        Sometimes a non-exist 'rename6' interface will be used for
        pci-passthrough nic after vm maintenance
        Sudo reboot from the vm as workaround.
        By default will try to reboot for a maximum of 3 times

    """
    if not vm_id or not net_seg_id:
        raise ValueError("vm_id and/or net_seg_id not provided.")

    net_seg_id_dict = None
    if isinstance(net_seg_id, dict):
        net_seg_id_dict = net_seg_id
        net_seg_id = None

    for i in range(retry):
        vm_pcipt_nics = get_vm_nics_info(vm_id, vnic_type='direct-physical')

        if not vm_pcipt_nics:
            LOG.warning("No pci-passthrough device found for vm from nova "
                        "show {}".format(vm_id))
            return

        with ssh_to_vm_from_natbox(vm_id=vm_id) as vm_ssh:
            for pcipt_nic in vm_pcipt_nics:

                mac_addr = pcipt_nic['mac_address']
                eth_name = network_helper.get_eth_for_mac(mac_addr=mac_addr,
                                                          ssh_client=vm_ssh)
                if not eth_name:
                    if not init_conf:
                        LOG.warning(
                            "Interface with mac {} is not listed in 'ip addr' "
                            "in vm {}".format(mac_addr, vm_id))
                        LOG.info("Try to get first eth with mac 90:...")
                        eth_name = network_helper.get_eth_for_mac(
                            mac_addr="link/ether 90:", ssh_client=vm_ssh)
                        if not eth_name:
                            exceptions.VMNetworkError(
                                "No Mac starts with 90: in ip addr for vm "
                                "{}".format(vm_id))
                    else:
                        raise exceptions.VMNetworkError(
                            "Interface with mac {} is not listed in 'ip addr' "
                            "in vm {}".format(mac_addr, vm_id))

                if 'rename' in eth_name:
                    LOG.warning(
                        "Retry {}: non-existing interface {} found on "
                        "pci-passthrough nic in vm {}, "
                        "reboot vm to try to recover".format(
                            i + 1, eth_name, vm_id))
                    sudo_reboot_from_vm(vm_id=vm_id, vm_ssh=vm_ssh)
                    wait_for_vm_pingable_from_natbox(vm_id)
                    break

                else:
                    if net_seg_id_dict:
                        net_name = pcipt_nic['network']
                        net_seg_id = net_seg_id_dict[net_name]
                        LOG.info(
                            "Seg id for {}: {}".format(net_name, net_seg_id))

                    vlan_name = "{}.{}".format(eth_name, net_seg_id)

                    output_pre_ipaddr = \
                        vm_ssh.exec_cmd('ip addr', fail_ok=False)[1]
                    if vlan_name in output_pre_ipaddr:
                        LOG.info("{} already in ip addr. Skip.".format(
                            vlan_name))
                        continue

                    # Bring up pcipt interface and assign IP manually.
                    # Upstream bug causes dev name and MAC addr
                    # change after reboot,migrate, making it impossible to
                    # use DHCP or configure permanant static IP.
                    # https://bugs.launchpad.net/nova/+bug/1617429
                    wait_for_interfaces_up(vm_ssh, eth_name, set_up=True)
                    # 'ip link add' works for all linux guests but it does
                    # not persists after network service restart
                    vm_ssh.exec_cmd(
                        'ip link add link {} name {} type vlan id {}'.format(
                            eth_name, vlan_name,
                            net_seg_id))
                    vm_ssh.exec_cmd('ip link set {} up'.format(vlan_name))
                    vnic_ip = pcipt_nic['ip_address']
                    vm_ssh.exec_cmd(
                        'ip addr add {}/24 dev {}'.format(vnic_ip, vlan_name))

                    LOG.info(
                        "Check if vlan is added successfully with IP assigned")
                    output_post_ipaddr = \
                        vm_ssh.exec_cmd('ip addr', fail_ok=False)[1]
                    if vlan_name not in output_post_ipaddr:
                        raise exceptions.VMNetworkError(
                            "{} is not found in 'ip addr' after adding vlan "
                            "interface".
                            format(vlan_name))
                    time.sleep(5)
                    if not is_ip_assigned(vm_ssh, eth_name=vlan_name):
                        msg = 'No IP assigned to {} vlan interface for VM ' \
                              '{}'.format(vlan_name, vm_id)
                        LOG.warning(msg)
                        raise exceptions.VMNetworkError(msg)
                    else:
                        LOG.info(
                            "vlan {} is successfully added and an IP is "
                            "assigned.".format(vlan_name))
            else:
                # did not break, meaning no 'rename' interface detected,
                # vlan either existed or successfully added
                return

            # 'for' loop break which means 'rename' interface detected,
            # and vm reboot triggered - known issue with wrl
            LOG.info("Reboot vm completed. Retry started.")

    else:
        raise exceptions.VMNetworkError(
            "'rename' interface still exists in pci-passthrough vm {} with {} "
            "reboot attempts.".format(vm_id, retry))


def is_ip_assigned(vm_ssh, eth_name):
    output = vm_ssh.exec_cmd('ip addr show {}'.format(eth_name),
                             fail_ok=False)[1]
    return re.search('inet {}'.format(Networks.IPV4_IP), output)


def wait_for_interfaces_up(vm_ssh, eth_names, check_interval=10, timeout=180,
                           set_up=False):
    LOG.info(
        "Waiting for vm interface(s) to be in UP state: {}".format(eth_names))
    end_time = time.time() + timeout
    if isinstance(eth_names, str):
        eth_names = [eth_names]
    ifs_to_check = list(eth_names)
    while time.time() < end_time:
        for eth in ifs_to_check:
            output = \
                vm_ssh.exec_cmd('ip -d link show {}'.format(eth),
                                fail_ok=False)[1]
            if 'state UP' in output:
                ifs_to_check.remove(eth)
                continue
            else:
                if set_up:
                    vm_ssh.exec_cmd('ip link set {} up'.format(eth))
                LOG.info(
                    "{} is not up - wait for {} seconds and check again".format(
                        eth, check_interval))
                break

        if not ifs_to_check:
            LOG.info('interfaces are up: {}'.format(eth_names))
            return

        time.sleep(check_interval)

    raise exceptions.VMNetworkError("Interface(s) not up for given vm")


def sudo_reboot_from_vm(vm_id, vm_ssh=None, check_host_unchanged=True,
                        con_ssh=None):
    pre_vm_host = None
    if check_host_unchanged:
        pre_vm_host = get_vm_host(vm_id, con_ssh=con_ssh)

    LOG.info("Initiate sudo reboot from vm")

    def _sudo_reboot(vm_ssh_):
        extra_prompt = 'Broken pipe'
        output = vm_ssh_.exec_sudo_cmd('reboot -f', get_exit_code=False,
                                       extra_prompt=extra_prompt)[1]
        expt_string = 'The system is going down for reboot|Broken pipe'
        if re.search(expt_string, output):
            # Sometimes system rebooting msg will be displayed right after
            # reboot cmd sent
            vm_ssh_.parent.flush()
            return

        try:
            time.sleep(10)
            vm_ssh_.send('')
            index = vm_ssh_.expect([expt_string, vm_ssh_.prompt], timeout=60)
            if index == 1:
                raise exceptions.VMOperationFailed("Unable to reboot vm {}")
            vm_ssh_.parent.flush()
        except pexpect.TIMEOUT:
            vm_ssh_.send_control('c')
            vm_ssh_.expect()
            raise

    if not vm_ssh:
        with ssh_to_vm_from_natbox(vm_id) as vm_ssh:
            _sudo_reboot(vm_ssh)
    else:
        _sudo_reboot(vm_ssh)

    LOG.info(
        "sudo vm reboot initiated - wait for reboot completes and VM reaches "
        "active state")
    system_helper.wait_for_events(VMTimeout.AUTO_RECOVERY, strict=False,
                                  fail_ok=False, con_ssh=con_ssh,
                                  **{'Entity Instance ID': vm_id,
                                     'Event Log ID':
                                         EventLogID.REBOOT_VM_COMPLETE})
    wait_for_vm_status(vm_id, status=VMStatus.ACTIVE, fail_ok=False,
                       con_ssh=con_ssh)

    if check_host_unchanged:
        post_vm_host = get_vm_host(vm_id, con_ssh=con_ssh)
        if not pre_vm_host == post_vm_host:
            raise exceptions.HostError(
                "VM host changed from {} to {} after sudo reboot vm".format(
                    pre_vm_host, post_vm_host))


def get_proc_nums_from_vm(vm_ssh):
    total_cores = common.parse_cpus_list(
        vm_ssh.exec_cmd('cat /sys/devices/system/cpu/present', fail_ok=False)[
            1])
    online_cores = common.parse_cpus_list(
        vm_ssh.exec_cmd('cat /sys/devices/system/cpu/online', fail_ok=False)[1])
    offline_cores = common.parse_cpus_list(
        vm_ssh.exec_cmd('cat /sys/devices/system/cpu/offline', fail_ok=False)[
            1])

    return total_cores, online_cores, offline_cores


def get_instance_names_via_virsh(host_ssh):
    """
    Get instance names via virsh list on given host
    Args:
        host_ssh:

    Returns (list):

    """
    inst_names = host_ssh.exec_sudo_cmd(
        "virsh list | grep instance- | awk {{'print $2'}}",
        get_exit_code=False)[1]
    return [name.strip() for name in inst_names.splitlines()]


def get_vcpu_cpu_map(instance_names=None, host_ssh=None, host=None,
                     con_ssh=None):
    """
    Get vm(s) vcpu cpu map on given host
    Args:
        instance_names (str|tuple|list|None):
        host_ssh (SSHClient|None):
        host (str|None):
        con_ssh:

    Returns (dict): {<instance_name>: {0: <host_log_core0>,
        1: <host_log_core1>, ...}, ...}

    """
    if not host and not host_ssh:
        raise ValueError('host or host_ssh has to be specified')

    extra_grep = ''
    if instance_names:
        if isinstance(instance_names, str):
            instance_names = (instance_names,)
        extra_grep = '|grep -E "{}"'.format('|'.join(instance_names))
    cmd = 'ps-sched.sh|grep qemu{}|grep " CPU" '.format(extra_grep) + \
          """| awk '{{print $10" "$12" "$15 ;}}'"""

    if host_ssh:
        output = host_ssh.exec_cmd(cmd)[1]
    else:
        with host_helper.ssh_to_host(host, con_ssh=con_ssh) as host_ssh:
            output = host_ssh.exec_cmd(cmd)[1]
    vcpu_cpu_map = {}
    for line in output.splitlines():
        cpu, vcpu, instance_name = line.split()
        instance_name = instance_name.split(sep=',')[0].split(sep='=')[1]
        if instance_name not in vcpu_cpu_map:
            vcpu_cpu_map[instance_name] = {}
        vcpu_cpu_map[instance_name][int(vcpu.split(sep='/')[0])] = int(cpu)
    return vcpu_cpu_map


def get_affined_cpus_for_vm(vm_id, host_ssh=None, vm_host=None,
                            instance_name=None, con_ssh=None):
    """
    cpu affinity list for vm via taskset -pc
    Args:
        vm_id (str):
        host_ssh
        vm_host
        instance_name
        con_ssh (SSHClient):

    Returns (list): such as [10, 30]

    """
    cmd = "ps-sched.sh|grep qemu|grep {}|grep -v grep|awk '{{print $2;}}'" + \
          '|xargs -i /bin/sh -c "taskset -pc {{}}"'

    if host_ssh:
        if not vm_host or not instance_name:
            raise ValueError(
                "vm_host and instance_name have to be provided together with "
                "host_ssh")

        output = host_ssh.exec_cmd(cmd.format(instance_name))[1]

    else:
        vm_host = get_vm_host(vm_id, con_ssh=con_ssh)
        instance_name = get_vm_instance_name(vm_id, con_ssh=con_ssh)

        with host_helper.ssh_to_host(vm_host, con_ssh=con_ssh) as host_ssh:
            output = host_ssh.exec_cmd(cmd.format(instance_name))[1]

    # Sample output:
    # pid 6376's current affinity list: 10
    # pid 6380's current affinity list: 10
    # pid 6439's current affinity list: 10
    # pid 6441's current affinity list: 10
    # pid 6442's current affinity list: 30
    # pid 6445's current affinity list: 10
    # pid 24142's current affinity list: 10

    all_cpus = []
    lines = output.splitlines()
    for line in lines:

        # skip line if below output occurs due to timing in executing cmds
        # taskset: failed to get pid 17125's affinity: No such process
        if "No such process" in line:
            continue

        cpu_str = line.split(sep=': ')[-1].strip()
        cpus = common.parse_cpus_list(cpus=cpu_str)
        all_cpus += cpus

    all_cpus = sorted(list(set(all_cpus)))
    LOG.info("Affined cpus on host {} for vm {}: {}".format(vm_host, vm_id,
                                                            all_cpus))

    return all_cpus


def _scp_net_config_cloud_init(guest_os):
    con_ssh = get_cli_client()
    dest_dir = '{}/userdata'.format(ProjVar.get_var('USER_FILE_DIR'))

    if 'ubuntu' in guest_os:
        dest_name = 'ubuntu_cloud_init_if_conf.sh'
    elif 'centos' in guest_os:
        dest_name = 'centos_cloud_init_if_conf.sh'
    else:
        raise ValueError("Unknown guest_os")

    dest_path = '{}/{}'.format(dest_dir, dest_name)

    if con_ssh.file_exists(file_path=dest_path):
        LOG.info('userdata {} already exists. Return existing path'.format(
            dest_path))
        return dest_path

    LOG.debug('Create userdata directory if not already exists')
    cmd = 'mkdir -p {}'.format(dest_dir)
    con_ssh.exec_cmd(cmd, fail_ok=False)

    # LOG.info('wget image from {} to {}/{}'.format(img_url, img_dest,
    # new_name))
    # cmd = 'wget {} --no-check-certificate -P {} -O {}'.format(img_url,
    # img_dest, new_name)
    # con_ssh.exec_cmd(cmd, expect_timeout=7200, fail_ok=False)

    source_path = '{}/userdata/{}'.format(TestFileServer.HOME, dest_name)
    LOG.info('scp image from test server to active controller')

    scp_cmd = 'scp -oStrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' \
              ' {}@{}:{} {}'.format(TestFileServer.USER, TestFileServer.SERVER,
                                    source_path, dest_dir)

    con_ssh.send(scp_cmd)
    index = con_ssh.expect(
        [con_ssh.prompt, Prompt.PASSWORD_PROMPT, Prompt.ADD_HOST], timeout=3600)
    if index == 2:
        con_ssh.send('yes')
        index = con_ssh.expect([con_ssh.prompt, Prompt.PASSWORD_PROMPT],
                               timeout=3600)
    if index == 1:
        con_ssh.send(TestFileServer.PASSWORD)
        index = con_ssh.expect()
    if index != 0:
        raise exceptions.SSHException("Failed to scp files")

    return dest_dir


def _create_cloud_init_if_conf(guest_os, nics_num):
    """

    Args:
        guest_os:
        nics_num:

    Returns (str|None): file path of the cloud init userdata file for given
        guest os and number of nics
        Sample file content for Centos vm:
            #!/bin/bash
            sudo cp /etc/sysconfig/network-scripts/ifcfg-eth0
            /etc/sysconfig/network-scripts/ifcfg-eth1
            sudo sed -i 's/eth0/eth1/g'
            /etc/sysconfig/network-scripts/ifcfg-eth1
            sudo ifup eth1

        Sample file content for Ubuntu vm:

    """

    file_dir = '{}/userdata'.format(ProjVar.get_var('USER_FILE_DIR'))
    guest_os = guest_os.lower()

    # default eth_path for non-ubuntu image
    eth_path = VMPath.ETH_PATH_CENTOS
    new_user = None

    if 'ubuntu' in guest_os or 'trusty_uefi' in guest_os:
        guest_os = 'ubuntu'
        # vm_if_path = VMPath.VM_IF_PATH_UBUNTU
        eth_path = VMPath.ETH_PATH_UBUNTU
        new_user = 'ubuntu'
    elif 'centos' in guest_os:
        # vm_if_path = VMPath.VM_IF_PATH_CENTOS
        new_user = 'centos'

    file_name = '{}_{}nic_cloud_init_if_conf.sh'.format(guest_os, nics_num)

    file_path = file_dir + file_name
    con_ssh = get_cli_client()
    if con_ssh.file_exists(file_path=file_path):
        LOG.info('userdata {} already exists. Return existing path'.format(
            file_path))
        return file_path

    LOG.info('Create userdata directory if not already exists')
    cmd = 'mkdir -p {}'.format(file_dir)
    con_ssh.exec_cmd(cmd, fail_ok=False)

    tmp_dir = '{}/userdata'.format(ProjVar.get_var('TEMP_DIR'))
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_file = tmp_dir + file_name

    # No longer need to specify bash using cloud-config
    # if 'centos_7' in guest_os:
    #     shell = '/usr/bin/bash'
    # else:
    #     shell = '/bin/bash'

    with open(tmp_file, mode='a', encoding='utf8') as f:
        f.write("#cloud-config\n")

        if new_user is not None:
            f.write("user: {}\n"
                    "password: {}\n"
                    "chpasswd: {{ expire: False}}\n"
                    "ssh_pwauth: True\n\n".format(new_user, new_user))

        if eth_path is not None:
            eth0_path = eth_path.format('eth0')
            f.write("runcmd:\n")
            # f.write(" - echo '#!{}'\n".format(shell))
            for i in range(nics_num - 1):
                ethi_name = 'eth{}'.format(i + 1)
                ethi_path = eth_path.format(ethi_name)
                f.write(' - cp {} {}\n'.format(eth0_path, ethi_path))
                f.write(
                    " - sed -i 's/eth0/{}/g' {}\n".format(ethi_name, ethi_path))
                f.write(' - ifup {}\n'.format(ethi_name))

    if not ProjVar.get_var('REMOTE_CLI'):
        common.scp_from_localhost_to_active_controller(source_path=tmp_file,
                                                       dest_path=file_path,
                                                       is_dir=False)

    LOG.info("Userdata file created: {}".format(file_path))
    return file_path


def _get_cloud_config_add_user(con_ssh=None):
    """
    copy the cloud-config userdata to STX server.
    This userdata adds stx/li69nux user to guest

    Args:
        con_ssh (SSHClient):

    Returns (str): STX filepath of the userdata

    """
    file_dir = ProjVar.get_var('USER_FILE_DIR')
    file_name = UserData.ADDUSER_TO_GUEST
    file_path = file_dir + file_name

    if con_ssh is None:
        con_ssh = get_cli_client()
    if con_ssh.file_exists(file_path=file_path):
        LOG.info('userdata {} already exists. Return existing path'.format(
            file_path))
        return file_path

    source_file = TestServerPath.USER_DATA + file_name
    dest_path = common.scp_from_test_server_to_user_file_dir(
        source_path=source_file, dest_dir=file_dir,
        dest_name=file_name, con_ssh=con_ssh)
    if dest_path is None:
        raise exceptions.CommonError(
            "userdata file {} does not exist after download".format(dest_path))

    return dest_path


def boost_vm_cpu_usage(vm_id, end_event, new_dd_events=None, dd_event=None,
                       timeout=1200, con_ssh=None):
    """
    Boost cpu usage on given number of cpu cores on specified vm using dd cmd
    on a new thread

    Args:
        vm_id (str):
        end_event (Events): Event for kill the dd processes
        new_dd_events (list|Events): list of Event(s) for adding new dd
            process(es)
        dd_event (Events): Event to set after sending first dd cmd.
        timeout: Max time to wait for the end_event to be set before killing dd.
        con_ssh

    Returns: thread

    Examples:
        LOG.tc_step("Boost VM cpu usage")


    """
    if not new_dd_events:
        new_dd_events = []
    elif not isinstance(new_dd_events, list):
        new_dd_events = [new_dd_events]

    def _boost_cpu_in_vm():
        LOG.info("Boosting cpu usage for vm {} using 'dd'".format(vm_id))
        dd_cmd = 'dd if=/dev/zero of=/dev/null &'
        kill_dd = 'pkill -ex dd'

        with ssh_to_vm_from_natbox(vm_id, con_ssh=con_ssh, timeout=120,
                                   auth_info=None) as vm_ssh:
            LOG.info("Start first 2 dd processes in vm")
            vm_ssh.exec_cmd(cmd=dd_cmd)
            vm_ssh.exec_cmd(cmd=dd_cmd)
            if dd_event:
                dd_event.set()

            end_time = time.time() + timeout
            while time.time() < end_time:
                if end_event.is_set():
                    LOG.info("End event set, kill dd processes in vm")
                    vm_ssh.flush()
                    vm_ssh.exec_cmd(kill_dd, get_exit_code=False)
                    return

                for event in new_dd_events:
                    if event.is_set():
                        LOG.info(
                            "New dd event set, start 2 new dd processes in vm")
                        vm_ssh.exec_cmd(cmd=dd_cmd)
                        vm_ssh.exec_cmd(cmd=dd_cmd)
                        new_dd_events.remove(event)
                        break

                time.sleep(3)

            LOG.error(
                "End event is not set within timeout - {}s, kill dd "
                "anyways".format(
                    timeout))
            vm_ssh.exec_cmd(kill_dd)

    LOG.info(
        "Creating new thread to spike cpu_usage on vm cores for vm {}".format(
            vm_id))
    thread = multi_thread.MThread(_boost_cpu_in_vm)
    thread.start_thread(timeout=timeout + 10)

    return thread


def write_in_vm(vm_id, end_event, start_event=None, expect_timeout=120,
                thread_timeout=None, write_interval=5,
                con_ssh=None):
    """
    Continue to write in vm using dd

    Args:
        vm_id (str):
        start_event (Events): set this event when write in vm starts
        end_event (Events): if this event is set, end write right away
        expect_timeout (int):
        thread_timeout (int):
        write_interval (int): how frequent to write. Note: 5 seconds seem to
        be a good interval,
            1 second interval might have noticeable impact on the performance
            of pexpect.
        con_ssh (SSHClient): controller ssh client

    Returns (MThread): new_thread

    """
    if not start_event:
        start_event = Events("Write in vm {} start".format(vm_id))
    write_cmd = "while (true) do date; dd if=/dev/urandom of=output.txt " \
                "bs=1k count=1 conv=fsync || break; echo ; " \
                "sleep {}; done 2>&1 | tee trace.txt".format(write_interval)

    def _keep_writing(vm_id_):
        LOG.info("starting to write to vm using dd...")
        with ssh_to_vm_from_natbox(vm_id_, con_ssh=con_ssh,
                                   close_ssh=False) as vm_ssh_:
            vm_ssh_.send(cmd=write_cmd)

        start_event.set()
        LOG.info("Write_in_vm started")

        LOG.info("Reading the dd output from vm {}".format(vm_id))
        thread.res = True
        try:
            while True:
                expt_output = '1024 bytes'
                index = vm_ssh_.expect([expt_output, vm_ssh_.prompt],
                                       timeout=expect_timeout, fail_ok=True,
                                       searchwindowsize=100)
                if index != 0:
                    LOG.warning(
                        "write has stopped or expected output-'{}' is not "
                        "found".format(
                            expt_output))
                    thread.res = False
                    break

                if end_event.is_set():
                    LOG.info("End thread now")
                    break

                LOG.info("Writing in vm continues...")
                time.sleep(write_interval)

        finally:
            vm_ssh_.send_control('c')

        return vm_ssh_

    thread = multi_thread.MThread(_keep_writing, vm_id)
    thread_timeout = expect_timeout + 30 if thread_timeout is None else \
        thread_timeout
    thread.start_thread(timeout=thread_timeout)

    start_event.wait_for_event(timeout=thread_timeout)

    return thread


def attach_interface(vm_id, port_id=None, net_id=None, fixed_ip=None,
                     fail_ok=False, auth_info=None,
                     con_ssh=None):
    """
    Attach interface to a vm via port_id OR net_id
    Args:
        vm_id (str):
        port_id (str): port to attach to vm
        net_id (str): port from given net to attach to vm
        fixed_ip (str): fixed ip for attached interface. Only works when
        attaching interface via net_id
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (tuple): (<return_code>, <attached_port_id>)
        (0, <port_id_attached>)
        (1, <std_err>)  - cli rejected
        (2, "Post interface attach check failed: <reasons>")     -
        net_id/port_id, vif_model, or fixed_ip do not match
                                                                    with
                                                                    given value

    """
    LOG.info("Attaching interface to VM {}".format(vm_id))
    if not vm_id:
        raise ValueError('vm_id is not supplied')

    args = ''
    args_dict = {
        '--port-id': port_id,
        '--net-id': net_id,
        '--fixed-ip': fixed_ip,
    }

    for key, val in args_dict.items():
        if val is not None:
            args += ' {} {}'.format(key, val)

    args += ' {}'.format(vm_id)

    prev_ports = network_helper.get_ports(server=vm_id, auth_info=auth_info,
                                          con_ssh=con_ssh)
    # Not switching to openstack client due to nova cli makes more sense.
    # openstack client has separate cmds for adding
    # port, network and fixed ip, while fixed ip cmd has to specify the network.
    code, output = cli.nova('interface-attach', args, ssh_client=con_ssh,
                            fail_ok=fail_ok, auth_info=auth_info)

    if code == 1:
        return code, output

    LOG.info("Post interface-attach checks started...")
    post_ports = network_helper.get_ports(server=vm_id, auth_info=auth_info,
                                          con_ssh=con_ssh)
    attached_port = list(set(post_ports) - set(prev_ports))

    err_msgs = []
    if len(attached_port) != 1:
        err_msg = "NICs for vm {} is not incremented by 1".format(vm_id)
        err_msgs.append(err_msg)
    else:
        attached_port = attached_port[0]

    if net_id:
        net_name = network_helper.get_net_name_from_id(net_id, con_ssh=con_ssh,
                                                       auth_info=auth_info)
        net_ips = get_vm_values(vm_id, fields=net_name, strict=False,
                                con_ssh=con_ssh, auth_info=auth_info)[0]
        if fixed_ip and fixed_ip not in net_ips.split(sep=', '):
            err_msg = "specified fixed ip {} is not found in nova show " \
                      "{}".format(fixed_ip, vm_id)
            err_msgs.append(err_msg)

    elif port_id and port_id not in post_ports:
        err_msg = "port {} is not associated to VM".format(port_id)
        err_msgs.append(err_msg)

    if err_msgs:
        err_msgs_str = "Post interface attach check failed:\n{}".format(
            '\n'.join(err_msgs))
        if fail_ok:
            LOG.warning(err_msgs_str)
            return 2, attached_port
        raise exceptions.NovaError(err_msgs_str)

    succ_msg = "Port {} successfully attached to VM {}".format(attached_port,
                                                               vm_id)
    LOG.info(succ_msg)
    return 0, attached_port


def add_ifcfg_scripts(vm_id, mac_addrs, static_ips=None, ipv6='no', reboot=True,
                      vm_prompt=None,
                      **extra_configs):
    """

    Args:
        vm_id:
        mac_addrs (list of str):
        static_ips (None|str|list):
        ipv6:
        reboot:
        vm_prompt
        **extra_configs:

    Returns:

    """
    LOG.info('Add ifcfg script(s) to VM {}'.format(vm_id))
    with ssh_to_vm_from_natbox(vm_id, prompt=vm_prompt) as vm_ssh:
        vm_eths = []
        for mac_addr in mac_addrs:
            eth_name = network_helper.get_eth_for_mac(mac_addr=mac_addr,
                                                      ssh_client=vm_ssh)
            assert eth_name, "vif not found for expected mac_address {} in vm" \
                             " {}".format(mac_addr, vm_id)
            vm_eths.append(eth_name)

        if static_ips:
            if isinstance(static_ips, str):
                static_ips = [static_ips]
            if len(static_ips) != len(vm_eths):
                raise ValueError(
                    "static_ips count has to be the same as vm devs to be "
                    "configured")

        for i in range(len(vm_eths)):
            eth = vm_eths[i]
            if static_ips:
                static_ip = static_ips[i]
                script_content = VMNetwork.IFCFG_STATIC.format(eth, ipv6,
                                                               static_ip)
            else:
                script_content = VMNetwork.IFCFG_DHCP.format(eth, ipv6)

            if extra_configs:
                extra_str = '\n'.join(
                    ['{}={}'.format(k, v) for k, v in extra_configs.items()])
                script_content += '\n{}'.format(extra_str)

            script_path = VMPath.ETH_PATH_CENTOS.format(eth)
            vm_ssh.exec_sudo_cmd('touch {}'.format(script_path))
            vm_ssh.exec_sudo_cmd(
                "cat > {} << 'EOT'\n{}\nEOT".format(script_path,
                                                    script_content),
                fail_ok=False)

    if reboot:
        reboot_vm(vm_id=vm_id)


def detach_interface(vm_id, port_id, cleanup_route=False, fail_ok=False,
                     auth_info=None, con_ssh=None,
                     verify_virsh=True):
    """
    Detach a port from vm
    Args:
        vm_id (str):
        port_id (str): existing port that is attached to given vm
        fail_ok (bool):
        auth_info (dict):
        con_ssh (SSHClient):
        cleanup_route (bool)
        verify_virsh (bool): Whether to verify in virsh xmldump for detached
            port

    Returns (tuple): (<return_code>, <msg>)
        (0, Port <port_id> is successfully detached from VM <vm_id>)
        (1, <stderr>)   - cli rejected
        (2, "Port <port_id> is not detached from VM <vm_id>")   - detached
            port is still shown in nova show

    """
    target_ips = None
    if cleanup_route:
        fixed_ips = \
            network_helper.get_ports(field='Fixed IP Addresses',
                                     port_id=port_id,
                                     con_ssh=con_ssh, auth_info=auth_info)[0]
        target_ips = [fixed_ip['ip_address'] for fixed_ip in fixed_ips]

    mac_to_check = None
    if verify_virsh:
        prev_ports, prev_macs = network_helper.get_ports(
            server=vm_id, auth_info=auth_info, con_ssh=con_ssh,
            field=('ID', 'MAC Address'))
        for prev_port in prev_ports:
            if port_id == prev_port:
                mac_to_check = prev_macs[list(prev_ports).index(prev_port)]
                break

    LOG.info("Detaching port {} from vm {}".format(port_id, vm_id))
    args = '{} {}'.format(vm_id, port_id)
    code, output = cli.nova('interface-detach', args, ssh_client=con_ssh,
                            fail_ok=fail_ok, auth_info=auth_info)
    if code == 1:
        return code, output

    post_ports = network_helper.get_ports(server=vm_id, auth_info=auth_info,
                                          con_ssh=con_ssh)
    if port_id in post_ports:
        err_msg = "Port {} is not detached from VM {}".format(port_id, vm_id)
        if fail_ok:
            return 2, err_msg
        else:
            raise exceptions.NeutronError(
                'port {} is still listed for vm {} after detaching'.format(
                    port_id, vm_id))

    succ_msg = "Port {} is successfully detached from VM {}".format(port_id,
                                                                    vm_id)
    LOG.info(succ_msg)

    if cleanup_route and target_ips:
        cleanup_routes_for_vifs(vm_id=vm_id, vm_ips=target_ips, reboot=True)

    if verify_virsh and mac_to_check:
        if not (cleanup_route and target_ips):
            reboot_vm(vm_id=vm_id, auth_info=auth_info, con_ssh=con_ssh)

        check_devs_detached(vm_id=vm_id, mac_addrs=mac_to_check,
                            con_ssh=con_ssh)

    return 0, succ_msg


def check_devs_detached(vm_id, mac_addrs, con_ssh=None):
    if isinstance(mac_addrs, str):
        mac_addrs = [mac_addrs]

    wait_for_vm_pingable_from_natbox(vm_id, con_ssh=con_ssh)

    LOG.info("Check dev detached from vm")
    vm_err = ''
    with ssh_to_vm_from_natbox(vm_id=vm_id, con_ssh=con_ssh,
                               retry_timeout=180) as vm_ssh:
        for mac_addr in mac_addrs:
            if vm_ssh.exec_cmd('ip addr | grep -B 1 "{}"'.format(mac_addr))[0] \
                    == 0:
                vm_err += 'Interface with mac address {} still exists in ' \
                          'vm\n'.format(mac_addr)

    LOG.info("Check virsh xmldump on compute host")
    inst_name, vm_host = get_vm_values(vm_id,
                                       fields=[":instance_name", ":host"],
                                       strict=False)
    host_err = ''
    with host_helper.ssh_to_host(vm_host, con_ssh=con_ssh) as host_ssh:
        for mac_addr in mac_addrs:
            if host_ssh.exec_sudo_cmd(
                    'virsh dumpxml {} | grep -B 1 -A 1 "{}"'.format(
                        inst_name, mac_addr))[0] == 0:
                host_err += 'VM interface with mac address {} still exists in' \
                            ' virsh\n'.format(mac_addr)
    assert not host_err, host_err

    assert not vm_err, vm_err


def evacuate_vms(host, vms_to_check, con_ssh=None, timeout=600,
                 wait_for_host_up=False, fail_ok=False, post_host=None,
                 force=True, ping_vms=False):
    """
    Evacuate given vms by rebooting their host. VMs should be on specified
    host already when this keyword called.
    Args:
        host (str): host to reboot
        vms_to_check (list): vms to check status for after host reboot
        con_ssh (SSHClient):
        timeout (int): Max time to wait for vms to reach active state after
        reboot -f initiated on host
        wait_for_host_up (bool): whether to wait for host reboot completes
        before checking vm status
        fail_ok (bool): whether to return or to fail test when vm(s) failed
        to evacuate
        post_host (str): expected host for vms to be evacuated to
        force (bool): whether to use 'reboot -f'. This param is only used if
        vlm=False.
        ping_vms (bool): whether to ping vms after evacuation

    Returns (tuple): (<code> (int), <vms_failed_to_evac> (list))
        - (0, [])   all vms evacuated successfully. i.e., active state,
        host changed, pingable from NatBox
        - (1, <inactive_vms>)   some vms did not reach active state after
        host reboot
        - (2, <vms_host_err>)   some vms' host did not change after host reboot

    """
    if isinstance(vms_to_check, str):
        vms_to_check = [vms_to_check]

    HostsToRecover.add(host)
    is_swacted = False
    standby = None
    if wait_for_host_up:
        active, standby = system_helper.get_active_standby_controllers(
            con_ssh=con_ssh)
        if standby and active == host:
            is_swacted = True

    is_sx = system_helper.is_aio_simplex()

    LOG.tc_step("'sudo reboot -f' from {}".format(host))
    host_helper.reboot_hosts(host, wait_for_offline=True,
                             wait_for_reboot_finish=False, force_reboot=force,
                             con_ssh=con_ssh)

    if is_sx:
        host_helper.wait_for_hosts_ready(hosts=host, con_ssh=con_ssh)

    try:
        LOG.tc_step(
            "Wait for vms to reach ERROR or REBUILD state with best effort")
        if not is_sx:
            wait_for_vms_values(vms_to_check,
                                value=[VMStatus.ERROR, VMStatus.REBUILD],
                                fail_ok=True, timeout=120,
                                con_ssh=con_ssh)

        LOG.tc_step(
            "Check vms are in Active state and moved to other host(s) ("
            "non-sx) after host failure")
        res, active_vms, inactive_vms = wait_for_vms_values(
            vms=vms_to_check, value=VMStatus.ACTIVE, timeout=timeout,
            con_ssh=con_ssh)

        if not is_sx:
            vms_host_err = []
            for vm in vms_to_check:
                if post_host:
                    if get_vm_host(vm) != post_host:
                        vms_host_err.append(vm)
                else:
                    if get_vm_host(vm) == host:
                        vms_host_err.append(vm)

            if vms_host_err:
                if post_host:
                    err_msg = "Following VMs is not moved to expected host " \
                              "{} from {}: {}\nVMs did not reach Active " \
                              "state: {}".format(post_host, host, vms_host_err,
                                                 inactive_vms)
                else:
                    err_msg = "Following VMs stayed on the same host {}: " \
                              "{}\nVMs did not reach Active state: {}".\
                        format(host, vms_host_err, inactive_vms)

                if fail_ok:
                    LOG.warning(err_msg)
                    return 1, vms_host_err
                raise exceptions.VMError(err_msg)

        if inactive_vms:
            err_msg = "VMs did not reach Active state after vm host rebooted:" \
                      " {}".format(inactive_vms)
            if fail_ok:
                LOG.warning(err_msg)
                return 2, inactive_vms
            raise exceptions.VMError(err_msg)

        if ping_vms:
            LOG.tc_step("Ping vms after evacuated")
            for vm_ in vms_to_check:
                wait_for_vm_pingable_from_natbox(vm_id=vm_,
                                                 timeout=VMTimeout.DHCP_RETRY)

        LOG.info("All vms are successfully evacuated to other host")
        return 0, []

    finally:
        if wait_for_host_up:
            LOG.tc_step("Waiting for {} to recover".format(host))
            host_helper.wait_for_hosts_ready(host, con_ssh=con_ssh)
            # Do not fail the test due to task affining incomplete for now to
            # unblock test case.
            host_helper.wait_for_tasks_affined(host=host, con_ssh=con_ssh,
                                               fail_ok=True)
            if is_swacted:
                host_helper.wait_for_tasks_affined(standby, con_ssh=con_ssh,
                                                   fail_ok=True)
            time.sleep(60)  # Give some idle time before continue.
            if system_helper.is_aio_duplex(con_ssh=con_ssh):
                system_helper.wait_for_alarm_gone(
                    alarm_id=EventLogID.CPU_USAGE_HIGH, fail_ok=True,
                    check_interval=30)


def boot_vms_various_types(storage_backing=None, target_host=None,
                           cleanup='function', avail_zone='nova', vms_num=5):
    """
    Boot following 5 vms and ensure they are pingable from NatBox:
        - vm1: ephemeral=0, swap=0, boot_from_volume
        - vm2: ephemeral=1, swap=1, boot_from_volume
        - vm3: ephemeral=0, swap=0, boot_from_image
        - vm4: ephemeral=0, swap=0, boot_from_image, attach_volume
        - vm5: ephemeral=1, swap=1, boot_from_image
    Args:
        storage_backing (str|None): storage backing to set in flavor spec.
            When None, storage backing which used by
            most up hypervisors will be used.
        target_host (str|None): Boot vm on target_host when specified. (admin
            role has to be added to tenant under test)
        cleanup (str|None): Scope for resource cleanup, valid values:
            'function', 'class', 'module', None.
            When None, vms/volumes/flavors will be kept on system
        avail_zone (str): availability zone to boot the vms
        vms_num

    Returns (list): list of vm ids

    """
    LOG.info("Create a flavor without ephemeral or swap disks")
    flavor_1 = \
        nova_helper.create_flavor('flv_rootdisk',
                                  storage_backing=storage_backing,
                                  cleanup=cleanup)[1]

    LOG.info("Create another flavor with ephemeral and swap disks")
    flavor_2 = nova_helper.create_flavor('flv_ephemswap', ephemeral=1, swap=512,
                                         storage_backing=storage_backing,
                                         cleanup=cleanup)[1]

    launched_vms = []
    for i in range(int(math.ceil(vms_num / 5.0))):
        LOG.info(
            "Boot vm1 from volume with flavor flv_rootdisk and wait for it "
            "pingable from NatBox")
        vm1_name = "vol_root"
        vm1 = boot_vm(vm1_name, flavor=flavor_1, source='volume',
                      avail_zone=avail_zone, vm_host=target_host,
                      cleanup=cleanup)[1]

        wait_for_vm_pingable_from_natbox(vm1)
        launched_vms.append(vm1)
        if len(launched_vms) == vms_num:
            break

        LOG.info(
            "Boot vm2 from volume with flavor flv_localdisk and wait for it "
            "pingable from NatBox")
        vm2_name = "vol_ephemswap"
        vm2 = boot_vm(vm2_name, flavor=flavor_2, source='volume',
                      avail_zone=avail_zone, vm_host=target_host,
                      cleanup=cleanup)[1]

        wait_for_vm_pingable_from_natbox(vm2)
        launched_vms.append(vm2)
        if len(launched_vms) == vms_num:
            break

        LOG.info(
            "Boot vm3 from image with flavor flv_rootdisk and wait for it "
            "pingable from NatBox")
        vm3_name = "image_root"
        vm3 = boot_vm(vm3_name, flavor=flavor_1, source='image',
                      avail_zone=avail_zone, vm_host=target_host,
                      cleanup=cleanup)[1]

        wait_for_vm_pingable_from_natbox(vm3)
        launched_vms.append(vm3)
        if len(launched_vms) == vms_num:
            break

        LOG.info(
            "Boot vm4 from image with flavor flv_rootdisk, attach a volume to "
            "it and wait for it "
            "pingable from NatBox")
        vm4_name = 'image_root_attachvol'
        vm4 = boot_vm(vm4_name, flavor_1, source='image', avail_zone=avail_zone,
                      vm_host=target_host,
                      cleanup=cleanup)[1]

        vol = cinder_helper.create_volume(bootable=False, cleanup=cleanup)[1]
        attach_vol_to_vm(vm4, vol_id=vol, cleanup=cleanup)

        wait_for_vm_pingable_from_natbox(vm4)
        launched_vms.append(vm4)
        if len(launched_vms) == vms_num:
            break

        LOG.info(
            "Boot vm5 from image with flavor flv_localdisk and wait for it "
            "pingable from NatBox")
        vm5_name = 'image_ephemswap'
        vm5 = boot_vm(vm5_name, flavor_2, source='image', avail_zone=avail_zone,
                      vm_host=target_host,
                      cleanup=cleanup)[1]

        wait_for_vm_pingable_from_natbox(vm5)
        launched_vms.append(vm5)
        if len(launched_vms) == vms_num:
            break

    assert len(launched_vms) == vms_num
    return launched_vms


def get_vcpu_model(vm_id, guest_os=None, con_ssh=None):
    """
    Get vcpu model of given vm. e.g., Intel(R) Xeon(R) CPU E5-2680 v2 @ 2.80GHz
    Args:
        vm_id (str):
        guest_os (str):
        con_ssh (SSHClient):

    Returns (str):

    """
    with ssh_to_vm_from_natbox(vm_id, vm_image_name=guest_os,
                               con_ssh=con_ssh) as vm_ssh:
        out = vm_ssh.exec_cmd("cat /proc/cpuinfo | grep --color=never "
                              "'model name'", fail_ok=False)[1]
        vcpu_model = out.strip().splitlines()[0].split(sep=': ')[1].strip()

    LOG.info("VM {} cpu model: {}".format(vm_id, vcpu_model))
    return vcpu_model


def get_quotas(quotas, default=False, tenant=None, auth_info=None,
               con_ssh=None):
    """
    Get openstack quotas
    Args:
        quotas (str|list|tuple):
        default (bool)
        tenant (str|None): Only used if admin user is used in auth_info
        auth_info (dict):
        con_ssh:

    Returns (list):

    """
    if auth_info is None:
        auth_info = Tenant.get_primary()

    args = ''
    if default:
        args += '--default'
    if tenant and auth_info['user'] == 'admin':
        args += ' {}'.format(tenant)

    if isinstance(quotas, str):
        quotas = [quotas]

    table_ = table_parser.table(
        cli.openstack('quota show', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    values = []
    for item in quotas:
        val = table_parser.get_value_two_col_table(table_, item)
        try:
            val = eval(val)
        except (NameError, SyntaxError):
            pass
        values.append(val)

    return values


def get_quota_details_info(component='compute', tenant=None, detail=True,
                           resources=None,
                           auth_info=Tenant.get('admin'), con_ssh=None):
    """
    Get quota details table from openstack quota list --detail
    Args:
        component (str): compute, network or volume
        tenant:
        detail (bool)
        resources (str|list|tuple|None): filter out table. Used only if
        detail is True and component is not volume
        auth_info:
        con_ssh:

    Returns (dict): All keys are converted to lower case.
        e.g.,
        {'server_groups': {'in use': 0, 'reserved': 1, 'limit': 10},
         ...}

    """
    valid_components = ('compute', 'network', 'volume')
    if component not in valid_components:
        raise ValueError(
            "Please specify a valid component: {}".format(valid_components))

    if not tenant:
        tenant = Tenant.get_primary()['tenant']

    detail_str = ' --detail' if detail and component != 'volume' else ''
    args = '--project={} --{}{}'.format(tenant, component, detail_str)

    table_ = table_parser.table(
        cli.openstack('quota list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    key_header = 'Project ID'
    if detail_str:
        if resources:
            table_ = table_parser.filter_table(table_, Resource=resources)
        key_header = 'resource'

    table_ = table_parser.row_dict_table(table_, key_header=key_header,
                                         lower_case=True,
                                         eliminate_keys=key_header)
    return {k: int(v) for k, v in table_.items()}


def set_quotas(tenant=None, auth_info=Tenant.get('admin'), con_ssh=None,
               sys_con_for_dc=True, fail_ok=False,
               **kwargs):
    """
    Set openstack quotas
    Args:
        tenant (str):
        auth_info (dict):
        con_ssh:
        sys_con_for_dc (bool):
        fail_ok (bool):
        **kwargs: quotas to set. e.g., **{'instances': 10, 'volumes': 20}

    Returns (tuple):

    """
    if not tenant:
        tenant = Tenant.get_primary()['tenant']
    if not auth_info:
        auth_info = Tenant.get_primary()
    if ProjVar.get_var('IS_DC') and sys_con_for_dc and auth_info['region'] \
            != 'SystemController':
        auth_info = Tenant.get(auth_info['user'], dc_region='SystemController')

    args = common.parse_args(
        args_dict={k.replace('_', '-'): v for k, v in kwargs.items()})
    args = '{} {}'.format(args, tenant)
    code, output = cli.openstack('quota set', args, ssh_client=con_ssh,
                                 fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    msg = '{} quotas set successfully'.format(tenant)
    LOG.info(msg)
    return 0, msg


def ensure_vms_quotas(vms_num=10, cores_num=None, vols_num=None, ram=None,
                      tenant=None, auth_info=Tenant.get('admin'),
                      con_ssh=None):
    """
    Update instances, cores, volumes quotas to given numbers
    Args:
        vms_num (int): max number of instances allowed for given tenant
        cores_num (int|None): twice of the vms quota when None
        vols_num (int|None): twice of the vms quota when None
        ram (int|None)
        tenant (None|str):
        auth_info (dict): auth info for admin user
        con_ssh (SSHClient):

    """
    if not vols_num:
        vols_num = 2 * vms_num
    if not cores_num:
        cores_num = 2 * vms_num
    if not ram:
        ram = 2048 * vms_num

    if not tenant:
        tenant = Tenant.get_primary()['tenant']

    volumes_quota, vms_quota, cores_quota, ram_quota = get_quotas(
        quotas=['volumes', 'instances', 'cores', 'ram'],
        con_ssh=con_ssh, tenant=tenant, auth_info=auth_info)
    kwargs = {}
    if vms_num > vms_quota:
        kwargs['instances'] = vms_num
    if cores_num > cores_quota:
        kwargs['cores'] = cores_num
    if vols_num > volumes_quota:
        kwargs['volumes'] = vols_num
    if ram > ram_quota:
        kwargs['ram'] = ram

    if kwargs:
        set_quotas(con_ssh=con_ssh, tenant=tenant, auth_info=auth_info,
                   **kwargs)


def launch_vms(vm_type, count=1, nics=None, flavor=None, storage_backing=None,
               image=None, boot_source=None,
               guest_os=None, avail_zone=None, target_host=None, ping_vms=False,
               con_ssh=None, auth_info=None,
               cleanup='function', **boot_vm_kwargs):
    """

    Args:
        vm_type:
        count:
        nics:
        flavor:
        storage_backing (str):
            storage backend for flavor to be created
            only used if flavor is None
        image:
        boot_source:
        guest_os
        avail_zone:
        target_host:
        ping_vms
        con_ssh:
        auth_info:
        cleanup:
        boot_vm_kwargs (dict):
            additional kwargs to pass to boot_vm

    Returns:

    """

    if not flavor:
        flavor = nova_helper.create_flavor(name=vm_type, vcpus=2,
                                           storage_backing=storage_backing,
                                           cleanup=cleanup)[1]
        extra_specs = {FlavorSpec.CPU_POLICY: 'dedicated'}

        if vm_type in ['vswitch', 'dpdk', 'vhost']:
            extra_specs.update({FlavorSpec.VCPU_MODEL: 'SandyBridge',
                                FlavorSpec.MEM_PAGE_SIZE: '2048'})

        nova_helper.set_flavor(flavor=flavor, **extra_specs)

    resource_id = None
    boot_source = boot_source if boot_source else 'volume'
    if image:
        if boot_source == 'volume':
            resource_id = \
                cinder_helper.create_volume(name=vm_type, source_id=image,
                                            auth_info=auth_info,
                                            guest_image=guest_os)[1]
            if cleanup:
                ResourceCleanup.add('volume', resource_id, scope=cleanup)
        else:
            resource_id = image

    if not nics:
        if vm_type in ['pci-sriov', 'pci-passthrough']:
            raise NotImplementedError("nics has to be provided for pci-sriov and "
                                      "pci-passthrough")

        if vm_type in ['vswitch', 'dpdk', 'vhost']:
            vif_model = 'avp'
        else:
            vif_model = vm_type

        mgmt_net_id = network_helper.get_mgmt_net_id(auth_info=auth_info)
        tenant_net_id = network_helper.get_tenant_net_id(auth_info=auth_info)
        internal_net_id = network_helper.get_internal_net_id(
            auth_info=auth_info)

        nics = [{'net-id': mgmt_net_id},
                {'net-id': tenant_net_id, 'vif-model': vif_model},
                {'net-id': internal_net_id, 'vif-model': vif_model}]

    user_data = None
    if vm_type in ['vswitch', 'dpdk', 'vhost']:
        user_data = network_helper.get_dpdk_user_data(con_ssh=con_ssh)

    vms = []
    for i in range(count):
        vm_id = boot_vm(name="{}-{}".format(vm_type, i), flavor=flavor,
                        source=boot_source, source_id=resource_id,
                        nics=nics, guest_os=guest_os, avail_zone=avail_zone,
                        vm_host=target_host, user_data=user_data,
                        auth_info=auth_info, con_ssh=con_ssh, cleanup=cleanup,
                        **boot_vm_kwargs)[1]
        vms.append(vm_id)

        if ping_vms:
            wait_for_vm_pingable_from_natbox(vm_id=vm_id, con_ssh=con_ssh)
    return vms, nics


def get_ping_loss_duration_between_vms(from_vm, to_vm, net_type='data',
                                       timeout=600, ipv6=False,
                                       start_event=None,
                                       end_event=None, con_ssh=None,
                                       ping_interval=1):
    """
    Get ping loss duration in milliseconds from one vm to another
    Args:
        from_vm (str): id of the ping source vm
        to_vm (str): id of the ping destination vm
        net_type (str): e.g., data, internal, mgmt
        timeout (int): max time to wait for ping loss before force end it
        ipv6 (bool): whether to use ping -6 for ipv6 address
        start_event (Event): set given event to signal ping has started
        end_event (Event): stop ping loss detection if given event is set
        con_ssh (SSHClient):
        ping_interval (int|float): timeout of ping cmd in seconds

    Returns (int): milliseconds of ping loss duration

    """

    to_vm_ip = _get_vms_ips(vm_ids=to_vm, net_types=net_type,
                            con_ssh=con_ssh)[0][0]
    with ssh_to_vm_from_natbox(vm_id=from_vm, con_ssh=con_ssh) as from_vm_ssh:
        duration = network_helper.get_ping_failure_duration(
            server=to_vm_ip, ssh_client=from_vm_ssh, timeout=timeout,
            ipv6=ipv6, start_event=start_event, end_event=end_event,
            ping_interval=ping_interval)
        return duration


def get_ping_loss_duration_from_natbox(vm_id, timeout=900, start_event=None,
                                       end_event=None, con_ssh=None,
                                       ping_interval=0.5):
    vm_ip = _get_vms_ips(vm_ids=vm_id, net_types='mgmt', con_ssh=con_ssh)[0][0]
    natbox_client = NATBoxClient.get_natbox_client()
    duration = network_helper.get_ping_failure_duration(
        server=vm_ip, ssh_client=natbox_client, timeout=timeout,
        start_event=start_event, end_event=end_event,
        ping_interval=ping_interval)
    return duration


def get_ping_loss_duration_on_operation(vm_id, timeout, ping_interval,
                                        oper_func, *func_args, **func_kwargs):
    LOG.tc_step("Start pinging vm {} from NatBox on a new thread".format(vm_id))
    start_event = Events("Ping started")
    end_event = Events("Operation completed")
    ping_thread = MThread(get_ping_loss_duration_from_natbox, vm_id=vm_id,
                          timeout=timeout,
                          start_event=start_event, end_event=end_event,
                          ping_interval=ping_interval)
    ping_thread.start_thread(timeout=timeout + 30)

    try:
        if start_event.wait_for_event(timeout=60):
            LOG.tc_step(
                "Perform operation on vm and ensure it's reachable after that")
            oper_func(*func_args, **func_kwargs)
            # Operation completed. Set end flag so ping thread can end properly
            time.sleep(3)
            end_event.set()
            # Expect ping thread to end in less than 1 minute after
            # live-migration complete
            duration = ping_thread.get_output(timeout=60)
            # assert duration, "No ping loss detected"
            if duration == 0:
                LOG.warning("No ping loss detected")
            return duration

        assert False, "Ping failed since start"
    finally:
        ping_thread.wait_for_thread_end(timeout=5)


def collect_guest_logs(vm_id):
    LOG.info("Attempt to collect guest logs with best effort")
    log_names = ['messages', 'user.log']
    try:
        res = _recover_vm(vm_id=vm_id)
        if not res:
            LOG.info(
                "VM {} in unrecoverable state, skip collect guest logs.".format(
                    vm_id))
            return

        with ssh_to_vm_from_natbox(vm_id) as vm_ssh:
            for log_name in log_names:
                log_path = '/var/log/{}'.format(log_name)
                if not vm_ssh.file_exists(log_path):
                    continue

                local_log_path = '{}/{}_{}'.format(
                    ProjVar.get_var('GUEST_LOGS_DIR'), log_name, vm_id)
                current_user = local_host.get_user()
                if current_user == TestFileServer.USER:
                    vm_ssh.exec_sudo_cmd('chmod -R 755 {}'.format(log_path),
                                         fail_ok=True)
                    vm_ssh.scp_on_source_to_localhost(
                        source_file=log_path,
                        dest_user=current_user,
                        dest_password=TestFileServer.PASSWORD,
                        dest_path=local_log_path)
                else:
                    output = vm_ssh.exec_cmd('tail -n 200 {}'.format(log_path),
                                             fail_ok=False)[1]
                    with open(local_log_path, mode='w', encoding='utf8') as f:
                        f.write(output)
                return

    except Exception as e:
        LOG.warning("Failed to collect guest logs: {}".format(e))


def _recover_vm(vm_id, con_ssh=None):
    status = get_vm_status(vm_id=vm_id, con_ssh=con_ssh)
    if status == VMStatus.ACTIVE:
        return True
    elif status == VMStatus.STOPPED:
        code, msg = start_vms(vms=vm_id, fail_ok=True)
        return code == 0
    elif status == VMStatus.PAUSED:
        code, msg = unpause_vm(vm_id=vm_id, fail_ok=True, con_ssh=con_ssh)
        if code > 0:
            code, msg = resume_vm(vm_id, fail_ok=True, con_ssh=con_ssh)
            if code > 0:
                return False
        return True
    else:
        return False


def get_vim_events(vm_id, event_ids=None, controller=None, con_ssh=None):
    """
    Get vim events from nfv-vim-events.log
    Args:
        vm_id (str):
        event_ids (None|str|list|tuple): return only given vim events when
            specified
        controller (None|str): controller where vim log is on. Use current
        active controller if None.
        con_ssh (SSHClient):

    Returns (list): list of dictionaries, each dictionary is one event. e.g.,:
        [{'log-id': '47', 'event-id': 'instance-live-migrate-begin', ... ,
        'timestamp': '2018-03-04 01:34:28.915008'},
        {'log-id': '49', 'event-id': 'instance-live-migrated', ... ,
        'timestamp': '2018-03-04 01:35:34.043094'}]

    """
    if not controller:
        controller = system_helper.get_active_controller_name()

    if isinstance(event_ids, str):
        event_ids = [event_ids]

    with host_helper.ssh_to_host(controller, con_ssh=con_ssh) as controller_ssh:
        vm_logs = controller_ssh.exec_cmd(
            'grep --color=never -A 4 -B 6 -E "entity .*{}" '
            '/var/log/nfv-vim-events.log'.
            format(vm_id))[1]

    log_lines = vm_logs.splitlines()
    vm_events = []
    vm_event = {}
    for line in log_lines:
        if re.search(' = ', line):
            if line.startswith('log-id') and vm_event:
                if not event_ids or vm_event['event-id'] in event_ids:
                    vm_events.append(vm_event)

                vm_event = {}
            key, val = re.findall('(.*)= (.*)', line)[0]
            vm_event[key.strip()] = val.strip()

    if vm_event and (not event_ids or vm_event['event-id'] in event_ids):
        vm_events.append(vm_event)

    LOG.info("VM events: {}".format(vm_events))
    return vm_events


def get_live_migrate_duration(vm_id, con_ssh=None):
    LOG.info(
        "Get live migration duration from nfv-vim-events.log for vm {}".format(
            vm_id))
    events = (VimEventID.LIVE_MIG_BEGIN, VimEventID.LIVE_MIG_END)
    live_mig_begin, live_mig_end = get_vim_events(vm_id=vm_id, event_ids=events,
                                                  con_ssh=con_ssh)

    start_time = live_mig_begin['timestamp']
    end_time = live_mig_end['timestamp']
    duration = common.get_timedelta_for_isotimes(time1=start_time,
                                                 time2=end_time).total_seconds()
    LOG.info("Live migration for vm {} took {} seconds".format(vm_id, duration))

    return duration


def get_cold_migrate_duration(vm_id, con_ssh=None):
    LOG.info("Get cold migration duration from vim-event-log for vm {}".format(
        vm_id))
    events = (VimEventID.COLD_MIG_BEGIN, VimEventID.COLD_MIG_END,
              VimEventID.COLD_MIG_CONFIRM_BEGIN, VimEventID.COLD_MIG_CONFIRMED)
    cold_mig_begin, cold_mig_end, cold_mig_confirm_begin, \
        cold_mig_confirm_end = get_vim_events(vm_id=vm_id, event_ids=events,
                                              con_ssh=con_ssh)

    duration_cold_mig = common.get_timedelta_for_isotimes(
        time1=cold_mig_begin['timestamp'],
        time2=cold_mig_end['timestamp']).total_seconds()

    duration_confirm = common.get_timedelta_for_isotimes(
        time1=cold_mig_confirm_begin['timestamp'],
        time2=cold_mig_confirm_end['timestamp']).total_seconds()

    duration = duration_cold_mig + duration_confirm
    LOG.info("Cold migrate and confirm for vm {} took {} seconds".format(
        vm_id, duration))

    return duration


def live_migrate_force_complete(vm_id, migration_id=None, timeout=300,
                                fail_ok=False, con_ssh=None):
    """
    Run nova live-migration-force-complete against given vm and migration
    session.
    Args:
        vm_id (str):
        migration_id (str|int):
        timeout:
        fail_ok:
        con_ssh:

    Returns (tuple):
        (0, 'VM is successfully live-migrated after
        live-migration-force-complete')
        (1, <err_msg>)      # nova live-migration-force-complete cmd
        rejected. Only returns if fail_ok=True.

    """
    if not migration_id:
        migration_id = get_vm_migration_values(vm_id=vm_id, fail_ok=False,
                                               con_ssh=con_ssh)[0]

    # No replacement in openstack client
    code, output = cli.nova('live-migration-force-complete',
                            '{} {}'.format(vm_id, migration_id),
                            ssh_client=con_ssh,
                            fail_ok=fail_ok)

    if code > 0:
        return 1, output

    wait_for_vm_migration_status(vm_id=vm_id, migration_id=migration_id,
                                 fail_ok=False, timeout=timeout,
                                 con_ssh=con_ssh)
    msg = "VM is successfully live-migrated after live-migration-force-complete"
    LOG.info(msg)
    return 0, msg


def get_vm_migration_values(vm_id, field='Id', migration_type='live-migration',
                            fail_ok=True, con_ssh=None, **kwargs):
    """
    Get values for given vm via nova migration-list
    Args:
        vm_id (str):
        field (str):
        migration_type(str): valid types: live-migration, migration
        fail_ok:
        con_ssh:
        **kwargs:

    Returns (list):

    """
    migration_tab = nova_helper.get_migration_list_table(con_ssh=con_ssh)
    filters = {'Instance UUID': vm_id, 'Type': migration_type}
    if kwargs:
        filters.update(kwargs)
    mig_ids = table_parser.get_values(migration_tab, target_header=field,
                                      **filters)
    if not mig_ids and not fail_ok:
        raise exceptions.VMError(
            "{} has no {} session with filters: {}".format(vm_id,
                                                           migration_type,
                                                           kwargs))

    return mig_ids


def wait_for_vm_migration_status(vm_id, migration_id=None, migration_type=None,
                                 expt_status='completed',
                                 fail_ok=False, timeout=300, check_interval=5,
                                 con_ssh=None):
    """
    Wait for a migration session to reach given status in nova mgiration-list
    Args:
        vm_id (str):
        migration_id (str|int):
        migration_type (str): valid types: live-migration, migration
        expt_status (str): migration status to wait for. such as completed,
        running, etc
        fail_ok (bool):
        timeout (int): max time to wait for the state
        check_interval (int):
        con_ssh:

    Returns (tuple):
        (0, <expt_status>)      #  migration status reached as expected
        (1, <current_status>)   # did not reach given status. This only
        returns if fail_ok=True

    """
    if not migration_id:
        migration_id = get_vm_migration_values(
            vm_id=vm_id, migration_type=migration_type, fail_ok=False,
            con_ssh=con_ssh)[0]

    LOG.info("Waiting for migration {} for vm {} to reach {} status".format(
        migration_id, vm_id, expt_status))
    end_time = time.time() + timeout
    prev_state = None
    while time.time() < end_time:
        mig_status = get_vm_migration_values(vm_id=vm_id, field='Status',
                                             **{'Id': migration_id})[0]
        if mig_status == expt_status:
            LOG.info(
                "Migration {} for vm {} reached status: {}".format(migration_id,
                                                                   vm_id,
                                                                   expt_status))
            return True, expt_status

        if mig_status != prev_state:
            LOG.info(
                "Migration {} for vm {} is in status - {}".format(migration_id,
                                                                  vm_id,
                                                                  mig_status))
            prev_state = mig_status

        time.sleep(check_interval)

    msg = 'Migration {} for vm {} did not reach {} status within {} seconds. ' \
          'It is in {} status.'.format(migration_id, vm_id, expt_status,
                                       timeout, prev_state)
    if fail_ok:
        LOG.warning(msg)
        return False, prev_state
    else:
        raise exceptions.VMError(msg)


def get_vms_ports_info(vms, rtn_subnet_id=False):
    """
    Get VMs' ports' (ip_addr, subnet_cidr_or_id, mac_addr).

    Args:
        vms (str|list):
            vm_id, or a list of vm_ids
        rtn_subnet_id (bool):
            replaces cidr with subnet_id in result

    Returns (dict):
        {vms[0]: [(ip_addr, subnet, ...], vms[1]: [...], ...}
    """
    if not issubclass(type(vms), (list, tuple)):
        vms = [vms]

    info = {}
    subnet_tab_ = table_parser.table(
        cli.openstack('subnet list', auth_info=Tenant.get('admin'))[1])
    for vm in vms:
        info[vm] = []
        vm_ports, vm_macs, vm_fixed_ips = network_helper.get_ports(
            server=vm, field=('ID', 'MAC Address', 'Fixed IP Addresses'))
        for i in range(len(vm_ports)):
            port = vm_ports[i]
            mac = vm_macs[i]
            fixed_ips = vm_fixed_ips[i]
            if not isinstance(fixed_ips, list):
                fixed_ips = [fixed_ips]

            for fixed_ip in fixed_ips:
                subnet_id = fixed_ip['subnet_id']
                ip_addr = fixed_ip['ip_address']
                subnet = subnet_id if rtn_subnet_id else \
                    table_parser.get_values(subnet_tab_, 'Subnet',
                                            id=subnet_id)[0]
                net_id = table_parser.get_values(subnet_tab_, 'Network',
                                                 id=subnet_id)[0]

                LOG.info(
                    "VM {} port {}: mac={} ip={} subnet={} net_id={}".format(
                        vm, port, mac, ip_addr,  subnet, net_id))
                info[vm].append((port, ip_addr, subnet, mac, net_id))

    return info


def _set_vm_route(vm_id, target_subnet, via_ip, dev_or_mac, persist=True):
    # returns True if the targeted VM is vswitch-enabled
    # for vswitch-enabled VMs, it must be setup with TisInitServiceScript if
    # persist=True
    with ssh_to_vm_from_natbox(vm_id) as ssh_client:
        vshell, msg = ssh_client.exec_cmd("vshell port-list", fail_ok=True)
        vshell = not vshell
        if ':' in dev_or_mac:
            dev = network_helper.get_eth_for_mac(ssh_client, dev_or_mac,
                                                 vshell=vshell)
        else:
            dev = dev_or_mac
        if not vshell:  # not avs managed
            param = target_subnet, via_ip, dev
            LOG.info("Routing {} via {} on interface {}".format(*param))
            ssh_client.exec_sudo_cmd(
                "route add -net {} gw {} {}".format(*param), fail_ok=False)
            if persist:
                LOG.info("Setting persistent route")
                ssh_client.exec_sudo_cmd(
                    "echo -e \"{} via {}\" > "
                    "/etc/sysconfig/network-scripts/route-{}".format(
                        *param), fail_ok=False)
            return False
        else:
            param = target_subnet, via_ip, dev
            LOG.info(
                "Routing {} via {} on interface {}, AVS-enabled".format(*param))
            ssh_client.exec_sudo_cmd(
                "sed -i $'s,quit,route add {} {} {} 1\\\\nquit,"
                "g' /etc/vswitch/vswitch.cmds.default".format(
                    target_subnet, dev, via_ip), fail_ok=False)
            # reload vswitch
            ssh_client.exec_sudo_cmd("/etc/init.d/vswitch restart",
                                     fail_ok=False)
            if persist:
                LOG.info("Setting persistent route")
                ssh_client.exec_sudo_cmd(
                    # ROUTING_STUB
                    # "192.168.1.0/24,192.168.111.1,eth0"
                    "sed -i $'s@#ROUTING_STUB@\"{},{},"
                    "{}\"\\\\n#ROUTING_STUB@g' {}".format(
                        target_subnet, via_ip, dev,
                        TisInitServiceScript.configuration_path
                    ), fail_ok=False)
            return True


def route_vm_pair(vm1, vm2, bidirectional=True, validate=True):
    """
    Route the pair of VMs' data interfaces through internal interfaces
    If multiple interfaces available on either of the VMs, the last one is used
    If no interfaces available for data/internal network for either VM,
    raises IndexError
    The internal interfaces for the pair VM must be on the same gateway
    no fail_ok option, since if failed, the vm's state is undefined

    Args:
        vm1 (str):
            vm_id, src if bidirectional=False
        vm2 (str):
            vm_id, dest if bidirectional=False
        bidirectional (bool):
            if True, also routes from vm2 to vm1
        validate (bool):
            validate pings between the pair over the data network

    Returns (dict):
        the interfaces used for routing,
        {vm_id: {'data': {'ip', 'cidr', 'mac'},
        'internal':{'ip', 'cidr', 'mac'}}}
    """
    if vm1 == vm2:
        raise ValueError("cannot route to a VM itself")

    auth_info = Tenant.get('admin')
    LOG.info("Collecting VMs' networks")
    interfaces = {
        vm1: {"data": network_helper.get_tenant_ips_for_vms(
            vm1, auth_info=auth_info),
              "internal": network_helper.get_internal_ips_for_vms(vm1)},
        vm2: {"data": network_helper.get_tenant_ips_for_vms(
            vm2, auth_info=auth_info),
              "internal": network_helper.get_internal_ips_for_vms(vm2)},
    }

    for vm, info in get_vms_ports_info([vm1, vm2]).items():
        for port, ip, cidr, mac, net_id in info:
            # expect one data and one internal
            if ip in interfaces[vm]['data']:
                interfaces[vm]['data'] = {'ip': ip, 'cidr': cidr, 'mac': mac,
                                          'port': port}
            elif ip in interfaces[vm]['internal']:
                interfaces[vm]['internal'] = {'ip': ip, 'cidr': cidr,
                                              'mac': mac, 'port': port}

    if interfaces[vm1]['internal']['cidr'] != \
            interfaces[vm2]['internal']['cidr']:
        raise ValueError(
            "the internal interfaces for the VM pair is not on the same "
            "gateway")

    vshell_ = _set_vm_route(
        vm1,
        interfaces[vm2]['data']['cidr'], interfaces[vm2]['internal']['ip'],
        interfaces[vm1]['internal']['mac'])

    if bidirectional:
        _set_vm_route(vm2, interfaces[vm1]['data']['cidr'],
                      interfaces[vm1]['internal']['ip'],
                      interfaces[vm2]['internal']['mac'])

    for vm in (vm1, vm2):
        LOG.info("Add vms' data network ip as allowed address for internal "
                 "network port")
        network_helper.set_port(
            port_id=interfaces[vm]['internal']['port'],
            auth_info=auth_info,
            allowed_addr_pairs={'ip-address': interfaces[vm]['data']['ip']})

    if validate:
        LOG.info("Validating route(s) across data")
        ping_between_routed_vms(to_vm=vm2, from_vm=vm1, vshell=vshell_,
                                bidirectional=bidirectional)

    return interfaces


def ping_between_routed_vms(to_vm, from_vm, vshell=True, bidirectional=True,
                            timeout=120):
    """
    Ping between routed vm pair
    Args:
        to_vm:
        from_vm:
        vshell:
        bidirectional:
        timeout:

    Returns:

    """
    ping_vms_from_vm(to_vms=to_vm, from_vm=from_vm, timeout=timeout,
                     net_types='data', vshell=vshell,
                     source_net_types='internal')
    if bidirectional:
        ping_vms_from_vm(to_vms=from_vm, from_vm=to_vm, timeout=timeout,
                         net_types='data', vshell=vshell,
                         source_net_types='internal')


def setup_kernel_routing(vm_id, **kwargs):
    """
    Setup kernel routing function for the specified VM
    replicates the operation as in wrs_guest_setup.sh (and comes
    with the same assumptions)
    in order to persist kernel routing after reboots, the operation has to be
    stored in /etc/init.d
    see TisInitServiceScript for script details
    no fail_ok option, since if failed, the vm's state is undefined

    Args:
        vm_id (str):
            the VM to be configured
        kwargs (dict):
            kwargs for TisInitServiceScript.configure

    """
    LOG.info(
        "Setting up kernel routing for VM {}, kwargs={}".format(vm_id, kwargs))

    scp_to_vm(vm_id, TisInitServiceScript.src(), TisInitServiceScript.dst())
    with ssh_to_vm_from_natbox(vm_id) as ssh_client:
        r, msg = ssh_client.exec_cmd("cat /proc/sys/net/ipv4/ip_forward",
                                     fail_ok=False)
        if msg == "1":
            LOG.warn(
                "VM {} has ip_forward enabled already, skipping".format(vm_id))
            return
        TisInitServiceScript.configure(ssh_client, **kwargs)
        TisInitServiceScript.enable(ssh_client)
        TisInitServiceScript.start(ssh_client)


def setup_avr_routing(vm_id, mtu=1500, vm_type='vswitch', **kwargs):
    """
    Setup avr routing (vswitch L3) function for the specified VM
    replciates the operation as in wrs_guest_setup.sh (and comes with
    the same assumptions)
    in order to persist kernel routing after reboots, the operation has to be
    stored in /etc/init.d
    see TisInitServiceScript for script details
    no fail_ok option, since if failed, the vm's state is undefined

    Args:
        vm_id (str):
            the VM to be configured
        mtu (int):
            1500 by default
            for jumbo frames (9000), tenant net support is required
        vm_type (str):
            PCI NIC_DEVICE
            vhost: "${PCI_VENDOR_VIRTIO}:${PCI_DEVICE_VIRTIO}:
                ${PCI_SUBDEVICE_NET}"
            any other: "${PCI_VENDOR_VIRTIO}:${PCI_DEVICE_MEMORY}:
                ${PCI_SUBDEVICE_AVP}" (default)
        kwargs (dict):
            kwargs for TisInitServiceScript.configure

    """
    LOG.info(
        "Setting up avr routing for VM {}, kwargs={}".format(vm_id, kwargs))
    datas = network_helper.get_tenant_ips_for_vms(vm_id)
    data_dict = dict()
    try:
        internals = network_helper.get_internal_ips_for_vms(vm_id)
    except ValueError:
        internals = list()
    internal_dict = dict()
    for vm, info in get_vms_ports_info([vm_id]).items():
        for port, ip, cidr, mac, net_id in info:
            if ip in datas:
                data_dict[ip] = ipaddress.ip_network(cidr).netmask
            elif ip in internals:
                internal_dict[ip] = ipaddress.ip_network(cidr).netmask

    interfaces = list()
    items = list(data_dict.items()) + list(internal_dict.items())

    if len(items) > 2:
        LOG.warn(
            "wrs_guest_setup/tis_automation_init does not support more than "
            "two DPDK NICs")
        LOG.warn("stripping {} from interfaces".format(items[2:]))
        items = items[:2]

    for (ip, netmask), ct in zip(items, range(len(items))):
        interfaces.append(
            """\"{},{},eth{},{}\"""".format(ip, netmask, ct, str(mtu)))

    nic_device = ""
    if vm_type == 'vhost':
        nic_device = "\"${PCI_VENDOR_VIRTIO}:${PCI_DEVICE_VIRTIO}:" \
                     "${PCI_SUBDEVICE_NET}\""

    scp_to_vm(vm_id, TisInitServiceScript.src(), TisInitServiceScript.dst())
    with ssh_to_vm_from_natbox(vm_id) as ssh_client:
        TisInitServiceScript.configure(
            ssh_client, NIC_DEVICE=nic_device,
            NIC_COUNT=str(len(items)), FUNCTIONS="avr,",
            ROUTES="""(
    #ROUTING_STUB
)""",
            ADDRESSES="""(
    {}
)
""".format("\n    ".join(interfaces)), **kwargs)
        TisInitServiceScript.enable(ssh_client)
        TisInitServiceScript.start(ssh_client)


def launch_vm_pair(vm_type='virtio', primary_kwargs=None, secondary_kwargs=None,
                   **launch_vms_kwargs):
    """
    Launch a pair of routed VMs
    one on the primary tenant, and the other on the secondary tenant

    Args:
        vm_type (str):
            one of 'virtio', 'avp', 'dpdk'
        primary_kwargs (dict):
            launch_vms_kwargs for the VM launched under the primary tenant
        secondary_kwargs (dict):
            launch_vms_kwargs for the VM launched under the secondary tenant
        **launch_vms_kwargs:
            additional keyword arguments for launch_vms for both tenants
            overlapping keys will be overridden by primary_kwargs and
            secondary_kwargs
            shall not specify count, ping_vms, auth_info

    Returns (tuple):
        (vm_id_on_primary_tenant, vm_id_on_secondary_tenant)
    """
    LOG.info("Launch a {} test-observer pair of VMs".format(vm_type))
    for invalid_key in ('count', 'ping_vms'):
        if invalid_key in launch_vms_kwargs:
            launch_vms_kwargs.pop(invalid_key)

    primary_kwargs = dict() if not primary_kwargs else primary_kwargs
    secondary_kwargs = dict() if not secondary_kwargs else secondary_kwargs
    if 'auth_info' not in primary_kwargs:
        primary_kwargs['auth_info'] = Tenant.get_primary()
    if 'auth_info' not in secondary_kwargs:
        secondary_kwargs['auth_info'] = Tenant.get_secondary()

    if 'nics' not in primary_kwargs or 'nics' not in secondary_kwargs:
        if vm_type in ['pci-sriov', 'pci-passthrough']:
            raise NotImplementedError(
                "nics has to be provided for pci-sriov and pci-passthrough")

        if vm_type in ['vswitch', 'dpdk', 'vhost']:
            vif_model = 'avp'
        else:
            vif_model = vm_type

        internal_net_id = network_helper.get_internal_net_id()
        for tenant_info in (primary_kwargs, secondary_kwargs):
            auth_info_ = tenant_info['auth_info']
            mgmt_net_id = network_helper.get_mgmt_net_id(auth_info=auth_info_)
            tenant_net_id = network_helper.get_tenant_net_id(
                auth_info=auth_info_)
            nics = [{'net-id': mgmt_net_id},
                    {'net-id': tenant_net_id, 'vif-model': vif_model},
                    {'net-id': internal_net_id, 'vif-model': vif_model}]
            tenant_info['nics'] = nics

    vm_test = launch_vms(vm_type=vm_type, count=1, ping_vms=True,
                         **__merge_dict(launch_vms_kwargs, primary_kwargs)
                         )[0][0]
    vm_observer = launch_vms(vm_type=vm_type, count=1, ping_vms=True,
                             **__merge_dict(launch_vms_kwargs,
                                            secondary_kwargs))[0][0]

    LOG.info("Route the {} test-observer VM pair".format(vm_type))
    if vm_type in ('dpdk', 'vhost', 'vswitch'):
        setup_avr_routing(vm_test, vm_type=vm_type)
        setup_avr_routing(vm_observer, vm_type=vm_type)
    else:
        # vm_type in ('virtio', 'avp'):
        setup_kernel_routing(vm_test)
        setup_kernel_routing(vm_observer)

    route_vm_pair(vm_test, vm_observer)

    return vm_test, vm_observer


def get_all_vms(field='ID', con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get VMs for all tenants in the systems

    Args:
        field:
        con_ssh:
        auth_info

    Returns (list): list of all vms on the system

    """
    return get_vms(field=field, all_projects=True, long=False, con_ssh=con_ssh,
                   auth_info=auth_info)


def get_vms_info(fields, vms=None, con_ssh=None, long=True, all_projects=True,
                 host=None,
                 auth_info=Tenant.get('admin')):
    """
    Get vms values for given fields
    Args:
        fields (str|list|tuple):
        vms:
        con_ssh:
        long:
        all_projects:
        host
        auth_info:

    Returns (dict): vm as key, values for given fields as value
        Examples:
            input: fields = [field1, field2]
            output: {vm_1: [vm1_field1_value, vm1_field2_value],
                    vm_2: [vm2_field1_value, vm2_field2_value]}

    """
    if isinstance(fields, str):
        fields = (fields,)
    fields = ['ID'] + list(fields)

    values = get_vms(vms=vms, field=fields, con_ssh=con_ssh, long=long,
                     all_projects=all_projects, host=host,
                     auth_info=auth_info)
    vm_ids = values.pop(0)
    values = list(zip(*values))
    results = {vm_ids[i]: values[i] for i in range(len(vm_ids))}

    return results


def get_vms(vms=None, field='ID', long=False, all_projects=True, host=None,
            project=None, project_domain=None,
            strict=True, regex=False, con_ssh=None, auth_info=None, **kwargs):
    """
    get a list of VM IDs or Names for given tenant in auth_info param.

    Args:
        vms (list): filter vms from this list if not None
        field (str|tuple|list): 'ID' or 'Name'
        con_ssh (SSHClient): controller SSHClient.
        auth_info (dict): such as ones in auth.py: auth.ADMIN, auth.TENANT1
        long (bool): whether to use --long in cmd
        project (str)
        project_domain (str)
        all_projects (bool): whether to use --a in cmd
        host (str): value for --host arg in cmd
        strict (bool): applies to search for value(s) specified in kwargs
        regex (bool): whether to use regular expression to search for the
            kwargs value(s)
        **kwargs: header/value pair to filter out the vms

    Returns (list): list of VMs for tenant(s).

    """
    args_dict = {'--long': long,
                 '--a': all_projects if auth_info and auth_info[
                     'user'] == 'admin' else None,
                 '--host': host,
                 '--project': project,
                 '--project-domain': project_domain}
    args = common.parse_args(args_dict)
    table_ = table_parser.table(
        cli.openstack('server list', args, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    if vms:
        table_ = table_parser.filter_table(table_, ID=vms)

    return table_parser.get_multi_values(table_, field, strict=strict,
                                         regex=regex, **kwargs)


def get_vm_status(vm_id, con_ssh=None, auth_info=Tenant.get('admin')):
    return get_vm_values(vm_id, 'status', strict=True, con_ssh=con_ssh,
                         auth_info=auth_info)[0]


def get_vm_id_from_name(vm_name, con_ssh=None, strict=True, regex=False,
                        fail_ok=False, auth_info=Tenant.get('admin')):
    if not auth_info:
        auth_info = Tenant.get_primary()
    vm_ids = get_vms(name=vm_name, strict=strict, regex=regex, con_ssh=con_ssh,
                     auth_info=auth_info)
    if not vm_ids:
        err_msg = "No vm found with name: {}".format(vm_name)
        LOG.info(err_msg)
        if fail_ok:
            return ''
        raise exceptions.VMError(err_msg)

    return vm_ids[0]


def get_vm_name_from_id(vm_id, con_ssh=None, auth_info=None):
    return get_vm_values(vm_id, fields='name', con_ssh=con_ssh,
                         auth_info=auth_info)[0]


def get_vm_volumes(vm_id, con_ssh=None, auth_info=None):
    """
    Get volume ids attached to given vm.

    Args:
        vm_id (str):
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple): list of volume ids attached to specific vm

    """
    table_ = table_parser.table(
        cli.openstack('server show', vm_id, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    return _get_vm_volumes(table_)


def get_vm_values(vm_id, fields, strict=True, con_ssh=None,
                  auth_info=Tenant.get('admin')):
    """
    Get vm values via openstack server show
    Args:
        vm_id (str):
        fields (str|list|tuple): fields in openstack server show table
        strict (bool): whether to perform a strict search on given field name
        con_ssh (SSHClient):
        auth_info (dict|None):

    Returns (list): values for given fields

    """
    if isinstance(fields, str):
        fields = [fields]

    table_ = table_parser.table(
        cli.openstack('server show', vm_id, ssh_client=con_ssh,
                      auth_info=auth_info)[1])

    values = []
    for field in fields:
        merge = False
        if field in ('fault',):
            merge = True
        value = table_parser.get_value_two_col_table(table_, field, strict,
                                                     merge_lines=merge)
        if field in ('properties',):
            value = table_parser.convert_value_to_dict(value)
        elif field in ('security_groups',):
            if isinstance(value, str):
                value = [value]
            value = [re.findall("name='(.*)'", v)[0] for v in value]
        values.append(value)
    return values


def get_vm_fault_message(vm_id, con_ssh=None, auth_info=None):
    return get_vm_values(vm_id=vm_id, fields='fault', con_ssh=con_ssh,
                         auth_info=auth_info)[0]


def get_vm_flavor(vm_id, field='id', con_ssh=None, auth_info=None):
    """
    Get flavor id of given vm

    Args:
        vm_id (str):
        field (str): id or name
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (str):

    """
    flavor = get_vm_values(vm_id, fields='flavor', strict=True, con_ssh=con_ssh,
                           auth_info=auth_info)[0]
    flavor_name, flavor_id = flavor.split('(')
    if field == 'id':
        flavor = flavor_id.strip().split(')')[0]
    else:
        flavor = flavor_name.strip()
    return flavor


def get_vm_host(vm_id, con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get host of given vm via openstack server show
    Args:
        vm_id:
        con_ssh:
        auth_info

    Returns (str):

    """
    return get_vm_values(vm_id, ':host', strict=False, con_ssh=con_ssh,
                         auth_info=auth_info)[0]


def get_vms_hosts(vm_ids, con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get vms' hosts via openstack server list
    Args:
        vm_ids:
        con_ssh:
        auth_info

    Returns:

    """
    vms_hosts = get_vms_info(vms=vm_ids, fields='host', auth_info=auth_info,
                             con_ssh=con_ssh)
    vms_hosts = [vms_hosts[vm][0] for vm in vm_ids]

    return vms_hosts


def get_vms_on_host(hostname, field='ID', con_ssh=None,
                    auth_info=Tenant.get('admin')):
    """
    Get vms on given host
    Args:
        field: ID or Name
        hostname (str):Name of a compute node
        con_ssh:
        auth_info

    Returns (list): A list of VMs' ID under a hypervisor

    """
    vms = get_vms(host=hostname, all_projects=True, long=False, con_ssh=con_ssh,
                  auth_info=auth_info, field=field)
    return vms


def get_vms_per_host(vms=None, con_ssh=None, auth_info=Tenant.get('admin')):
    """
    Get vms per host
    Args:
        vms
        con_ssh (SSHClient):
        auth_info (dict)

    Returns (dict):return a dictionary where the host(hypervisor) is the key
    and value are a list of VMs under the host

    """
    vms_hosts = get_vms_info(vms=vms, fields='host', auth_info=auth_info,
                             con_ssh=con_ssh, long=True, all_projects=True)
    vms_per_host = {}
    for vm in vms_hosts:
        host = vms_hosts[vm][0]
        if host in vms_per_host:
            vms_per_host[host].append(vm)
        else:
            vms_per_host[host] = [vm]

    return vms_per_host


def _get_boot_info(table_, vm_id, auth_info=None, con_ssh=None):
    image = table_parser.get_value_two_col_table(table_, 'image')
    if not image:
        volumes = _get_vm_volumes(table_)
        if len(volumes) == 0:
            raise exceptions.VMError(
                "Booted from volume, but no volume id found.")

        from keywords import cinder_helper
        if len(volumes) == 1:
            vol_id = volumes[0]
            vol_name, image_info = cinder_helper.get_volume_show_values(
                vol_id, auth_info=auth_info, con_ssh=con_ssh,
                fields=('name', 'volume_image_metadata'))
            LOG.info("VM booted from volume.")
            return {'type': 'volume', 'id': vol_id, 'volume_name': vol_name,
                    'image_name': image_info['image_name']}
        else:
            LOG.info(
                "VM booted from volume. Multiple volumes found, taking the "
                "first boot-able volume.")
            for volume in volumes:
                bootable, vol_name, image_info = \
                    cinder_helper.get_volume_show_values(
                        volume,
                        fields=('bootable', 'name', 'volume_image_metadata'),
                        auth_info=auth_info, con_ssh=con_ssh)
                if str(bootable).lower() == 'true':
                    return {'type': 'volume', 'id': volume,
                            'volume_name': vol_name,
                            'image_name': image_info['image_name']}

            raise exceptions.VMError(
                "VM {} has no bootable volume attached.".format(vm_id))

    else:
        name, img_uuid = image.strip().split(sep='(')
        return {'type': 'image', 'id': img_uuid.split(sep=')')[0],
                'image_name': name.strip()}


def get_vm_boot_info(vm_id, auth_info=None, con_ssh=None):
    """
    Get vm boot source and id.

    Args:
        vm_id (str):
        auth_info (dict|None):
        con_ssh (SSHClient):

    Returns (dict): VM boot info dict.
        Format: {'type': <boot_source>, 'id': <source_id>}.
        <boot_source> is either 'volume' or 'image'

    """
    table_ = table_parser.table(
        cli.openstack('server show', vm_id, ssh_client=con_ssh,
                      auth_info=auth_info)[1])
    return _get_boot_info(table_, vm_id=vm_id, auth_info=auth_info,
                          con_ssh=con_ssh)


def get_vm_image_name(vm_id, auth_info=None, con_ssh=None):
    """

    Args:
        vm_id (str):
        auth_info (dict):
        con_ssh (SSHClient):

    Returns (str): image name for the vm. If vm booted from volume,
        then image name in volume image metadata will be returned.

    """
    boot_info = get_vm_boot_info(vm_id, auth_info=auth_info, con_ssh=con_ssh)

    return boot_info['image_name']


def _get_vm_volumes(table_):
    """
    Args:
        table_ (dict):

    Returns (list: A list of volume ids from the novashow_table.

    """
    volumes = table_parser.get_value_two_col_table(table_, 'volumes_attached',
                                                   merge_lines=False)
    if not volumes:
        return []

    if isinstance(volumes, str):
        volumes = [volumes]

    return [re.findall("id='(.*)'", volume)[0] for volume in volumes]


def get_vm_instance_name(vm_id, con_ssh=None):
    return get_vm_values(vm_id, ":instance_name", strict=False,
                         con_ssh=con_ssh)[0]
