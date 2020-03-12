#
# Copyright (c) 2019, 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


"""
Container/Application related helper functions for non-kubectl commands.
For example:
- docker commands
- system application-xxx commands
- helm commands

"""

import os
import time
import yaml

from utils import cli, exceptions, table_parser
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient
from consts.auth import Tenant
from consts.proj_vars import ProjVar
from consts.stx import AppStatus, Prompt, EventLogID, Container
from consts.filepaths import StxPath
from keywords import system_helper, host_helper


def exec_helm_upload_cmd(tarball, repo=None, timeout=120, con_ssh=None,
                         fail_ok=False):
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    if not repo:
        repo = 'starlingx'
    cmd = 'helm-upload {} {}'.format(repo, tarball)
    con_ssh.send(cmd)
    pw_prompt = Prompt.PASSWORD_PROMPT
    prompts = [con_ssh.prompt, pw_prompt]

    index = con_ssh.expect(prompts, timeout=timeout, searchwindowsize=100,
                           fail_ok=fail_ok)
    if index == 1:
        con_ssh.send(con_ssh.password)
        prompts.remove(pw_prompt)
        con_ssh.expect(prompts, timeout=timeout, searchwindowsize=100,
                       fail_ok=fail_ok)

    code, output = con_ssh._process_exec_result(rm_date=True,
                                                get_exit_code=True)
    if code != 0 and not fail_ok:
        raise exceptions.SSHExecCommandFailed(
            "Non-zero return code for cmd: {}. Output: {}".
            format(cmd, output))

    return code, output


def exec_docker_cmd(sub_cmd, args, timeout=120, con_ssh=None, fail_ok=False):
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    cmd = 'docker {} {}'.format(sub_cmd, args)
    code, output = con_ssh.exec_sudo_cmd(cmd, expect_timeout=timeout,
                                         fail_ok=fail_ok)

    return code, output


def upload_helm_charts(tar_file, repo=None, delete_first=False, con_ssh=None,
                       timeout=120, fail_ok=False):
    """
    Upload helm charts via helm-upload cmd
    Args:
        tar_file:
        repo
        delete_first:
        con_ssh:
        timeout:
        fail_ok:

    Returns (tuple):
        (0, <path_to_charts>)
        (1, <std_err>)
        (2, <hostname for host that does not have helm charts in expected dir>)

    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    helm_dir = os.path.normpath(StxPath.HELM_CHARTS_DIR)
    if not repo:
        repo = 'starlingx'
    file_path = os.path.join(helm_dir, repo, os.path.basename(tar_file))
    current_host = con_ssh.get_hostname()
    controllers = [current_host]
    if not system_helper.is_aio_simplex(con_ssh=con_ssh):
        con_name = 'controller-1' if controllers[
                                         0] == 'controller-0' else \
            'controller-0'
        controllers.append(con_name)

    if delete_first:
        for host in controllers:
            with host_helper.ssh_to_host(hostname=host,
                                         con_ssh=con_ssh) as host_ssh:
                if host_ssh.file_exists(file_path):
                    host_ssh.exec_sudo_cmd('rm -f {}'.format(file_path))

    code, output = exec_helm_upload_cmd(tarball=tar_file, repo=repo,
                                        timeout=timeout, con_ssh=con_ssh,
                                        fail_ok=fail_ok)
    if code != 0:
        return 1, output

    file_exist = con_ssh.file_exists(file_path)
    if not file_exist:
        raise exceptions.ContainerError(
            "{} not found on {} after helm-upload".format(file_path,
                                                          current_host))

    LOG.info("Helm charts {} uploaded successfully".format(file_path))
    return 0, file_path


def upload_app(tar_file, app_name=None, app_version=None, check_first=True,
               fail_ok=False, uploaded_timeout=300,
               con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Upload an application via 'system application-upload'
    Args:
        app_name:
        app_version:
        tar_file:
        check_first
        fail_ok:
        uploaded_timeout:
        con_ssh:
        auth_info:

    Returns:

    """
    if check_first and get_apps(application=app_name, con_ssh=con_ssh,
                                auth_info=auth_info):
        msg = '{} already exists. Do nothing.'.format(app_name)
        LOG.info(msg)
        return -1, msg

    args = ''
    if app_name:
        args += '-n {} '.format(app_name)
    if app_version:
        args += '-v {} '.format(app_version)
    args = '{}{}'.format(args, tar_file)
    code, output = cli.system('application-upload', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)

    if code > 0:
        return 1, output

    res = wait_for_apps_status(apps=app_name, status=AppStatus.UPLOADED,
                               timeout=uploaded_timeout,
                               con_ssh=con_ssh, auth_info=auth_info,
                               fail_ok=fail_ok)[0]
    if not res:
        return 2, "{} failed to upload".format(app_name)

    msg = '{} uploaded successfully'.format(app_name)
    LOG.info(msg)
    return 0, msg


def get_apps(field='status', application=None, con_ssh=None,
             auth_info=Tenant.get('admin_platform'),
             rtn_dict=False, **kwargs):
    """
    Get applications values for give apps and fields via system application-list
    Args:
        application (str|list|tuple):
        field (str|list|tuple):
        con_ssh:
        auth_info:
        rtn_dict:
        **kwargs: extra filters other than application

    Returns (list|dict):
        list of list, or
        dict with app name(str) as key and values(list) for given fields for
        each app as value

    """
    table_ = table_parser.table(
        cli.system('application-list', ssh_client=con_ssh, auth_info=auth_info)[
            1])
    if application:
        kwargs['application'] = application

    return table_parser.get_multi_values(table_, fields=field,
                                         rtn_dict=rtn_dict, zip_values=True,
                                         **kwargs)


def get_app_values(app_name, fields, con_ssh=None,
                   auth_info=Tenant.get('admin_platform')):
    """
    Get values from system application-show
    Args:
        app_name:
        fields (str|list|tuple):
        con_ssh:
        auth_info:

    Returns:

    """
    if isinstance(fields, str):
        fields = [fields]

    table_ = table_parser.table(
        cli.system('application-show', app_name, ssh_client=con_ssh,
                   auth_info=auth_info)[1],
        combine_multiline_entry=True)
    values = table_parser.get_multi_values_two_col_table(table_, fields=fields)
    return values


def wait_for_apps_status(apps, status, timeout=360, check_interval=5,
                         fail_ok=False, con_ssh=None,
                         auth_info=Tenant.get('admin_platform')):
    """
    Wait for applications to reach expected status via system application-list
    Args:
        apps:
        status:
        timeout:
        check_interval:
        fail_ok:
        con_ssh:
        auth_info:

    Returns (tuple):

    """
    status = '' if not status else status
    if isinstance(apps, str):
        apps = [apps]
    apps_to_check = list(apps)
    check_failed = []
    end_time = time.time() + timeout

    LOG.info(
        "Wait for {} application(s) to reach status: {}".format(apps, status))
    while time.time() < end_time:
        apps_status = get_apps(application=apps_to_check,
                               field=('application', 'status'), con_ssh=con_ssh,
                               auth_info=auth_info)
        apps_status = {item[0]: item[1] for item in apps_status if item}

        checked = []
        for app in apps_to_check:
            current_app_status = apps_status.get(app, '')
            if current_app_status == status:
                checked.append(app)
            elif current_app_status.endswith('ed'):
                check_failed.append(app)
                checked.append(app)

        apps_to_check = list(set(apps_to_check) - set(checked))
        if not apps_to_check:
            if check_failed:
                msg = '{} failed to reach status - {}'.format(check_failed,
                                                              status)
                LOG.warning(msg)
                if fail_ok:
                    return False, check_failed
                else:
                    raise exceptions.ContainerError(msg)

            LOG.info("{} reached expected status {}".format(apps, status))
            return True, None

        time.sleep(check_interval)

    check_failed += apps_to_check
    msg = '{} did not reach status {} within {}s'.format(check_failed, status,
                                                         timeout)
    LOG.warning(msg)
    if fail_ok:
        return False, check_failed
    raise exceptions.ContainerError(msg)


def apply_app(app_name, check_first=False, fail_ok=False, applied_timeout=300,
              check_interval=10,
              wait_for_alarm_gone=True, con_ssh=None,
              auth_info=Tenant.get('admin_platform')):
    """
    Apply/Re-apply application via system application-apply. Check for status
    reaches 'applied'.
    Args:
        app_name (str):
        check_first:
        fail_ok:
        applied_timeout:
        check_interval:
        con_ssh:
        wait_for_alarm_gone (bool):
        auth_info:

    Returns (tuple):
        (-1, "<app_name> is already applied. Do nothing.")     # only returns
        if check_first=True.
        (0, "<app_name> (re)applied successfully")
        (1, <std_err>)  # cli rejected
        (2, "<app_name> failed to apply")   # did not reach applied status
        after apply.

    """
    if check_first:
        app_status = get_apps(application=app_name, field='status',
                              con_ssh=con_ssh, auth_info=auth_info)
        if app_status and app_status[0] == AppStatus.APPLIED:
            msg = '{} is already applied. Do nothing.'.format(app_name)
            LOG.info(msg)
            return -1, msg

    LOG.info("Apply application: {}".format(app_name))
    code, output = cli.system('application-apply', app_name, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code > 0:
        return 1, output

    res = wait_for_apps_status(apps=app_name, status=AppStatus.APPLIED,
                               timeout=applied_timeout,
                               check_interval=check_interval, con_ssh=con_ssh,
                               auth_info=auth_info, fail_ok=fail_ok)[0]
    if not res:
        return 2, "{} failed to apply".format(app_name)

    if wait_for_alarm_gone:
        alarm_id = EventLogID.CONFIG_OUT_OF_DATE
        if system_helper.wait_for_alarm(alarm_id=alarm_id,
                                        entity_id='controller',
                                        timeout=15, fail_ok=True,
                                        auth_info=auth_info,
                                        con_ssh=con_ssh)[0]:
            system_helper.wait_for_alarm_gone(alarm_id=alarm_id,
                                              entity_id='controller',
                                              timeout=120,
                                              check_interval=10,
                                              con_ssh=con_ssh,
                                              auth_info=auth_info)

    msg = '{} (re)applied successfully'.format(app_name)
    LOG.info(msg)
    return 0, msg


def delete_app(app_name, check_first=True, fail_ok=False, applied_timeout=300,
               con_ssh=None,
               auth_info=Tenant.get('admin_platform')):
    """
    Delete an application via system application-delete. Verify application
    no longer listed.
    Args:
        app_name:
        check_first:
        fail_ok:
        applied_timeout:
        con_ssh:
        auth_info:

    Returns (tuple):
        (-1, "<app_name> does not exist. Do nothing.")
        (0, "<app_name> deleted successfully")
        (1, <std_err>)
        (2, "<app_name> failed to delete")

    """

    if check_first:
        app_vals = get_apps(application=app_name, field='status',
                            con_ssh=con_ssh, auth_info=auth_info)
        if not app_vals:
            msg = '{} does not exist. Do nothing.'.format(app_name)
            LOG.info(msg)
            return -1, msg

    code, output = cli.system('application-delete', app_name,
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, output

    res = wait_for_apps_status(apps=app_name, status=None,
                               timeout=applied_timeout,
                               con_ssh=con_ssh, auth_info=auth_info,
                               fail_ok=fail_ok)[
        0]
    if not res:
        return 2, "{} failed to delete".format(app_name)

    msg = '{} deleted successfully'.format(app_name)
    LOG.info(msg)
    return 0, msg


def remove_app(app_name, check_first=True, fail_ok=False, applied_timeout=300,
               con_ssh=None,
               auth_info=Tenant.get('admin_platform')):
    """
    Remove applied application via system application-remove. Verify it is in
    'uploaded' status.
    Args:
        app_name (str):
        check_first:
        fail_ok:
        applied_timeout:
        con_ssh:
        auth_info:

    Returns (tuple):
        (-1, "<app_name> is not applied. Do nothing.")
        (0, "<app_name> removed successfully")
        (1, <std_err>)
        (2, "<app_name> failed to remove")  # Did not reach uploaded status

    """

    if check_first:
        app_vals = get_apps(application=app_name, field='status',
                            con_ssh=con_ssh, auth_info=auth_info)
        if not app_vals or app_vals[0] in (AppStatus.UPLOADED,
                                           AppStatus.UPLOAD_FAILED):
            msg = '{} is not applied. Do nothing.'.format(app_name)
            LOG.info(msg)
            return -1, msg

    code, output = cli.system('application-remove', app_name,
                              ssh_client=con_ssh, fail_ok=fail_ok,
                              auth_info=auth_info)
    if code > 0:
        return 1, output

    res = wait_for_apps_status(apps=app_name, status=AppStatus.UPLOADED,
                               timeout=applied_timeout,
                               con_ssh=con_ssh, auth_info=auth_info,
                               fail_ok=fail_ok)[0]
    if not res:
        return 2, "{} failed to remove".format(app_name)

    msg = '{} removed successfully'.format(app_name)
    LOG.info(msg)
    return 0, msg


def get_docker_reg_addr(con_ssh=None):
    """
    Get local docker registry ip address in docker conf file.
    Args:
        con_ssh:

    Returns (str):

    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    output = con_ssh.exec_cmd(
        'grep --color=never "addr: " {}'.format(StxPath.DOCKER_CONF),
        fail_ok=False)[1]
    reg_addr = output.split('addr: ')[1].strip()
    return reg_addr


def pull_docker_image(name, tag=None, digest=None, con_ssh=None, timeout=300,
                      fail_ok=False):
    """
    Pull docker image via docker image pull. Verify image is listed in docker
    image list.
    Args:
        name:
        tag:
        digest:
        con_ssh:
        timeout:
        fail_ok:

    Returns (tuple):
        (0, <docker image ID>)
        (1, <std_err>)

    """

    args = '{}'.format(name.strip())
    if tag:
        args += ':{}'.format(tag)
    elif digest:
        args += '@{}'.format(digest)

    LOG.info("Pull docker image {}".format(args))
    code, out = exec_docker_cmd('image pull', args, timeout=timeout,
                                fail_ok=fail_ok, con_ssh=con_ssh)
    if code != 0:
        return 1, out

    image_id = get_docker_images(repo=name, tag=tag, field='IMAGE ID',
                                 con_ssh=con_ssh, fail_ok=False)[0]
    LOG.info(
        'docker image {} successfully pulled. ID: {}'.format(args, image_id))

    return 0, image_id


def login_to_docker(registry=None, user=None, password=None, con_ssh=None,
                    fail_ok=False):
    """
    Login to docker registry
    Args:
        registry (str|None): default docker registry will be used when None
        user (str|None): admin user will be used when None
        password (str|None): admin password will be used when None
        con_ssh (SSHClient|None):
        fail_ok (bool):

    Returns (tuple):
        (0, <cmd_args>(str))    # login succeeded
        (1, <std_err>(str))     # login failed

    """
    if not user:
        user = 'admin'
    if not password:
        password = Tenant.get('admin_platform').get('password')
    if not registry:
        registry = Container.LOCAL_DOCKER_REG

    args = '-u {} -p {} {}'.format(user, password, registry)
    LOG.info("Login to docker registry {}".format(registry))
    code, out = exec_docker_cmd('login', args, timeout=60, fail_ok=fail_ok,
                                con_ssh=con_ssh)
    if code != 0:
        return 1, out

    LOG.info('Logged into docker registry successfully: {}'.format(registry))
    return 0, args


def push_docker_image(name, tag=None, login_registry=None, con_ssh=None,
                      timeout=300, fail_ok=False):
    """
    Push docker image via docker image push.
    Args:
        name:
        tag:
        login_registry (str|None): when set, login to given docker registry
        before push
        con_ssh:
        timeout:
        fail_ok:

    Returns (tuple):
        (0, <args_used>)
        (1, <std_err>)

    """
    args = '{}'.format(name.strip())
    if tag:
        args += ':{}'.format(tag)

    if login_registry:
        login_to_docker(registry=login_registry, con_ssh=con_ssh)

    LOG.info("Push docker image: {}".format(args))
    code, out = exec_docker_cmd('image push', args, timeout=timeout,
                                fail_ok=fail_ok, con_ssh=con_ssh)
    if code != 0:
        return 1, out

    LOG.info('docker image {} successfully pushed.'.format(args))
    return 0, args


def tag_docker_image(source_image, target_name, source_tag=None,
                     target_tag=None, con_ssh=None, timeout=300,
                     fail_ok=False):
    """
    Tag docker image via docker image tag. Verify image is tagged via docker
    image list.
    Args:
        source_image:
        target_name:
        source_tag:
        target_tag:
        con_ssh:
        timeout:
        fail_ok:

    Returns:
        (0, <target_args>)
        (1, <std_err>)

    """
    source_args = source_image.strip()
    if source_tag:
        source_args += ':{}'.format(source_tag)

    target_args = target_name.strip()
    if target_tag:
        target_args += ':{}'.format(target_tag)

    LOG.info("Tag docker image {} as {}".format(source_args, target_args))
    args = '{} {}'.format(source_args, target_args)
    code, out = exec_docker_cmd('image tag', args, timeout=timeout,
                                fail_ok=fail_ok, con_ssh=con_ssh)
    if code != 0:
        return 1, out

    if not get_docker_images(repo=target_name, tag=target_tag, con_ssh=con_ssh,
                             fail_ok=False):
        raise exceptions.ContainerError(
            "Docker image {} is not listed after tagging {}".format(
                target_name, source_image))

    LOG.info('docker image {} successfully tagged as {}.'.format(source_args,
                                                                 target_args))
    return 0, target_args


def remove_docker_images_with_pattern(pattern, con_ssh=None, timeout=300):
    """
    Remove docker image(s) via docker image rm matching 'pattern'
    Args:
        pattern:
        con_ssh:
        timeout:

    Returns (tuple):
        (0, <std_out>)
        (1, <std_err>)

    """

    LOG.info("Remove docker images matching pattern: {}".format(pattern))

    args = " | grep " + pattern + " | awk '{print $3}' "
    code, out = exec_docker_cmd("images", args, timeout=timeout, fail_ok=True, con_ssh=con_ssh)

    if out:
        image_list = out.splitlines()
        code, out = remove_docker_images(image_list, force=True, con_ssh=con_ssh)

    return code, out


def remove_docker_images(images, force=False, con_ssh=None, timeout=300,
                         fail_ok=False):
    """
    Remove docker image(s) via docker image rm
    Args:
        images (str|tuple|list):
        force (bool):
        con_ssh:
        timeout:
        fail_ok:

    Returns (tuple):
        (0, <std_out>)
        (1, <std_err>)

    """
    if isinstance(images, str):
        images = (images,)

    LOG.info("Remove docker images: {}".format(images))
    args = ' '.join(images)
    if force:
        args = '--force {}'.format(args)

    code, out = exec_docker_cmd('image rm', args, timeout=timeout,
                                fail_ok=fail_ok, con_ssh=con_ssh)
    return code, out


def get_docker_images(repo=None, tag=None, field='IMAGE ID', con_ssh=None,
                      fail_ok=False):
    """
    get values for given docker image via 'docker image ls <repo>'
    Args:
        repo (str):
        tag (str|None):
        field (str|tuple|list):
        con_ssh:
        fail_ok

    Returns (list|None): return None if no docker images returned at all due
    to cmd failure

    """
    args = None
    if repo:
        args = repo
        if tag:
            args += ':{}'.format(tag)
    code, output = exec_docker_cmd(sub_cmd='image ls', args=args,
                                   fail_ok=fail_ok, con_ssh=con_ssh)
    if code != 0:
        return None

    table_ = table_parser.table_kube(output)
    if not table_['values']:
        if fail_ok:
            return None
        else:
            raise exceptions.ContainerError(
                "docker image {} does not exist".format(args))

    values = table_parser.get_multi_values(table_, fields=field,
                                           zip_values=True)

    return values


def get_helm_overrides(field='overrides namespaces', app_name='stx-openstack',
                       charts=None,
                       auth_info=Tenant.get('admin_platform'), con_ssh=None):
    """
    Get helm overrides values via system helm-override-list
    Args:
        field (str):
        app_name
        charts (None|str|list|tuple):
        auth_info:
        con_ssh:

    Returns (list):

    """
    table_ = table_parser.table(
        cli.system('helm-override-list', app_name, ssh_client=con_ssh,
                   auth_info=auth_info)[1])

    if charts:
        table_ = table_parser.filter_table(table_, **{'chart name': charts})

    vals = table_parser.get_multi_values(table_, fields=field, evaluate=True)

    return vals


def get_helm_override_values(chart, namespace, app_name='stx-openstack',
                             fields=('combined_overrides',),
                             auth_info=Tenant.get('admin_platform'),
                             con_ssh=None):
    """
    Get helm-override values for given chart via system helm-override-show
    Args:
        chart (str):
        namespace (str):
        app_name (str)
        fields (str|tuple|list):
        auth_info:
        con_ssh:

    Returns (list): list of parsed yaml formatted output. e.g., list of dict,
    list of list, list of str

    """
    args = '{} {} {}'.format(app_name, chart, namespace)
    table_ = table_parser.table(
        cli.system('helm-override-show', args, ssh_client=con_ssh,
                   auth_info=auth_info)[1],
        rstrip_value=True)

    if isinstance(fields, str):
        fields = (fields,)

    values = []
    for field in fields:
        value = table_parser.get_value_two_col_table(table_, field=field,
                                                     merge_lines=False)
        values.append(yaml.load('\n'.join(value)))

    return values


def __convert_kv(k, v):
    if '.' not in k:
        return {k: v}
    new_key, new_val = k.rsplit('.', maxsplit=1)
    return __convert_kv(new_key, {new_val: v})


def update_helm_override(chart, namespace, app_name='stx-openstack',
                         yaml_file=None, kv_pairs=None,
                         reset_vals=False, reuse_vals=False,
                         auth_info=Tenant.get('admin_platform'),
                         con_ssh=None, fail_ok=False):
    """
    Update helm_override values for given chart
    Args:
        chart:
        namespace:
        app_name
        yaml_file:
        kv_pairs:
        reset_vals:
        reuse_vals:
        fail_ok
        con_ssh
        auth_info

    Returns (tuple):
        (0, <overrides>(str|list|dict))     # cmd accepted.
        (1, <std_err>)  #  system helm-override-update cmd rejected

    """
    args = '{} {} {}'.format(app_name, chart, namespace)
    if reset_vals:
        args = '--reset-values {}'.format(args)
    if reuse_vals:
        args = '--reuse-values {}'.format(args)
    if yaml_file:
        args = '--values {} {}'.format(yaml_file, args)
    if kv_pairs:
        cmd_overrides = ','.join(
            ['{}={}'.format(k, v) for k, v in kv_pairs.items()])
        args = '--set {} {}'.format(cmd_overrides, args)

    code, output = cli.system('helm-override-update', args, ssh_client=con_ssh,
                              fail_ok=fail_ok, auth_info=auth_info)
    if code != 0:
        return 1, output

    table_ = table_parser.table(output, rstrip_value=True)
    overrides = table_parser.get_value_two_col_table(table_, 'user_overrides')
    overrides = yaml.load('\n'.join(overrides))
    # yaml.load converts str to bool, int, float; but does not convert
    # None type. Updates are not verified here since it is rather complicated
    # to verify properly.
    LOG.info("Helm-override updated : {}".format(overrides))

    return 0, overrides


def is_stx_openstack_deployed(applied_only=False, con_ssh=None,
                              auth_info=Tenant.get('admin_platform'),
                              force_check=False):
    """
    Whether stx-openstack application  is deployed.
    Args:
        applied_only (bool): if True, then only return True when application
            is in applied state
        con_ssh:
        auth_info:
        force_check:

    Returns (bool):

    """
    openstack_deployed = ProjVar.get_var('OPENSTACK_DEPLOYED')
    if not applied_only and not force_check and openstack_deployed is not None:
        return openstack_deployed

    openstack_status = get_apps(application='stx-openstack', field='status',
                                con_ssh=con_ssh, auth_info=auth_info)

    LOG.info("{}".format(openstack_status))

    res = False
    if openstack_status and 'appl' in openstack_status[0].lower():
        res = True
        if applied_only and openstack_status[0] != AppStatus.APPLIED:
            res = False

    return res
