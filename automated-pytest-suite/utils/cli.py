import os

from pytest import skip

from consts.auth import Tenant
from consts.stx import Prompt
from consts.proj_vars import ProjVar
from consts.timeout import CLI_TIMEOUT
from utils import exceptions
from utils.clients.ssh import ControllerClient
from utils.clients.telnet import TelnetClient


def exec_cli(cmd, sub_cmd, positional_args='', client=None, flags='',
             fail_ok=False, cli_dir='', auth_info=None,
             source_openrc=None, timeout=CLI_TIMEOUT):
    """

    Args:
        cmd: such as 'neutron'
        sub_cmd: such as 'net-show'
        client: SSHClient, TelnetClient or LocalHostClient
        positional_args: string or list.
            Single arg examples: 'arg0' or ['arg0']
            Multiple args string example: 'arg1 arg2'
            Multiple args list example: ['arg1','arg2']
        flags: string or list.
            Single arg examples: 'arg0 value0' or ['arg0 value']
            Multiple args string example: 'arg1 value1 arg2 value2 arg3'
            Multiple args list example: ['arg1 value1','arg2 value2', 'arg3']
        auth_info: (dict) authorization information to run cli commands.
        source_openrc (None|bool): In general this should NOT be set unless
        necessary.
        fail_ok:
        cli_dir:
        timeout:

    Returns:
        if command executed successfully: return command_output
        if command failed to execute such as authentication failure:
            if fail_ok: return exit_code, command_output
            if not fail_ok: raise exception
    """
    use_telnet = True if isinstance(client, TelnetClient) else False

    # Determine region and auth_url
    raw_cmd = cmd.strip().split()[0]
    is_dc = ProjVar.get_var('IS_DC')
    platform_cmds = ('system', 'fm')

    if auth_info is None:
        auth_info = Tenant.get_primary()

    platform = True if auth_info.get('platform') else False

    if not platform and ProjVar.get_var('OPENSTACK_DEPLOYED') is False:
        skip('stx-openstack application is not applied.')

    region = auth_info.get('region')
    dc_region = region if region and is_dc else None
    default_region_and_url = Tenant.get_region_and_url(platform=platform,
                                                       dc_region=dc_region)

    region = region if region else default_region_and_url['region']
    auth_url = auth_info.get('auth_url', default_region_and_url['auth_url'])

    if is_dc:
        # Set proper region when cmd is against DC central cloud. This is
        # needed due to the same auth_info may be
        # passed to different keywords that require different region
        if region in ('RegionOne', 'SystemController'):
            region = 'RegionOne' if raw_cmd in platform_cmds else \
                'SystemController'

        # # Reset auth_url if cmd is against DC central cloud RegionOne
        # containerized services. This is needed due to
        # # the default auth_url for central controller RegionOne is platform
        # auth_url
        # if region == 'RegionOne' and not platform:
        #     auth_url = default_region_and_url['auth_url']

    positional_args = __convert_args(positional_args)
    flags = __convert_args(flags)

    if not use_telnet and not client:
        if is_dc:
            # This may not exist if cli cmd used before DC vars are initialized
            client = ControllerClient.get_active_controller(name=region,
                                                            fail_ok=True)

        if not client:
            client = ControllerClient.get_active_controller()

    if source_openrc is None:
        source_openrc = ProjVar.get_var('SOURCE_OPENRC')

    if source_openrc:
        source_file = _get_rc_path(user=auth_info['user'], platform=platform)
        if use_telnet:
            cmd = 'source {}; {}'.format(source_file, cmd)
        else:
            source_openrc_file(ssh_client=client, auth_info=auth_info,
                               rc_file=source_file, fail_ok=fail_ok)
        flags = ''
    elif auth_info:
        # auth params
        auth_args = (
            "--os-username '{}' --os-password '{}' --os-project-name {} "
            "--os-auth-url {} "
            "--os-user-domain-name Default --os-project-domain-name Default".
            format(auth_info['user'], auth_info['password'],
                   auth_info['tenant'], auth_url))

        flags = '{} {}'.format(auth_args.strip(), flags.strip())

    # internal URL handling
    if raw_cmd in ('openstack', 'sw-manager'):
        flags += ' --os-interface internal'
    else:
        flags += ' --os-endpoint-type internalURL'

    # region handling
    if raw_cmd != 'dcmanager':
        if raw_cmd == 'cinder':
            flags += ' --os_region_name {}'.format(region)
        else:
            flags += ' --os-region-name {}'.format(region)

    complete_cmd = ' '.join([os.path.join(cli_dir, cmd), flags.strip(), sub_cmd,
                             positional_args]).strip()

    # workaround for dcmanager cmd not supporting --os-project-name
    if complete_cmd.startswith('dcmanager'):
        complete_cmd = complete_cmd.replace('--os-project-name',
                                            '--os-tenant-name')

    kwargs = {'searchwindowsize': 100} if not use_telnet else {}
    exit_code, cmd_output = client.exec_cmd(complete_cmd,
                                            expect_timeout=timeout, **kwargs)

    if exit_code == 0:
        return 0, cmd_output

    if fail_ok and exit_code in [1, 2]:
        return 1, cmd_output

    raise exceptions.CLIRejected(
        "CLI '{}' failed to execute. Output: {}".format(complete_cmd,
                                                        cmd_output))


def __convert_args(args):
    if args is None:
        args = ''
    elif isinstance(args, list):
        args = ' '.join(str(arg) for arg in args)
    else:
        args = str(args)

    return args.strip()


def _get_rc_path(user, remote_cli=False, platform=None):
    if remote_cli:
        openrc_path = os.path.join(ProjVar.get_var('LOG_DIR'), 'horizon',
                                   '{}-openrc.sh'.format(user))
    else:
        openrc_path = '/etc/platform/openrc' if platform and user == 'admin' \
            else '~/openrc.{}'.format(user)

    return openrc_path


def source_openrc_file(ssh_client, auth_info, rc_file, fail_ok=False,
                       force=True):
    """
    Source to the given openrc file on the ssh client.
    Args:
        ssh_client:
        auth_info:
        rc_file:
        fail_ok:
        force (bool): Whether to source even if already sourced.

    Returns:
        (-1, None)    # Already sourced, no action done
        (0, <cmd_output>)   # sourced to openrc file successfully
        (1, <err_output>)   # Failed to source

    """
    exit_code, cmd_output = -1, None
    user = auth_info['user']
    if force or 'keystone_{}'.format(user) not in ssh_client.prompt:
        password = auth_info['password']
        new_prompt = Prompt.TENANT_PROMPT.format(user)

        cmd = 'source {}'.format(rc_file)
        ssh_client.send(cmd)
        prompts = [new_prompt]
        index = ssh_client.expect(prompts, fail_ok=False)

        if index == 2:
            ssh_client.send()
            index = ssh_client.expect(prompts[0:3])
        if index == 1:
            ssh_client.send(password)
            index = ssh_client.expect(prompts[0:2])

        if index == 0:
            ssh_client.set_prompt(new_prompt)
            exit_code = ssh_client.get_exit_code()
        else:
            cmd_output = ssh_client.cmd_output
            ssh_client.send_control()
            ssh_client.expect()
            exit_code = 1

        if exit_code != 0:
            if not fail_ok:
                raise exceptions.SSHExecCommandFailed(
                    "Failed to Source. Output: {}".format(cmd_output))

    return exit_code, cmd_output


def openstack(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
              cli_dir='', auth_info=None,
              timeout=CLI_TIMEOUT, source_openrc=False):
    flags += ' --os-identity-api-version 3'

    return exec_cli('openstack', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc, timeout=timeout)


def nova(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
         cli_dir='', auth_info=None,
         timeout=CLI_TIMEOUT):
    return exec_cli('nova', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    timeout=timeout)


def heat(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
         cli_dir='', auth_info=Tenant.get('admin'),
         timeout=CLI_TIMEOUT):
    return exec_cli('heat', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    timeout=timeout)


def neutron(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
            cli_dir='', auth_info=None,
            timeout=CLI_TIMEOUT):
    return exec_cli('neutron', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    timeout=timeout)


def cinder(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
           cli_dir='', auth_info=None,
           timeout=CLI_TIMEOUT):
    return exec_cli('cinder', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    timeout=timeout)


def swift(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
          cli_dir='', auth_info=Tenant.get('admin'),
          source_openrc=None, timeout=CLI_TIMEOUT):
    return exec_cli('swift', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc, timeout=timeout)


def sw_manager(cmd, positional_args='', ssh_client=None, flags='',
               fail_ok=False, cli_dir='',
               auth_info=Tenant.get('admin_platform'), source_openrc=None,
               timeout=CLI_TIMEOUT):
    return exec_cli('sw-manager', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc, timeout=timeout)


def system(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
           cli_dir='', auth_info=Tenant.get('admin_platform'),
           source_openrc=None, timeout=CLI_TIMEOUT):
    return exec_cli('system', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc,
                    timeout=timeout)


def fm(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
       cli_dir='',
       auth_info=Tenant.get('admin_platform'), source_openrc=None,
       timeout=CLI_TIMEOUT):
    build = ProjVar.get_var('BUILD_INFO').get('BUILD_ID')
    cmd_ = 'fm'
    if build and build != 'n/a' and build < '2018-08-19':
        cmd_ = 'system'

    return exec_cli(cmd_, sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags, fail_ok=fail_ok,
                    cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc, timeout=timeout)


def dcmanager(cmd, positional_args='', ssh_client=None, flags='', fail_ok=False,
              cli_dir='',
              auth_info=Tenant.get('admin_platform', dc_region='RegionOne'),
              timeout=CLI_TIMEOUT,
              source_openrc=None):
    if ssh_client is None:
        ssh_client = ControllerClient.get_active_controller('RegionOne')
    return exec_cli('dcmanager', sub_cmd=cmd, positional_args=positional_args,
                    client=ssh_client, flags=flags,
                    fail_ok=fail_ok, cli_dir=cli_dir, auth_info=auth_info,
                    source_openrc=source_openrc, timeout=timeout)
