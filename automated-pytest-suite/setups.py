#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import os
import re
import time
import ipaddress
import configparser

from consts.auth import Tenant, HostLinuxUser, CliAuth, Guest
from consts.stx import Prompt, SUBCLOUD_PATTERN, SysType, GuestImages, Networks
from consts.lab import Labs, add_lab_entry, NatBoxes
from consts.proj_vars import ProjVar
from keywords import host_helper, nova_helper, system_helper, keystone_helper, \
    common, container_helper
from utils import exceptions
from utils.clients.ssh import SSHClient, CONTROLLER_PROMPT, ControllerClient, \
    NATBoxClient, PASSWORD_PROMPT
from utils.tis_log import LOG


def less_than_two_controllers(con_ssh=None,
                              auth_info=Tenant.get('admin_platform')):
    return len(
        system_helper.get_controllers(con_ssh=con_ssh, auth_info=auth_info)) < 2


def setup_tis_ssh(lab):
    con_ssh = ControllerClient.get_active_controller(fail_ok=True)

    if con_ssh is None:
        con_ssh = SSHClient(lab['floating ip'], HostLinuxUser.get_user(),
                            HostLinuxUser.get_password(),
                            CONTROLLER_PROMPT)
        con_ssh.connect(retry=True, retry_timeout=30)
        ControllerClient.set_active_controller(con_ssh)

    return con_ssh


def setup_vbox_tis_ssh(lab):
    if 'external_ip' in lab.keys():

        con_ssh = ControllerClient.get_active_controller(fail_ok=True)
        if con_ssh:
            con_ssh.disconnect()

        con_ssh = SSHClient(lab['external_ip'], HostLinuxUser.get_user(),
                            HostLinuxUser.get_password(),
                            CONTROLLER_PROMPT, port=lab['external_port'])
        con_ssh.connect(retry=True, retry_timeout=30)
        ControllerClient.set_active_controller(con_ssh)

    else:
        con_ssh = setup_tis_ssh(lab)

    return con_ssh


def setup_primary_tenant(tenant):
    Tenant.set_primary(tenant)
    LOG.info("Primary Tenant for test session is set to {}".format(
        Tenant.get(tenant)['tenant']))


def setup_natbox_ssh(natbox, con_ssh):
    natbox_ip = natbox['ip'] if natbox else None
    if not natbox_ip and not container_helper.is_stx_openstack_deployed(
            con_ssh=con_ssh):
        LOG.info(
            "stx-openstack is not applied and natbox is unspecified. Skip "
            "natbox config.")
        return None

    NATBoxClient.set_natbox_client(natbox_ip)
    nat_ssh = NATBoxClient.get_natbox_client()
    ProjVar.set_var(natbox_ssh=nat_ssh)

    setup_keypair(con_ssh=con_ssh, natbox_client=nat_ssh)

    return nat_ssh


def setup_keypair(con_ssh, natbox_client=None):
    """
    copy private keyfile from controller-0:/opt/platform to natbox: priv_keys/
    Args:
        natbox_client (SSHClient): NATBox client
        con_ssh (SSHClient)
    """
    """
    copy private keyfile from controller-0:/opt/platform to natbox: priv_keys/
    Args:
        natbox_client (SSHClient): NATBox client
        con_ssh (SSHClient)
    """
    if not container_helper.is_stx_openstack_deployed(con_ssh=con_ssh):
        LOG.info("stx-openstack is not applied. Skip nova keypair config.")
        return

    # ssh private key should now exist under keyfile_path
    if not natbox_client:
        natbox_client = NATBoxClient.get_natbox_client()

    LOG.info("scp key file from controller to NATBox")
    # keyfile path that can be specified in testcase config
    keyfile_stx_origin = os.path.normpath(ProjVar.get_var('STX_KEYFILE_PATH'))

    # keyfile will always be copied to sysadmin home dir first and update file
    # permission
    keyfile_stx_final = os.path.normpath(
        ProjVar.get_var('STX_KEYFILE_SYS_HOME'))
    public_key_stx = '{}.pub'.format(keyfile_stx_final)

    # keyfile will also be saved to /opt/platform as well, so it won't be
    # lost during system upgrade.
    keyfile_opt_pform = '/opt/platform/{}'.format(
        os.path.basename(keyfile_stx_final))

    # copy keyfile to following NatBox location. This can be specified in
    # testcase config
    keyfile_path_natbox = os.path.normpath(
        ProjVar.get_var('NATBOX_KEYFILE_PATH'))

    auth_info = Tenant.get_primary()
    keypair_name = auth_info.get('nova_keypair',
                                 'keypair-{}'.format(auth_info['user']))
    nova_keypair = nova_helper.get_keypairs(name=keypair_name,
                                            auth_info=auth_info)

    linux_user = HostLinuxUser.get_user()
    nonroot_group = _get_nonroot_group(con_ssh=con_ssh, user=linux_user)
    if not con_ssh.file_exists(keyfile_stx_final):
        with host_helper.ssh_to_host('controller-0',
                                     con_ssh=con_ssh) as con_0_ssh:
            if not con_0_ssh.file_exists(keyfile_opt_pform):
                if con_0_ssh.file_exists(keyfile_stx_origin):
                    # Given private key file exists. Need to ensure public
                    # key exists in same dir.
                    if not con_0_ssh.file_exists('{}.pub'.format(
                            keyfile_stx_origin)) and not nova_keypair:
                        raise FileNotFoundError(
                            '{}.pub is not found'.format(keyfile_stx_origin))
                else:
                    # Need to generate ssh key
                    if nova_keypair:
                        raise FileNotFoundError(
                            "Cannot find private key for existing nova "
                            "keypair {}".format(nova_keypair))

                    con_0_ssh.exec_cmd("ssh-keygen -f '{}' -t rsa -N ''".format(
                        keyfile_stx_origin), fail_ok=False)
                    if not con_0_ssh.file_exists(keyfile_stx_origin):
                        raise FileNotFoundError(
                            "{} not found after ssh-keygen".format(
                                keyfile_stx_origin))

                # keyfile_stx_origin and matching public key should now exist
                # on controller-0
                # copy keyfiles to home dir and opt platform dir
                con_0_ssh.exec_cmd(
                    'cp {} {}'.format(keyfile_stx_origin, keyfile_stx_final),
                    fail_ok=False)
                con_0_ssh.exec_cmd(
                    'cp {}.pub {}'.format(keyfile_stx_origin, public_key_stx),
                    fail_ok=False)
                con_0_ssh.exec_sudo_cmd(
                    'cp {} {}'.format(keyfile_stx_final, keyfile_opt_pform),
                    fail_ok=False)

            # Make sure owner is sysadmin
            # If private key exists in opt platform, then it must also exist
            # in home dir
            con_0_ssh.exec_sudo_cmd(
                'chown {}:{} {}'.format(linux_user, nonroot_group,
                                        keyfile_stx_final),
                fail_ok=False)

        # ssh private key should now exists under home dir and opt platform
        # on controller-0
        if con_ssh.get_hostname() != 'controller-0':
            # copy file from controller-0 home dir to controller-1
            con_ssh.scp_on_dest(source_user=HostLinuxUser.get_user(),
                                source_ip='controller-0',
                                source_path=keyfile_stx_final,
                                source_pswd=HostLinuxUser.get_password(),
                                dest_path=keyfile_stx_final, timeout=60)

    if not nova_keypair:
        LOG.info("Create nova keypair {} using public key {}".
                 format(nova_keypair, public_key_stx))
        if not con_ssh.file_exists(public_key_stx):
            con_ssh.scp_on_dest(source_user=HostLinuxUser.get_user(),
                                source_ip='controller-0',
                                source_path=public_key_stx,
                                source_pswd=HostLinuxUser.get_password(),
                                dest_path=public_key_stx, timeout=60)
            con_ssh.exec_sudo_cmd('chown {}:{} {}'.format(
                linux_user, nonroot_group, public_key_stx),
                fail_ok=False)

        if ProjVar.get_var('REMOTE_CLI'):
            dest_path = os.path.join(ProjVar.get_var('TEMP_DIR'),
                                     os.path.basename(public_key_stx))
            common.scp_from_active_controller_to_localhost(
                source_path=public_key_stx, dest_path=dest_path, timeout=60)
            public_key_stx = dest_path
            LOG.info("Public key file copied to localhost: {}".format(
                public_key_stx))

        nova_helper.create_keypair(keypair_name, public_key=public_key_stx,
                                   auth_info=auth_info)

    natbox_client.exec_cmd(
        'mkdir -p {}'.format(os.path.dirname(keyfile_path_natbox)))
    tis_ip = ProjVar.get_var('LAB').get('floating ip')
    for i in range(10):
        try:
            natbox_client.scp_on_dest(source_ip=tis_ip,
                                      source_user=HostLinuxUser.get_user(),
                                      source_pswd=HostLinuxUser.get_password(),
                                      source_path=keyfile_stx_final,
                                      dest_path=keyfile_path_natbox,
                                      timeout=120)
            LOG.info("private key is copied to NatBox: {}".format(
                keyfile_path_natbox))
            break
        except exceptions.SSHException as e:
            if i == 9:
                raise

            LOG.info(e.__str__())
            time.sleep(10)


def _get_nonroot_group(con_ssh, user=None):
    if not user:
        user = HostLinuxUser.get_user()
    groups = con_ssh.exec_cmd('groups {}'.format(user), fail_ok=False)[1]
    err = 'Please ensure linux_user {} belongs to both root and non_root ' \
          'groups'.format(user)
    if 'root' not in groups:
        raise ValueError(err)

    groups = groups.split(': ')[-1].split()
    for group in groups:
        if group.strip() != 'root':
            return group

    raise ValueError('Please ensure linux_user {} belongs to both root '
                     'and at least one non-root groups'.format(user))


def get_lab_dict(labname):
    labname = labname.strip().lower().replace('-', '_')
    labs = get_labs_list()

    for lab in labs:
        if labname in lab.get('name').replace('-', '_').lower().strip() \
            or labname == lab.get('short_name').replace('-', '_').\
                lower().strip() or labname == lab.get('floating ip'):
            return lab
    else:
        return add_lab_entry(labname)


def get_labs_list():
    labs = [getattr(Labs, item) for item in dir(Labs) if
            not item.startswith('__')]
    labs = [lab_ for lab_ in labs if isinstance(lab_, dict)]
    return labs


def get_natbox_dict(natboxname, user=None, password=None, prompt=None):
    natboxname = natboxname.lower().strip()
    natboxes = [getattr(NatBoxes, item) for item in dir(NatBoxes) if
                item.startswith('NAT_')]

    for natbox in natboxes:
        if natboxname.replace('-', '_') in natbox.get('name').\
                replace('-', '_') or natboxname == natbox.get('ip'):
            return natbox
    else:
        if __get_ip_version(natboxname) == 6:
            raise ValueError('Only IPv4 address is supported for now')

        return NatBoxes.add_natbox(ip=natboxname, user=user,
                                   password=password, prompt=prompt)


def get_tenant_dict(tenantname):
    # tenantname = tenantname.lower().strip().replace('_', '').replace('-', '')
    tenants = [getattr(Tenant, item) for item in dir(Tenant) if
               not item.startswith('_') and item.isupper()]

    for tenant in tenants:
        if tenantname == tenant.get('tenant').replace('_', '').replace('-', ''):
            return tenant
    else:
        raise ValueError("{} is not a valid input".format(tenantname))


def collect_tis_logs(con_ssh):
    common.collect_software_logs(con_ssh=con_ssh)


def get_tis_timestamp(con_ssh):
    return con_ssh.exec_cmd('date +"%T"')[1]


def set_build_info(con_ssh):
    system_helper.get_build_info(con_ssh=con_ssh)


def _rsync_files_to_con1(con_ssh=None, central_region=False,
                         file_to_check=None):
    region = 'RegionOne' if central_region else None
    auth_info = Tenant.get('admin_platform', dc_region=region)
    if less_than_two_controllers(auth_info=auth_info, con_ssh=con_ssh):
        LOG.info("Less than two controllers on system. Skip copying file to "
                 "controller-1.")
        return

    LOG.info("rsync test files from controller-0 to controller-1 if not "
             "already done")
    stx_home = HostLinuxUser.get_home()
    if not file_to_check:
        file_to_check = '{}/images/tis-centos-guest.img'.format(stx_home)
    try:
        with host_helper.ssh_to_host("controller-1",
                                     con_ssh=con_ssh) as con_1_ssh:
            if con_1_ssh.file_exists(file_to_check):
                LOG.info(
                    "Test files already exist on controller-1. Skip rsync.")
                return

    except Exception as e:
        LOG.error(
            "Cannot ssh to controller-1. Skip rsync. "
            "\nException caught: {}".format(e.__str__()))
        return

    cmd = "rsync -avr -e 'ssh -o UserKnownHostsFile=/dev/null -o " \
          "StrictHostKeyChecking=no ' " \
          "{}/* controller-1:{}".format(stx_home, stx_home)

    timeout = 1800
    with host_helper.ssh_to_host("controller-0", con_ssh=con_ssh) as con_0_ssh:
        LOG.info("rsync files from controller-0 to controller-1...")
        con_0_ssh.send(cmd)

        end_time = time.time() + timeout
        while time.time() < end_time:
            index = con_0_ssh.expect(
                [con_0_ssh.prompt, PASSWORD_PROMPT, Prompt.ADD_HOST],
                timeout=timeout,
                searchwindowsize=100)
            if index == 2:
                con_0_ssh.send('yes')

            if index == 1:
                con_0_ssh.send(HostLinuxUser.get_password())

            if index == 0:
                output = int(con_0_ssh.exec_cmd('echo $?')[1])
                if output in [0, 23]:
                    LOG.info(
                        "Test files are successfully copied to controller-1 "
                        "from controller-0")
                    break
                else:
                    raise exceptions.SSHExecCommandFailed(
                        "Failed to rsync files from controller-0 to "
                        "controller-1")

        else:
            raise exceptions.TimeoutException(
                "Timed out rsync files to controller-1")


def copy_test_files():
    con_ssh = None
    central_region = False
    if ProjVar.get_var('IS_DC'):
        _rsync_files_to_con1(
            con_ssh=ControllerClient.get_active_controller(
                name=ProjVar.get_var('PRIMARY_SUBCLOUD')),
            file_to_check='~/heat/README',
            central_region=central_region)
        con_ssh = ControllerClient.get_active_controller(name='RegionOne')
        central_region = True

    _rsync_files_to_con1(con_ssh=con_ssh, central_region=central_region)


def get_auth_via_openrc(con_ssh, use_telnet=False, con_telnet=None):
    valid_keys = ['OS_AUTH_URL',
                  'OS_ENDPOINT_TYPE',
                  'CINDER_ENDPOINT_TYPE',
                  'OS_USER_DOMAIN_NAME',
                  'OS_PROJECT_DOMAIN_NAME',
                  'OS_IDENTITY_API_VERSION',
                  'OS_REGION_NAME',
                  'OS_INTERFACE',
                  'OS_KEYSTONE_REGION_NAME']

    client = con_telnet if use_telnet and con_telnet else con_ssh
    code, output = client.exec_cmd('cat /etc/platform/openrc')
    if code != 0:
        return None

    lines = output.splitlines()
    auth_dict = {}
    for line in lines:
        if 'export' in line:
            if line.split('export ')[1].split(sep='=')[0] in valid_keys:
                key, value = line.split(sep='export ')[1].split(sep='=')
                auth_dict[key.strip().upper()] = value.strip()

    return auth_dict


def is_https(con_ssh):
    return keystone_helper.is_https_enabled(con_ssh=con_ssh, source_openrc=True,
                                            auth_info=Tenant.get(
                                                'admin_platform'))


def get_version_and_patch_info():
    version = ProjVar.get_var('SW_VERSION')[0]
    info = 'Software Version: {}\n'.format(version)

    patches = ProjVar.get_var('PATCH')
    if patches:
        info += 'Patches:\n{}\n'.format('\n'.join(patches))

    # LOG.info("SW Version and Patch info: {}".format(info))
    return info


def get_system_mode_from_lab_info(lab, multi_region_lab=False,
                                  dist_cloud_lab=False):
    """

    Args:
        lab:
        multi_region_lab:
        dist_cloud_lab:

    Returns:

    """

    if multi_region_lab:
        return SysType.MULTI_REGION
    elif dist_cloud_lab:
        return SysType.DISTRIBUTED_CLOUD

    elif 'system_mode' not in lab:
        if 'storage_nodes' in lab:
            return SysType.STORAGE
        elif 'compute_nodes' in lab:
            return SysType.REGULAR

        elif len(lab['controller_nodes']) > 1:
            return SysType.AIO_DX
        else:
            return SysType.AIO_SX

    elif 'system_mode' in lab:
        if "simplex" in lab['system_mode']:
            return SysType.AIO_SX
        else:
            return SysType.AIO_DX
    else:
        LOG.warning(
            "Can not determine the lab to install system type based on "
            "provided information. Lab info: {}"
            .format(lab))
        return None


def add_ping_failure(test_name):
    file_path = '{}{}'.format(ProjVar.get_var('PING_FAILURE_DIR'),
                              'ping_failures.txt')
    with open(file_path, mode='a') as f:
        f.write(test_name + '\n')


def set_region(region=None):
    """
    set global variable region.
    This needs to be called after CliAuth.set_vars, since the custom region
    value needs to override what is
    specified in openrc file.

    local region and auth url is saved in CliAuth, while the remote region
    and auth url is saved in Tenant.

    Args:
        region: region to set

    """
    local_region = CliAuth.get_var('OS_REGION_NAME')
    if not region:
        if ProjVar.get_var('IS_DC'):
            region = 'SystemController'
        else:
            region = local_region
    Tenant.set_region(region=region)
    ProjVar.set_var(REGION=region)
    if re.search(SUBCLOUD_PATTERN, region):
        # Distributed cloud, lab specified is a subcloud.
        urls = keystone_helper.get_endpoints(region=region, field='URL',
                                             interface='internal',
                                             service_name='keystone')
        if not urls:
            raise ValueError(
                "No internal endpoint found for region {}. Invalid value for "
                "--region with specified lab."
                "sub-cloud tests can be run on controller, but not the other "
                "way round".format(
                    region))
        Tenant.set_platform_url(urls[0])


def set_sys_type(con_ssh):
    sys_type = system_helper.get_sys_type(con_ssh=con_ssh)
    ProjVar.set_var(SYS_TYPE=sys_type)


def arp_for_fip(lab, con_ssh):
    fip = lab['floating ip']
    code, output = con_ssh.exec_cmd(
        'ip addr | grep -B 4 {} | grep --color=never BROADCAST'.format(fip))
    if output:
        target_str = output.splitlines()[-1]
        dev = target_str.split(sep=': ')[1].split('@')[0]
        con_ssh.exec_cmd('arping -c 3 -A -q -I {} {}'.format(dev, fip))


def __get_ip_version(ip_addr):
    try:
        ip_version = ipaddress.ip_address(ip_addr).version
    except ValueError:
        ip_version = None

    return ip_version


def setup_testcase_config(testcase_config, lab=None, natbox=None):
    fip_error = 'A valid IPv4 OAM floating IP has to be specified via ' \
                'cmdline option --lab=<oam_floating_ip>, ' \
                'or testcase config file has to be provided via ' \
                '--testcase-config with oam_floating_ip ' \
                'specified under auth_platform section.'
    if not testcase_config:
        if not lab:
            raise ValueError(fip_error)
        return lab, natbox

    testcase_config = os.path.expanduser(testcase_config)
    auth_section = 'auth'
    guest_image_section = 'guest_image'
    guest_networks_section = 'guest_networks'
    guest_keypair_section = 'guest_keypair'
    natbox_section = 'natbox'

    config = configparser.ConfigParser()
    config.read(testcase_config)

    #
    # Update global variables for auth section
    #
    # Update OAM floating IP
    if lab:
        fip = lab.get('floating ip')
        config.set(auth_section, 'oam_floating_ip', fip)
    else:
        fip = config.get(auth_section, 'oam_floating_ip', fallback='').strip()
        lab = get_lab_dict(fip)

    if __get_ip_version(fip) != 4:
        raise ValueError(fip_error)

    # controller-0 oam ip is updated with best effort if a valid IPv4 IP is
    # provided
    if not lab.get('controller-0 ip') and config.get(auth_section,
                                                     'controller0_oam_ip',
                                                     fallback='').strip():
        con0_ip = config.get(auth_section, 'controller0_oam_ip').strip()
        if __get_ip_version(con0_ip) == 4:
            lab['controller-0 ip'] = con0_ip
        else:
            LOG.info(
                "controller0_oam_ip specified in testcase config file is not "
                "a valid IPv4 address. Ignore.")

    # Update linux user credentials
    if config.get(auth_section, 'linux_username', fallback='').strip():
        HostLinuxUser.set_user(
            config.get(auth_section, 'linux_username').strip())
    if config.get(auth_section, 'linux_user_password', fallback='').strip():
        HostLinuxUser.set_password(
            config.get(auth_section, 'linux_user_password').strip())

    # Update openstack keystone user credentials
    auth_dict_map = {
        'platform_admin': 'admin_platform',
        'admin': 'admin',
        'test1': 'tenant1',
        'test2': 'tenant2',
    }
    for conf_prefix, dict_name in auth_dict_map.items():
        kwargs = {}
        default_auth = Tenant.get(dict_name)
        conf_user = config.get(auth_section, '{}_username'.format(conf_prefix),
                               fallback='').strip()
        conf_password = config.get(auth_section,
                                   '{}_password'.format(conf_prefix),
                                   fallback='').strip()
        conf_project = config.get(auth_section,
                                  '{}_project_name'.format(conf_prefix),
                                  fallback='').strip()
        conf_domain = config.get(auth_section,
                                 '{}_domain_name'.format(conf_prefix),
                                 fallback='').strip()
        conf_keypair = config.get(auth_section,
                                  '{}_nova_keypair'.format(conf_prefix),
                                  fallback='').strip()
        if conf_user and conf_user != default_auth.get('user'):
            kwargs['username'] = conf_user
        if conf_password and conf_password != default_auth.get('password'):
            kwargs['password'] = conf_password
        if conf_project and conf_project != default_auth.get('tenant'):
            kwargs['tenant'] = conf_project
        if conf_domain and conf_domain != default_auth.get('domain'):
            kwargs['domain'] = conf_domain
        if conf_keypair and conf_keypair != default_auth.get('nova_keypair'):
            kwargs['nova_keypair'] = conf_keypair

        if kwargs:
            Tenant.update(dict_name, **kwargs)

    #
    # Update global variables for natbox section
    #
    natbox_host = config.get(natbox_section, 'natbox_host', fallback='').strip()
    natbox_user = config.get(natbox_section, 'natbox_user', fallback='').strip()
    natbox_password = config.get(natbox_section, 'natbox_password',
                                 fallback='').strip()
    natbox_prompt = config.get(natbox_section, 'natbox_prompt',
                               fallback='').strip()
    if natbox_host and (not natbox or natbox_host != natbox['ip']):
        natbox = get_natbox_dict(natbox_host, user=natbox_user,
                                 password=natbox_password, prompt=natbox_prompt)
    #
    # Update global variables for guest_image section
    #
    img_file_dir = config.get(guest_image_section, 'img_file_dir',
                              fallback='').strip()
    glance_image_name = config.get(guest_image_section, 'glance_image_name',
                                   fallback='').strip()
    img_file_name = config.get(guest_image_section, 'img_file_name',
                               fallback='').strip()
    img_disk_format = config.get(guest_image_section, 'img_disk_format',
                                 fallback='').strip()
    min_disk_size = config.get(guest_image_section, 'min_disk_size',
                               fallback='').strip()
    img_container_format = config.get(guest_image_section,
                                      'img_container_format',
                                      fallback='').strip()
    image_ssh_user = config.get(guest_image_section, 'image_ssh_user',
                                fallback='').strip()
    image_ssh_password = config.get(guest_image_section, 'image_ssh_password',
                                    fallback='').strip()

    if img_file_dir and img_file_dir != GuestImages.DEFAULT['image_dir']:
        # Update default image file directory
        img_file_dir = os.path.expanduser(img_file_dir)
        if not os.path.isabs(img_file_dir):
            raise ValueError(
                "Please provide a valid absolute path for img_file_dir "
                "under guest_image section in testcase config file")
        GuestImages.DEFAULT['image_dir'] = img_file_dir

    if glance_image_name and glance_image_name != GuestImages.DEFAULT['guest']:
        # Update default glance image name
        GuestImages.DEFAULT['guest'] = glance_image_name
        if glance_image_name not in GuestImages.IMAGE_FILES:
            # Add guest image info to consts.stx.GuestImages
            if not (img_file_name and img_disk_format and min_disk_size):
                raise ValueError(
                    "img_file_name and img_disk_format under guest_image "
                    "section have to be "
                    "specified in testcase config file")

            img_container_format = img_container_format if \
                img_container_format else 'bare'
            GuestImages.IMAGE_FILES[glance_image_name] = \
                (None, min_disk_size, img_file_name, img_disk_format,
                 img_container_format)

            # Add guest login credentials
            Guest.CREDS[glance_image_name] = {
                'user': image_ssh_user if image_ssh_user else 'root',
                'password': image_ssh_password if image_ssh_password else None,
            }

    #
    # Update global variables for guest_keypair section
    #
    natbox_keypair_dir = config.get(guest_keypair_section, 'natbox_keypair_dir',
                                    fallback='').strip()
    private_key_path = config.get(guest_keypair_section, 'private_key_path',
                                  fallback='').strip()

    if natbox_keypair_dir:
        natbox_keypair_path = os.path.join(natbox_keypair_dir,
                                           'keyfile_{}.pem'.format(
                                               lab['short_name']))
        ProjVar.set_var(NATBOX_KEYFILE_PATH=natbox_keypair_path)
    if private_key_path:
        ProjVar.set_var(STX_KEYFILE_PATH=private_key_path)

    #
    # Update global variables for guest_networks section
    #
    net_name_patterns = {
        'mgmt': config.get(guest_networks_section, 'mgmt_net_name_pattern',
                           fallback='').strip(),
        'data': config.get(guest_networks_section, 'data_net_name_pattern',
                           fallback='').strip(),
        'internal': config.get(guest_networks_section,
                               'internal_net_name_pattern',
                               fallback='').strip(),
        'external': config.get(guest_networks_section,
                               'external_net_name_pattern', fallback='').strip()
    }

    for net_type, net_name_pattern in net_name_patterns.items():
        if net_name_pattern:
            Networks.set_neutron_net_patterns(net_type=net_type,
                                              net_name_pattern=net_name_pattern)

    return lab, natbox
