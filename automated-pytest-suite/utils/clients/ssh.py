#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import os
import re
import threading
import time
from contextlib import contextmanager

import pexpect
from pexpect import pxssh

from consts.auth import Guest, HostLinuxUser
from consts.stx import Prompt, DATE_OUTPUT
from consts.lab import Labs, NatBoxes
from consts.proj_vars import ProjVar
from utils import exceptions, local_host
from utils.tis_log import LOG

# setup color.format strings
colorred = "\033[1;31m{0}\033[00m"
colorgrn = "\033[1;32m{0}\033[00m"
colorblue = "\033[1;34m{0}\033[00m"
coloryel = "\033[1;34m{0}\033[00m"

CONTROLLER_PROMPT = Prompt.CONTROLLER_PROMPT
ADMIN_PROMPT = Prompt.ADMIN_PROMPT
TENANT1_PROMPT = Prompt.TENANT1_PROMPT
TENANT2_PROMPT = Prompt.TENANT2_PROMPT
COMPUTE_PROMPT = Prompt.COMPUTE_PROMPT
PASSWORD_PROMPT = Prompt.PASSWORD_PROMPT
ROOT_PROMPT = Prompt.ROOT_PROMPT
CONNECTION_REFUSED = '.*Connection refused.*'
AUTHORIZED_KEYS_FPATH = "~/.ssh/authorized_keys"

_SSH_OPTS = (' -o RSAAuthentication=no'
             + ' -o PubkeyAuthentication=no'
             + ' -o StrictHostKeyChecking=no'
             + ' -o UserKnownHostsFile=/dev/null')

_SSH_OPTS_UBUNTU_VM = (' -o RSAAuthentication=no'
                       + ' -o StrictHostKeyChecking=no'
                       + ' -o UserKnownHostsFile=/dev/null')

EXIT_CODE_CMD = 'echo $?'
TIMEOUT_EXPECT = 10

RSYNC_SSH_OPTIONS = ['-o StrictHostKeyChecking=no',
                     '-o UserKnownHostsFile=/dev/null']


class SSHClient:
    """
        Base SSH Class that uses pexpect and pexpect.pxssh

        Supports:
            Multiple sessions, via instanciation of session objects
            connect             connects a session
            send                sends string to remote host
            expect()            waits for prompt
            expect('value')     expects 'value'
            expect('value', show_exp=yes)        expects 'value' and prints
            value found
            expect(var)         expects python variable
            expect('\w+::\w+')  expect short IPv6 address like 2001::0001
            close()             disconnects session
            reconnect()         reconnects to session
    """

    def __init__(self, host, user=HostLinuxUser.get_user(),
                 password=HostLinuxUser.get_password(),
                 force_password=True, initial_prompt=CONTROLLER_PROMPT,
                 timeout=60, session=None,
                 searchwindownsize=None, port=None):
        """
        Initiate an object for connecting to remote host
        Args:
            host: hostname or ip. such as "yow-cgcs-ironpass-1.wrs.com" or
                "128.224.151.212"
            user: linux username for login to host. such as "sysadmin"
            password: password for given user. such as "Li69nux*"

        Returns:

        """

        self.host = host
        self.user = user
        self.password = password
        self.initial_prompt = initial_prompt
        self.prompt = initial_prompt
        self.session = session
        self.cmd_sent = ''
        self.cmd_output = ''
        self.force_password = force_password
        self.timeout = timeout
        self.searchwindowsize = searchwindownsize
        self.logpath = None
        self.port = port

    def _get_logpath(self):
        lab_list = [getattr(Labs, attr) for attr in dir(Labs) if
                    not attr.startswith('__')]
        lab_list = [lab_ for lab_ in lab_list if isinstance(lab_, dict)]
        for lab in lab_list:
            if lab.get('floating ip') == self.host or \
                    lab.get('controller-0 ip') == self.host \
                    or lab.get('external_ip') == self.host:
                lab_name = lab.get('short_name')
                break
        else:
            lab_name = self.host

        log_dir = ProjVar.get_var('LOG_DIR')
        if log_dir:
            current_thread = threading.current_thread()
            if current_thread is threading.main_thread():
                logpath = log_dir + '/ssh_' + lab_name + ".log"
            else:
                log_dir += '/threads/'
                logpath = log_dir + current_thread.name + '_ssh_' + lab_name \
                    + ".log"
            os.makedirs(log_dir, exist_ok=True)
        else:
            logpath = None

        return logpath

    def connect(self, retry=False, retry_interval=3, retry_timeout=300,
                prompt=None,
                use_current=True, timeout=None):

        # Do nothing if current session is connected and force_close is False:
        if self._is_alive() and use_current and self.is_connected():
            LOG.debug("Already connected to {}. Do nothing.".format(self.host))
            # LOG.debug("ID of the session: {}".format(id(self)))
            return

        # use original prompt instead of self.prompt when connecting in case
        # of prompt change during a session
        if not prompt:
            prompt = self.initial_prompt
        if timeout is None:
            timeout = self.timeout

        # Connect to host
        LOG.info("Attempt to connect to host - {}".format(self.host))
        end_time = time.time() + retry_timeout
        while time.time() < end_time:
            # LOG into remote host
            # print(str(self.searchwindowsize))
            try:
                self.session = pxssh.pxssh(
                    encoding='utf-8', searchwindowsize=self.searchwindowsize)

                # set to ignore ssh host fingerprinting
                self.session.SSH_OPTS = _SSH_OPTS
                self.session.force_password = self.force_password
                self.session.maxread = 100000
                self.logpath = self._get_logpath()

                if self.logpath:
                    self.session.logfile = open(self.logpath, 'a+')

                # Login
                self.session.login(self.host, self.user, self.password,
                                   login_timeout=timeout,
                                   port=self.port, auto_prompt_reset=False,
                                   quiet=False)

                # Set prompt for matching
                self.set_prompt(prompt)

                # try to goto next line to ensure login really succeeded.
                # pxssh login method has a bug where it
                # almost won't report any login failures.
                # Login successful if prompt matching is found
                if self.is_connected():
                    LOG.info("Login successful!")
                    # LOG.debug(self.session)
                    # next 5 lines change ssh window size and flush its buffer
                    self.session.setwinsize(150, 250)
                    # self.session.maxread = 100000
                    self.send()

                    end_time = time.time() + 20
                    while time.time() < end_time:
                        index = self.expect(timeout=3, fail_ok=True)
                        if index != 0:
                            break
                    else:
                        LOG.warning(
                            "Still getting prompt from the buffer. Buffer "
                            "might not be cleared yet.")

                    self.exec_cmd('unset PROMPT_COMMAND', get_exit_code=False)
                    self.exec_cmd('export TMOUT=0', get_exit_code=False)
                    return

                # retry if this line is reached. it would've returned if
                # login succeeded.
                LOG.debug("Login failed although no exception caught.")
                if not retry:
                    raise exceptions.SSHException("Unable to connect to host")

            # pxssh has a bug where the TIMEOUT exception during pxssh.login
            # is completely eaten. i.e., it will still
            # pretend login passed even if timeout exception was thrown. So
            # below exceptions are unlikely to be received
            # at all. But leave as is in case pxssh fix it in future releases.
            except (OSError, pexpect.TIMEOUT, pxssh.TIMEOUT, pexpect.EOF,
                    pxssh.ExceptionPxssh) as e:
                # fail login if retry=False
                # LOG.debug("Reset session.after upon ssh error")
                # self.session.after = ''
                if not retry:
                    raise

                # don't retry if login credentials incorrect
                if "permission denied" in e.__str__():
                    LOG.error(
                        "Login credentials denied by {}. User: {} Password: "
                        "{}".format(self.host, self.user, self.password))
                    raise

                # print out error for more info before retrying
                LOG.debug("Login failed due to error: {}".format(e.__str__()))

                if 'password refused' in e.__str__():
                    if self.searchwindowsize is None:
                        before_str = self._parse_output(self.session.before)
                        after_str = self._parse_output(self.session.after)
                        output = before_str + after_str
                        if 'your password' in output:
                            LOG.warning(
                                "Login failed possibly due to password expire "
                                "warning. "
                                "Retry with small searchwindowsize")
                            self.searchwindowsize = 50
                        else:
                            raise
                    else:
                        self.searchwindowsize = None
                        raise

            self.close()
            LOG.debug("Retry in {} seconds".format(retry_interval))
            time.sleep(retry_interval)

        else:
            raise exceptions.SSHRetryTimeout("Host: {}, User: {}, Password: {}".
                                             format(self.host, self.user,
                                                    self.password))

    def _is_alive(self):
        return self.session is not None and self.session.isalive()

    def is_connected(self):
        if not self.session:
            return False

        # Connection is good if send and expect commands can be executed
        try:
            self.send()
        except OSError:
            return False
        return self.expect(timeout=3, fail_ok=True) == 0

    def wait_for_disconnect(self, timeout=120, check_interval=5, fail_ok=False):
        """ Wait for ssh connection disconnect """
        end_time = time.time() + timeout
        while time.time() < end_time:
            if not self.is_connected():
                LOG.info("ssh session to {} disconnected".format(self.host))
                return True
            time.sleep(check_interval)

        msg = "Did not disconnect to {} within {}s".format(self.host, timeout)
        LOG.warning(msg)
        if not fail_ok:
            raise exceptions.SSHException(msg)
        return False

    def send(self, cmd='', reconnect=False, reconnect_timeout=300, flush=False):
        """
        goto next line if no cmd is specified
        Args:
            cmd:
            reconnect:
            reconnect_timeout:
            flush: whether to flush out the expect buffer before sending a
            new command

        Returns:number of bytes sent

        """
        if flush:
            self.flush()

        LOG.debug("Send '{}'".format(cmd))

        try:
            rtn = self.session.sendline(cmd)
        except Exception as e:
            if not reconnect:
                raise
            else:
                LOG.exception("Failed to send line. {}".format(e.__str__()))
                self.close()
                self.connect(retry_timeout=reconnect_timeout)
                rtn = self.session.sendline(cmd)

        # LOG.debug("Command sent successfully")
        self.cmd_sent = cmd

        return str(rtn)

    def send_sudo(self, cmd='', reconnect=False, expt_pswd_timeout=60,
                  reconnect_timeout=300, flush=False):
        cmd = 'sudo ' + cmd
        self.send(cmd, reconnect=reconnect, reconnect_timeout=reconnect_timeout,
                  flush=flush)
        pw_prompt = Prompt.PASSWORD_PROMPT

        index = self.expect(pw_prompt, timeout=expt_pswd_timeout,
                            searchwindowsize=100, fail_ok=True)
        if index == 0:
            self.send(self.password)

    def flush(self, timeout=3):
        """
        flush before sending the next command.
        Returns:

        """
        self.expect(fail_ok=True, timeout=timeout)
        LOG.debug("Buffer is flushed by reading out the rest of the output")

    def expect(self, blob_list=None, timeout=60, fail_ok=False, rm_date=False,
               searchwindowsize=None):
        """
        Look for match in the output. Stop if 1) match is found, 2) match is
        not found and prompt is reached, 3) match
        is not found and timeout is reached. For scenario 2 and 3, either
        throw timeout exception or return False based
        on the 'fail' argument.
        Args:
            blob_list: pattern(s) to find match for
            timeout: max timeout value to wait for pattern(s)
            fail_ok: True or False. When False: throws exception if match not
            found. When True: return -1 when match not
                found.
            rm_date (bool): Whether to remove the date output before expecting
            searchwindowsize (int|None): number of chars from end of the
            buffer to search for the strings in blob_list

        Returns: the index of the pattern matched in the output, assuming
        that blob can be a list.

        Examples:
            expect(): to wait for prompt
            expect('good'): to wait for a match starts with 'good'
            expect(['good', 'bad'], 10, False): to wait for a match start
            with 'good' or 'bad' with 10seconds timeout

        """

        if blob_list is None:
            blob_list = self.prompt

        if not isinstance(blob_list, (list, tuple)):
            blob_list = [blob_list]

        kwargs = {}
        if searchwindowsize is not None:
            kwargs['searchwindowsize'] = searchwindowsize
        elif blob_list == [self.prompt]:
            kwargs['searchwindowsize'] = 100

        try:
            index = self.session.expect(blob_list, timeout=timeout, **kwargs)
        except pexpect.EOF:
            if fail_ok:
                return -1
            else:
                LOG.warning("EOF caught.")
                raise
        except pexpect.TIMEOUT:
            if fail_ok:
                return -2
            else:
                LOG.warning("No match found for {}. \nexpect timeout.".format(
                    blob_list))
                raise
        except Exception as e:
            if fail_ok:
                return -100
            else:
                LOG.warning(
                    "Exception occurred when expecting {}. "
                    "{}".format(blob_list, e.__str__()))
                raise

        # Match found, reformat the outputs
        before_str = self._parse_output(self.session.before)
        after_str = self._parse_output(self.session.after)
        output = before_str + after_str
        if not self.cmd_sent == '':
            output_list = output.split('\r\n')
            output_list[0] = ''  # do not display the sent command

            if rm_date:  # remove date output if any
                if re.search(DATE_OUTPUT, output_list[-1]):
                    output_list = output_list[:-1]

            output = '\n'.join(output_list)
        self.cmd_sent = ''  # Make sure sent line is only removed once

        self.cmd_output = output
        extra_str = ''  # extra logging info

        LOG.debug("Output{}: {}".format(extra_str, output))
        return index

    def __force_end(self, force):
        if force:
            self.flush(3)
            self.send_control('c')
            self.flush(10)

    def exec_cmd(self, cmd, expect_timeout=60, reconnect=False,
                 reconnect_timeout=300, err_only=False, rm_date=False,
                 fail_ok=True, get_exit_code=True, blob=None, force_end=False,
                 searchwindowsize=None,
                 prefix_space=False):
        """

        Args:
            cmd:
            expect_timeout:
            reconnect:
            reconnect_timeout:
            err_only: if true, stdout will not be included in output
            rm_date (bool): weather to remove date output from cmd output
                before returning
            fail_ok (bool): whether to raise exception when non-zero
                exit-code is returned
            get_exit_code
            blob
            force_end
            searchwindowsize (int): max chars to look for match from the end
                of the output.
                Usage: when expecting a prompt, set this to slightly larger
                than the number of chars of the prompt,
                    to speed up the search, and to avoid matching in the
                    middle of the output.
            prefix_space

        Returns (tuple): (exit code (int), command output (str))

        """
        if blob is None:
            blob = self.prompt

        LOG.debug("Executing command...")
        if err_only:
            cmd += ' 1> /dev/null'  # discard stdout

        if prefix_space:
            cmd = ' {}'.format(cmd)

        self.send(cmd, reconnect, reconnect_timeout)
        code_force = 0
        try:
            self.expect(blob_list=blob, timeout=expect_timeout,
                        searchwindowsize=searchwindowsize)
        except pexpect.TIMEOUT as e:
            code_force = 130
            self.send_control('c')
            self.flush(timeout=10)
            if fail_ok:
                LOG.warning(e.__str__())
            else:
                raise

        code, output = self._process_exec_result(rm_date,
                                                 get_exit_code=get_exit_code)
        if code_force != 0:
            code = code_force

        self.__force_end(force_end)

        if code > 0 and not fail_ok:
            raise exceptions.SSHExecCommandFailed(
                "Non-zero return code for cmd: {}. Output: {}".format(cmd,
                                                                      output))

        return code, output

    def _process_exec_result(self, rm_date=True, get_exit_code=True):
        cmd_output_list = self.cmd_output.split('\n')[0:-1]  # exclude prompt
        # LOG.info("cmd output list: {}".format(cmd_output_list))
        # cmd_output_list[0] = ''                                       #
        # exclude command, already done in expect

        if rm_date:  # remove date output if any
            if re.search(DATE_OUTPUT, cmd_output_list[-1]):
                cmd_output_list = cmd_output_list[:-1]

        cmd_output = '\n'.join(cmd_output_list)

        if get_exit_code:
            exit_code = self.get_exit_code()
        else:
            exit_code = -1

        cmd_output = cmd_output.strip()
        return exit_code, cmd_output

    def process_cmd_result(self, cmd, rm_date=True, get_exit_code=True):
        return self._process_exec_result(rm_date=rm_date,
                                         get_exit_code=get_exit_code)

    @staticmethod
    def _parse_output(output):
        if type(output) is bytes:
            output = output.decode("utf-8")
        return str(output)

    def set_prompt(self, prompt=CONTROLLER_PROMPT):
        self.prompt = prompt

    def get_prompt(self):
        return self.prompt

    def get_exit_code(self):
        self.send(EXIT_CODE_CMD)
        self.expect(timeout=30, fail_ok=False)
        matches = re.findall("\n([-+]?[0-9]+)\n", self.cmd_output)
        return int(matches[-1])

    def get_hostname(self):
        return self.exec_cmd('hostname', get_exit_code=False)[1].splitlines()[0]

    def rsync(self, source, dest_server, dest, dest_user=None,
              dest_password=None, ssh_port=None, extra_opts=None,
              pre_opts=None, timeout=120, fail_ok=False):

        dest_user = dest_user or HostLinuxUser.get_user()
        dest_password = dest_password or HostLinuxUser.get_password()
        if extra_opts:
            extra_opts_str = ' '.join(extra_opts) + ' '
        else:
            extra_opts_str = ''

        if not pre_opts:
            pre_opts = ''

        ssh_opts = 'ssh {}'.format(' '.join(RSYNC_SSH_OPTIONS))
        if ssh_port:
            ssh_opts += ' -p {}'.format(ssh_port)

        cmd = "{} rsync -are \"{}\" {} {} ".format(pre_opts, ssh_opts,
                                                   extra_opts_str, source)
        cmd += "{}@{}:{}".format(dest_user, dest_server, dest)

        LOG.info(
            "Rsyncing file(s) from {} to {}: {}".format(self.host, dest_server,
                                                        cmd))
        self.send(cmd)
        index = self.expect(blob_list=[self.prompt, PASSWORD_PROMPT],
                            timeout=timeout)

        if index == 1:
            self.send(dest_password)
            self.expect(timeout=timeout, searchwindowsize=100, fail_ok=fail_ok)

        code, output = self._process_exec_result(rm_date=True)
        if code != 0 and not fail_ok:
            raise exceptions.SSHExecCommandFailed(
                "Non-zero return code for rsync cmd: {}. Output: {}".
                format(cmd, output))

        return code, output

    def scp_on_source_to_localhost(self, source_file, dest_password,
                                   dest_user=None, dest_path=None, timeout=120):

        if not dest_path:
            dest_path = ProjVar.get_var('TEMP_DIR') + '/'

        to_host = local_host.get_host_ip() + ':'
        to_user = (
                      dest_user if dest_user is not None else
                      local_host.get_user()) + '@'

        destination = to_user + to_host + dest_path
        scp_cmd = ' '.join([
                               'scp -o StrictHostKeyChecking=no -o '
                               'UserKnownHostsFile=/dev/null -r',
                               source_file,
                               destination]).strip()
        LOG.info(
            "Copying files from ssh client to {}: {}".format(to_host, scp_cmd))
        self.send(scp_cmd)
        index = self.expect([self.prompt, PASSWORD_PROMPT, Prompt.ADD_HOST],
                            timeout=timeout)
        if index == 2:
            self.send('yes')
            index = self.expect([self.prompt, PASSWORD_PROMPT], timeout=timeout)
        if index == 1:
            self.send(dest_password)
            index = self.expect()
        if not index == 0:
            raise exceptions.SSHException("Failed to scp files")

    def scp_on_dest(self, source_user, source_ip, source_path, dest_path,
                    source_pswd, timeout=3600, cleanup=True,
                    is_dir=False):
        source = source_path
        if source_ip:
            source = '{}:{}'.format(source_ip, source)
            if source_user:
                source = '{}@{}'.format(source_user, source)

        option = '-r ' if is_dir else ''
        scp_cmd = 'scp -o StrictHostKeyChecking=no -o ' \
                  'UserKnownHostsFile=/dev/null {}{} ' \
                  '{}'.format(option, source, dest_path)

        try:
            self.send(scp_cmd)
            index = self.expect(
                [self.prompt, Prompt.PASSWORD_PROMPT, Prompt.ADD_HOST],
                timeout=timeout)
            if index == 2:
                self.send('yes')
                index = self.expect([self.prompt, Prompt.PASSWORD_PROMPT],
                                    timeout=timeout)
            if index == 1:
                self.send(source_pswd)
                index = self.expect(timeout=timeout)
            if index != 0:
                raise exceptions.SSHException("Failed to scp files")

            exit_code = self.get_exit_code()
            if not exit_code == 0:
                raise exceptions.CommonError("scp unsuccessfully")

        except:
            if cleanup:
                LOG.info(
                    "Attempt to remove {} to cleanup the system due to scp "
                    "failed".format(
                        dest_path))
                self.exec_cmd('rm -f {}'.format(dest_path), fail_ok=True,
                              get_exit_code=False)
            raise

    def scp_on_source(self, source_path, dest_user, dest_ip, dest_path,
                      dest_password, timeout=3600, is_dir=False):
        dest = dest_path
        if dest_ip:
            dest = '{}:{}'.format(dest_ip, dest)
            if dest_user:
                dest = '{}@{}'.format(dest_user, dest)

        if is_dir:
            if not source_path.endswith('/'):
                source_path += '/'
            source_path = '-r {}'.format(source_path)

        scp_cmd = 'scp -o StrictHostKeyChecking=no -o ' \
                  'UserKnownHostsFile=/dev/null {} {}'. \
            format(source_path, dest)

        self.send(scp_cmd)
        index = self.expect(
            [self.prompt, Prompt.PASSWORD_PROMPT, Prompt.ADD_HOST],
            timeout=timeout)
        if index == 2:
            self.send('yes')
            index = self.expect([self.prompt, Prompt.PASSWORD_PROMPT],
                                timeout=timeout)
        if index == 1:
            self.send(dest_password)
            index = self.expect(timeout=timeout)
        if index != 0:
            raise exceptions.SSHException("Failed to scp files")

        exit_code = self.get_exit_code()
        if not exit_code == 0:
            raise exceptions.CommonError("scp unsuccessfully")

    def file_exists(self, file_path):
        return self.exec_cmd('stat {}'.format(file_path), fail_ok=True)[0] == 0

    @contextmanager
    def login_as_root(self, timeout=10):
        self.send('sudo su -')
        index = self.expect([ROOT_PROMPT, PASSWORD_PROMPT], timeout=timeout)
        if index == 1:
            self.send(self.password)
            self.expect(ROOT_PROMPT)
        original_prompt = self.get_prompt()
        self.set_prompt(ROOT_PROMPT)
        self.set_session_timeout(timeout=0)
        try:
            yield self
        finally:
            try:
                current_user = self.get_current_user(
                    prompt=[ROOT_PROMPT, original_prompt])
            except:
                current_user = None
            if current_user == 'root':
                self.set_prompt(original_prompt)
                self.send('exit')
                self.expect()

    def exec_sudo_cmd(self, cmd, expect_timeout=60, rm_date=True, fail_ok=True,
                      get_exit_code=True,
                      searchwindowsize=None, strict_passwd_prompt=False,
                      extra_prompt=None, prefix_space=False):
        """
        Execute a command with sudo.

        Args:
            cmd (str): command to execute. such as 'ifconfig'
            expect_timeout (int): timeout waiting for command to return
            rm_date (bool): whether to remove date info at the end of the output
            fail_ok (bool): whether to raise exception when non-zero exit
            code is returned
            get_exit_code
            searchwindowsize (int): max chars to look for match from the end
                of the output.
                Usage: when expecting a prompt, set this to slightly larger
                than the number of chars of the prompt,
                    to speed up the search, and to avoid matching in the
                    middle of the output.
            strict_passwd_prompt (bool): whether to search output with strict
            password prompt (Not recommended. Use
                searchwindowsize instead)
            extra_prompt (str|None)
            prefix_space (bool): prefix ' ' to cmd, so that it will not go
            into bash history if HISTCONTROL=ignorespace

        Returns (tuple): (exit code (int), command output (str))

        """
        cmd = 'sudo ' + cmd
        if prefix_space:
            cmd = ' {}'.format(cmd)
        LOG.debug("Executing sudo command...")
        self.send(cmd)
        pw_prompt = Prompt.PASSWORD_PROMPT if not strict_passwd_prompt else \
            Prompt.SUDO_PASSWORD_PROMPT
        prompts = [self.prompt]
        if extra_prompt is not None:
            prompts.append(extra_prompt)
        prompts.append(pw_prompt)

        index = self.expect(prompts, timeout=expect_timeout,
                            searchwindowsize=searchwindowsize, fail_ok=fail_ok)
        if index == prompts.index(pw_prompt):
            self.send(self.password)
            prompts.remove(pw_prompt)
            self.expect(prompts, timeout=expect_timeout,
                        searchwindowsize=searchwindowsize, fail_ok=fail_ok)

        code, output = self._process_exec_result(rm_date,
                                                 get_exit_code=get_exit_code)
        if code != 0 and not fail_ok:
            raise exceptions.SSHExecCommandFailed(
                "Non-zero return code for sudo cmd: {}. Output: {}".
                format(cmd, output))

        return code, output

    def send_control(self, char='c'):
        LOG.debug("Sending ctrl+{}".format(char))
        self.session.sendcontrol(char=char)

    def get_current_user(self, prompt=None):
        output = self.exec_cmd('whoami', blob=prompt, expect_timeout=10,
                               get_exit_code=False)[1]
        if output:
            output = output.splitlines()[0]

        return output

    def close(self):
        self.session.close(True)
        LOG.debug("connection closed. host: {}, user: {}. Object ID: {}".format(
            self.host, self.user, id(self)))

    def set_session_timeout(self, timeout=0):
        self.send('TMOUT={}'.format(timeout))
        self.expect()

    def wait_for_cmd_output(self, cmd, content, timeout, strict=False,
                            regex=False, expt_timeout=10,
                            check_interval=3, disappear=False,
                            non_zero_rtn_ok=False, blob=None):
        """
        Wait for given content to appear or disappear in cmd output.

        Args:
            cmd (str): cmd to run repeatedly until given content
            appears|disappears or timeout reaches
            content (str): string expected to appear|disappear in cmd output
            timeout (int): max seconds to wait for the expected content
            strict (bool): whether to perform strict search  (search is NOT
            case sensitive even if strict=True)
            regex (bool): whether given content is regex pattern
            expt_timeout (int): max time to wait for cmd to return
            check_interval (int): how long to wait to execute the cmd again
            in seconds.
            disappear (bool): whether to wait for content appear or disappear
            non_zero_rtn_ok (bool): whether it's okay for cmd to have
            none-zero return code. Raise exception if False.
            blob (str): string to wait for

        Returns (bool): True if content appears in cmd output within max wait
        time.

        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            code, output = self.exec_cmd(cmd, expect_timeout=expt_timeout,
                                         blob=blob)
            if not non_zero_rtn_ok and code > 0:
                raise exceptions.SSHExecCommandFailed(
                    "Get non-zero return code for command: {}".format(cmd))

            content_exists = False
            if regex:
                if strict:
                    if re.match(content, output):
                        content_exists = True
                else:
                    if re.search(content, output):
                        content_exists = True
            else:
                if strict:
                    if content.lower() == output.lower():
                        content_exists = True
                else:
                    if content.lower() in output.lower():
                        content_exists = True

            if (content_exists and not disappear) or (
                    not content_exists and disappear):
                return True

            time.sleep(check_interval)

        else:
            return False

    def wait_for_cmd_output_persists(self, cmd, content, timeout=60,
                                     time_to_stay=10, strict=False, regex=False,
                                     expt_timeout=10, check_interval=1,
                                     exclude=False, non_zero_rtn_ok=False,
                                     sudo=False, fail_ok=True):
        """
        Wait for given content to be included/excluded in cmd output for more
        than <time_to_stay> seconds.

        Args:
            cmd (str): cmd to run repeatedly until given content
            appears|disappears or timeout reaches
            content (str): string expected to appear|disappear in cmd output
            time_to_stay (int): how long the expected content be
            included/excluded from cmd output to return True
            timeout (int): max seconds to wait for content to consistently be
            included/excluded from cmd output
            strict (bool): whether to perform strict search  (search is NOT
            case sensitive even if strict=True)
            regex (bool): whether given content is regex pattern
            expt_timeout (int): max time to wait for cmd to return
            check_interval (int): how long to wait to execute the cmd again
            in seconds.
            exclude (bool): whether to wait for content be consistently
            included or excluded from cmd output
            non_zero_rtn_ok (bool): whether it's okay for cmd to have
            none-zero return code. Raise exception if False.
            sudo (bool): whether to run cmd using sudo
            fail_ok (bool): whether to raise exception when False

        Returns (bool): True if content appears in cmd output within max wait
        time.

        """
        end_time = time.time() + timeout
        while time.time() < end_time:

            stay_end_time = time.time() + time_to_stay
            while time.time() < stay_end_time:
                if sudo:
                    code, output = self.exec_sudo_cmd(
                        cmd, expect_timeout=expt_timeout)
                else:
                    code, output = self.exec_cmd(
                        cmd, expect_timeout=expt_timeout)
                if not non_zero_rtn_ok and code > 0:
                    raise exceptions.SSHExecCommandFailed(
                        "Get non-zero return code for command: {}".format(cmd))

                content_exists = False
                if regex:
                    if strict:
                        if re.match(content, output):
                            content_exists = True
                    else:
                        if re.search(content, output):
                            content_exists = True
                else:
                    if strict:
                        if content.lower() == output.lower():
                            content_exists = True
                    else:
                        if content.lower() in output.lower():
                            content_exists = True

                if (content_exists and not exclude) or (
                        not content_exists and exclude):
                    time.sleep(check_interval)
                    continue
                else:
                    LOG.debug("Reset stay start time")
                    break
            else:
                # Did not break - meaning time to stay has reached
                return True

        else:
            if fail_ok:
                return False
            extra_str = 'is not excluded' if exclude else 'did not persist'
            raise exceptions.SSHException(
                "Expected output from {} - '{}' {} for {} seconds within {} "
                "seconds".
                format(cmd, content, extra_str, time_to_stay, timeout))

    def deploy_ssh_key(self, ssh_key=None):
        if ssh_key:
            self.exec_cmd("mkdir -p ~/.ssh/")
            cmd = 'grep -q "{}" {}'.format(ssh_key, AUTHORIZED_KEYS_FPATH)
            if self.exec_cmd(cmd) != 0:
                LOG.info(
                    "Adding public key to {}".format(AUTHORIZED_KEYS_FPATH))
                self.exec_cmd(r'echo -e "{}\n" >> {}'.format(
                    ssh_key, AUTHORIZED_KEYS_FPATH))
                self.exec_cmd("chmod 700 ~/.ssh/ && chmod 644 {}".format(
                    AUTHORIZED_KEYS_FPATH))

    def get_host(self):
        return self.host

    def update_host(self, new_host):
        self.host = new_host


class ContainerClient(SSHClient):
    """
        Base class for Starting Docker Container
        """

    def __init__(self, ssh_client, entry_cmd, user='root', host=None,
                 password=None, initial_prompt=None,
                 timeout=60):
        """
        Instantiate a container client
        Args:
            ssh_client: SSH Client object that's currently connected
            entry_cmd: cmd to run to enter the container shell, e.g.,
                docker run -it -e /bin/bash <docker_image>
                docker start <container_id>; docker attach <container_id>
            host: host to connect to from the existing ssh session
            user: default user in container shell
            password: password for given user
            initial_prompt: prompt for container shell

        """
        if not initial_prompt:
            initial_prompt = '.*{}@.*# .*'.format(user)
        if not host:
            host = ssh_client.host
        if not password:
            password = ssh_client.password

        super(ContainerClient, self).__init__(host=host, user=user,
                                              password=password,
                                              initial_prompt=initial_prompt,
                                              timeout=timeout,
                                              session=ssh_client.session)
        self.parent = ssh_client
        self.docker_cmd = entry_cmd
        self.timeout = timeout

    def connect(self, retry=False, retry_interval=1, retry_timeout=60,
                prompt=None,
                use_current=True, use_password=False, timeout=30):
        """
        Enter interactive mode for a container
        Args:
            retry:
            retry_interval:
            retry_timeout:
            prompt:
            use_current:
            use_password:
            timeout:

        Returns:

        """
        docker_cmd = self.docker_cmd
        if prompt:
            self.prompt = prompt
        self.exec_sudo_cmd(docker_cmd, expect_timeout=timeout,
                           get_exit_code=False)

        # Known issue with docker where an extra ENTER is needed to show prompt
        self.send()
        self.expect(timeout=5)

        # Ensure exec_cmd works after above workaround
        self.exec_cmd(cmd='', expect_timeout=5)

    def exec_cmd(self, cmd, expect_timeout=60, reconnect=False,
                 reconnect_timeout=300, err_only=False, rm_date=True,
                 fail_ok=True, get_exit_code=True, blob=None, force_end=False,
                 searchwindowsize=None,
                 prefix_space=False):
        """

        Args:
            cmd:
            expect_timeout:
            reconnect:
            reconnect_timeout:
            err_only: if true, stdout will not be included in output
            rm_date (bool): weather to remove date output from cmd output
                before returning
            fail_ok (bool): whether to raise exception when non-zero
                exit-code is returned
            get_exit_code
            blob
            force_end
            searchwindowsize (int): max chars to look for match from the end
                of the output.
                Usage: when expecting a prompt, set this to slightly larger
                than the number of chars of the prompt,
                    to speed up the search, and to avoid matching in the
                    middle of the output.
            prefix_space

        Returns (tuple): (exit code (int), command output (str))

        """
        if blob is None:
            blob = [self.prompt, self.parent.prompt]
        elif not isinstance(blob, (tuple, list)):
            blob = [blob]

        LOG.debug("Executing command...")
        if err_only:
            cmd += ' 1> /dev/null'  # discard stdout

        if prefix_space:
            cmd = ' {}'.format(cmd)

        self.send(cmd, reconnect, reconnect_timeout)
        code_force = 0
        try:
            index = self.expect(blob_list=blob, timeout=expect_timeout,
                                searchwindowsize=searchwindowsize)
        except pexpect.TIMEOUT as e:
            code_force = 130
            index = 0
            self.send_control('c')
            self.flush(timeout=10)
            if fail_ok:
                LOG.warning(e.__str__())
            else:
                raise

        if blob[index] == self.parent.prompt:
            # Connection lost. Returned to parent session.
            _, output = self._process_exec_result(get_exit_code=False)
            code = 100
        else:
            code, output = self._process_exec_result(
                get_exit_code=get_exit_code)

        if code_force != 0:
            code = code_force

        self.__force_end(force_end)

        if code > 0 and not fail_ok:
            raise exceptions.SSHExecCommandFailed(
                "Non-zero return code for cmd: {}. Output: {}".format(cmd,
                                                                      output))

        return code, output

    def close(self, force=False):
        if force or self.is_connected():
            self.send('exit')
            self.parent.expect()
            LOG.info(
                "ssh session to {} is closed and returned to parent session {}".
                format(self.host, self.parent.host))
        else:
            LOG.info(
                "ssh session to {} is not open. Flushing the buffer for "
                "parent session.".format(
                    self.host))
            self.parent.flush()


class SSHFromSSH(SSHClient):
    """
    Base class for ssh to another node from an existing ssh session
    """

    def __init__(self, ssh_client, host, user, password, force_password=True,
                 initial_prompt=COMPUTE_PROMPT,
                 timeout=60):
        """

        Args:
            ssh_client: SSH Client object that's currently connected
            host: host to connect to from the existing ssh session
            user: username
            password: password for given user

        Returns:

        """
        super(SSHFromSSH, self).__init__(host=host, user=user,
                                         password=password,
                                         force_password=force_password,
                                         initial_prompt=initial_prompt,
                                         timeout=timeout,
                                         session=ssh_client.session)
        self.parent = ssh_client
        self.ssh_cmd = '/usr/bin/ssh{} {}@{}'.format(_SSH_OPTS, self.user,
                                                     self.host)
        self.timeout = timeout

    def connect(self, retry=False, retry_interval=10, retry_timeout=300,
                prompt=None,
                use_current=True, use_password=True, timeout=None):
        """

        Args:
            retry:
            retry_interval:
            retry_timeout:
            timeout:
            prompt:
            use_current:
            use_password

        Returns:
            return the ssh client

        """
        self.logpath = self.parent.logpath
        self.session.logfile = self.parent.session.logfile

        if timeout is None:
            timeout = self.timeout
        if prompt is None:
            prompt = self.initial_prompt

        if use_current and self.is_connected():
            LOG.info(
                "Already connected to {} from {}. Do "
                "nothing.".format(self.host, self.parent.host))
            return

        LOG.info("Attempt to connect to {} from {}...".format(self.host,
                                                              self.parent.host))
        start_time = time.time()
        end_time = start_time + retry_timeout
        while time.time() < end_time:
            self.send(self.ssh_cmd)
            try:
                res_index = self.expect(
                    [prompt, PASSWORD_PROMPT, Prompt.ADD_HOST,
                     self.parent.get_prompt()],
                    timeout=timeout, fail_ok=False, searchwindowsize=100)
                if res_index == 3:
                    raise exceptions.SSHException(
                        "Unable to login to {}. \nOutput: "
                        "{}".format(self.host, self.cmd_output))

                if res_index == 2:
                    self.send('yes')
                    self.expect([prompt, PASSWORD_PROMPT])

                if res_index == 1:
                    if not use_password:
                        retry = False
                        raise exceptions.SSHException(
                            'password prompt appeared. Non-password auth '
                            'failed.')

                    self.send(self.password)
                    self.expect(prompt, timeout=timeout)

                # Set prompt for matching
                self.set_prompt(prompt)
                LOG.info(
                    "Successfully connected to {} from "
                    "{}!".format(self.host, self.parent.host))
                self.exec_cmd('export TMOUT=0')
                return

            except (OSError, pxssh.TIMEOUT, pexpect.EOF, pxssh.ExceptionPxssh,
                    exceptions.SSHException) as e:
                LOG.info("Unable to ssh to {}".format(self.host))
                if isinstance(e, pexpect.TIMEOUT):
                    self.parent.send_control('c')
                    self.parent.flush(timeout=3)
                # fail login if retry=False
                if not retry:
                    raise
                # don't retry if login credentials incorrect
                if "permission denied" in e.__str__().lower():
                    LOG.error(
                        "Login credentials denied by {}. User: {} Password: "
                        "{}".format(self.host, self.user, self.password))
                    raise

            LOG.info("Retry in {} seconds".format(retry_interval))
            time.sleep(retry_interval)
        else:
            try:
                self.parent.flush()
            except:
                pass
            raise exceptions.SSHRetryTimeout("Host: {}, User: {}, Password: {}".
                                             format(self.host, self.user,
                                                    self.password))

    def close(self, force=False):
        if force or self.is_connected():
            self.send('exit')
            self.parent.expect()
            LOG.info(
                "ssh session to {} is closed and returned to parent session {}".
                format(self.host, self.parent.host))
        else:
            LOG.info(
                "ssh session to {} is not open. Flushing the buffer for "
                "parent session.".format(self.host))
            self.parent.flush()

    def is_connected(self):
        # Connection is good if send and expect commands can be executed
        try:
            self.send()
        except OSError:
            return False

        index = self.expect(
            blob_list=[self.prompt, self.parent.get_prompt(), pexpect.TIMEOUT],
            timeout=3,
            fail_ok=True)
        if 2 == index:
            self.send_control('c')
            index = self.expect(
                blob_list=[self.prompt, self.parent.get_prompt()], timeout=3,
                fail_ok=True)
        return 0 == index


class VMSSHClient(SSHFromSSH):

    def __init__(self, vm_ip, vm_img_name=Guest, user=None, password=None,
                 vm_ext_port=None,
                 natbox_client=None, prompt=None, timeout=60, retry=True,
                 retry_timeout=120):
        """

        Args:
            vm_ip:
            vm_img_name:
            user:
            password:
            natbox_client:
            prompt:
            retry
            retry_timeout

        Returns:

        """
        LOG.debug("vm_image_name: {}".format(vm_img_name))
        if vm_img_name is None:
            vm_img_name = ''

        vm_img_name = vm_img_name.strip().lower()

        if not natbox_client:
            natbox_client = NATBoxClient.get_natbox_client()

        if user:
            if not password:
                password = None
        else:
            for image_name in Guest.CREDS:
                if image_name.lower() in vm_img_name.lower():
                    vm_creds = Guest.CREDS[image_name]
                    user = vm_creds['user']
                    password = vm_creds['password']
                    break
            else:
                user = 'root'
                password = 'root'
                known_guests = list(Guest.CREDS.keys())

                LOG.warning(
                    "User/password are not provided, and VM image type is not "
                    "in the list: {}. "
                    "Use root/root to login.".format(known_guests))

        if prompt is None:
            # prompt = r'.*{}\@{}.*\~.*[$#]'.format(user,
            # str(vm_name).replace('_', '-'))
            prompt = r'.*{}\@.*\~.*[$#]'.format(user)
        super(VMSSHClient, self).__init__(ssh_client=natbox_client, host=vm_ip,
                                          user=user, password=password,
                                          initial_prompt=prompt,
                                          timeout=timeout)

        # This needs to be modified in centos case.
        if not password:
            ssh_options = " -i {}{}".format(
                ProjVar.get_var('NATBOX_KEYFILE_PATH'), _SSH_OPTS_UBUNTU_VM)
        else:
            ssh_options = _SSH_OPTS

        # Check if connecting to vm through port forwarding rule
        if vm_ext_port:
            self.ssh_cmd = 'ssh -vvv {} -p {} {}@{}'.format(ssh_options,
                                                            vm_ext_port,
                                                            self.user,
                                                            self.host)
        else:
            self.ssh_cmd = 'ssh -vvv {} {}@{}'.format(ssh_options, self.user,
                                                      self.host)

        self.connect(use_password=password, retry=retry,
                     retry_timeout=retry_timeout)


class FloatingClient(SSHClient):
    def __init__(self, floating_ip, user=HostLinuxUser.get_user(),
                 password=HostLinuxUser.get_password(),
                 initial_prompt=CONTROLLER_PROMPT):

        # get a list of floating ips for all known labs
        __lab_list = [getattr(Labs, attr) for attr in dir(Labs) if
                      not attr.startswith(r'__')]
        __lab_list = [lab_ for lab_ in __lab_list if isinstance(lab_, dict)]
        ips = []
        for lab in __lab_list:
            ip = lab.get('floating ip')
            ips.append(ip)
        if not floating_ip.strip() in ips:
            raise ValueError(
                "Invalid input. No matching floating ips found in lab.Labs "
                "class")
        super(FloatingClient, self).__init__(host=floating_ip, user=user,
                                             password=password,
                                             initial_prompt=initial_prompt)


class NATBoxClient:
    # a list of natbox dicts from lab.NatBox class
    @classmethod
    def _get_natbox_list(cls):
        return [getattr(NatBoxes, attr) for attr in dir(NatBoxes) if
                attr.startswith('NAT_')]

    # internal dict that holds the natbox client if set_natbox_client was called
    __natbox_ssh_map = {}

    _PROMPT = r'\@.*[$#]'  # use user+_PROMPT to differentiate before
    # and after ssh to vm

    @classmethod
    def get_natbox_client(cls, natbox_ip=None):
        """

        Args:
            natbox_ip (str): natbox ip

        Returns (SSHClient): natbox ssh client

        """
        curr_thread = threading.current_thread()
        idx = 0 if curr_thread is threading.main_thread() else int(
            curr_thread.name.split('-')[-1])
        if not natbox_ip:
            natbox_ip = ProjVar.get_var('NATBOX').get('ip')
            num_natbox = len(cls.__natbox_ssh_map)
            if num_natbox == 0:
                raise exceptions.NatBoxClientUnsetException

        if len(cls.__natbox_ssh_map[natbox_ip]) > idx:
            nat_client = cls.__natbox_ssh_map[natbox_ip][
                idx]  # KeyError will be thrown if not exist
            LOG.info("Getting NatBox Client...")
            return nat_client

        LOG.warning('No NatBox client set for Thread-{}'.format(idx))
        return None

    @classmethod
    def set_natbox_client(cls, natbox_ip=None):
        if not natbox_ip:
            natbox_dict = ProjVar.get_var('NATBOX')
            if not natbox_dict:
                natbox_dict = NatBoxes.NAT_BOX_HW_EXAMPLE
                ProjVar.set_var(NATBOX=natbox_dict)
            natbox_ip = natbox_dict['ip']

        for natbox in cls._get_natbox_list():
            ip = natbox.get('ip')
            if ip == natbox_ip.strip():
                curr_thread = threading.current_thread()
                idx = 0 if curr_thread is threading.main_thread() else int(
                    curr_thread.name.split('-')[-1])
                user = natbox.get('user')
                if ip == 'localhost':
                    # use localhost as natbox
                    from utils.clients.local import LocalHostClient
                    nat_ssh = LocalHostClient()
                else:
                    nat_prompt = natbox.get('prompt', user+cls._PROMPT)
                    nat_ssh = SSHClient(ip, user, natbox.get('password'),
                                        initial_prompt=nat_prompt)
                nat_ssh.connect(use_current=False)

                if ip not in cls.__natbox_ssh_map:
                    cls.__natbox_ssh_map[ip] = []

                if len(cls.__natbox_ssh_map[ip]) == idx:
                    cls.__natbox_ssh_map[ip].append(nat_ssh)
                elif len(cls.__natbox_ssh_map[ip]) > idx:
                    cls.__natbox_ssh_map[ip][idx] = nat_ssh
                else:
                    if ip == 'localhost':
                        from utils.clients.local import LocalHostClient
                        new_ssh = LocalHostClient()
                    else:
                        new_ssh = SSHClient(ip, user, natbox.get('password'),
                                            initial_prompt=user + cls._PROMPT)

                    new_ssh.connect(use_current=False)
                    while len(cls.__natbox_ssh_map[ip]) < idx:
                        cls.__natbox_ssh_map[ip].append(new_ssh)
                    cls.__natbox_ssh_map[ip].append(nat_ssh)

                LOG.info("NatBox {} ssh client is set".format(ip))
                return nat_ssh

        raise ValueError(
            ("No matching natbox ip found from natbox list. IP provided: {}\n"
             "List of natbox(es) available: {}").format(natbox_ip,
                                                        cls._get_natbox_list()))


class ControllerClient:
    # Each entry is a lab dictionary such as Labs.VBOX. For newly created
    # dict entry, 'name' must be provided.
    __lab_attr_list = [attr for attr in dir(Labs) if not attr.startswith('__')]
    __lab_list = [getattr(Labs, attr) for attr in __lab_attr_list]
    __lab_list = [lab for lab in __lab_list if isinstance(lab, dict)]
    __lab_ssh_map = {}  # item such as 'PV0': [con_ssh, ...]

    __default_name = None
    __prev_client = None
    __prev_idx = None

    @classmethod
    def get_active_controller(cls, name=None, fail_ok=False):
        """
        Attempt to match given lab or current lab, otherwise return first ssh
        Args:
            name: The lab dictionary name in Labs class, such as 'PV0', 'HP380'
            fail_ok: when True: return None if no active controller was set

        Returns:

        """
        if not name:
            if cls.__default_name:
                name = cls.__default_name
            else:
                lab_dict = ProjVar.get_var('lab')
                if lab_dict is None:
                    return None

                for lab_ in cls.__lab_list:
                    if lab_dict['floating ip'] == lab_.get('floating ip'):
                        name = lab_.get('short_name')
                        break
                else:
                    name = 'no_name'

        if name in ('SystemController', 'central_region'):
            name = 'RegionOne'

        curr_thread = threading.current_thread()
        idx = 0 if curr_thread is threading.main_thread() else int(
            curr_thread.name.split('-')[-1])
        for lab_ in cls.__lab_ssh_map:
            if lab_ == name:
                controller_ssh = cls.__lab_ssh_map[lab_][idx]
                if isinstance(controller_ssh, SSHClient):
                    msg = "Getting active controller client for {}".format(lab_)
                    if name != cls.__prev_client or idx != cls.__prev_idx:
                        LOG.info(msg)
                        cls.__prev_client = name
                        cls.__prev_idx = idx
                    else:
                        LOG.debug(msg)
                    return controller_ssh

        if fail_ok:
            LOG.warning('No ssh client found for {}'.format(name))
            return None
        raise exceptions.ActiveControllerUnsetException(
            ("The name - {} does not have a corresponding "
             "controller ssh session set. ssh_map: {}").
            format(name, cls.__lab_ssh_map))

    @classmethod
    def get_active_controllers(cls, fail_ok=True, current_thread_only=True):
        """ Get all the active controllers ssh sessions.

        Used when running tests in multiple labs in parallel. i.e.,get all
        the active controllers' ssh sessions, and
        execute cli commands on all these controllers

        Returns: list of active controllers ssh clients.

        """
        controllers = []
        idx = 0
        if current_thread_only:
            curr_thread = threading.current_thread()
            idx = 0 if curr_thread is threading.main_thread() else int(
                curr_thread.name.split('-')[-1])
        for value in cls.__lab_ssh_map.values():
            if value:
                if current_thread_only:
                    if len(value) > idx:
                        controllers.append(value[idx])
                else:
                    controllers += value

        if len(controllers) == 0 and not fail_ok:
            raise exceptions.ActiveControllerUnsetException

        return controllers

    @classmethod
    def get_active_controllers_map(cls):
        return cls.__lab_ssh_map

    @classmethod
    def set_active_controller(cls, ssh_client, name=None):
        """
        lab_name for new entry

        Args:
            ssh_client:
            name: used in distributed cloud, when ssh for multiple systems
                need to be stored. e.g., name='subcloud-1'

        Returns:

        """
        if not isinstance(ssh_client, SSHClient):
            raise TypeError("ssh_client has to be an instance of SSHClient!")

        if not name:
            for lab_ in cls.__lab_list:
                if ssh_client.host == lab_.get(
                        'floating ip') or ssh_client.host == lab_.get(
                        'controller-0 ip') \
                        or ssh_client.host == lab_.get('external_ip'):
                    name = lab_.get('short_name')
                    break
            else:
                name = 'no_name'

        # new lab or ip address
        if name not in cls.__lab_ssh_map:
            cls.__lab_ssh_map[name] = []

        curr_thread = threading.current_thread()
        idx = 0 if curr_thread is threading.main_thread() else int(
            curr_thread.name.split('-')[-1])
        # set ssh for new lab
        if len(cls.__lab_ssh_map[name]) == idx:
            cls.__lab_ssh_map[name].append(ssh_client)
        # change existing ssh
        elif len(cls.__lab_ssh_map[name]) > idx:
            cls.__lab_ssh_map[name][idx] = ssh_client
        # fill with copy of new ssh session until list is correct length
        # (only when a different lab or ip address has also been added)
        else:
            new_ssh = SSHClient(ssh_client.host, ssh_client.user,
                                ssh_client.password)
            new_ssh.connect(use_current=False)
            while len(cls.__lab_ssh_map[name]) < idx:
                cls.__lab_ssh_map[name].append(new_ssh)
            cls.__lab_ssh_map[name].append(ssh_client)

        LOG.info(
            "Active controller client for {} is set. Host ip/name: {}".format(
                name, ssh_client.host))

    @classmethod
    def set_active_controllers(cls, *args):
        """
        Set active controller(s) for lab(s).

        Args:
            *args:ssh clients for lab(s)
                e.g.,ip_1-4_ssh , hp380_ssh

        """
        for lab_ssh in args:
            cls.set_active_controller(ssh_client=lab_ssh)

    @classmethod
    def set_default_ssh(cls, name=None):
        """
        Set ssh client to be used by default. This is usually used by
        distributed cloud.
        Unset if name=None.
        Args:
            name (str|None):
        """
        if not name:
            cls.__default_name = None
        elif name in cls.__lab_ssh_map:
            cls.__default_name = name
        else:
            raise ValueError(
                '{} is not in lab_ssh_map: {}. Please add the ssh client to '
                'lab_ssh_map via set_active_controller() before setting it '
                'to default'.format(name, cls.__lab_ssh_map))


def ssh_to_controller0(ssh_client=None):
    if ssh_client is None:
        ssh_client = ControllerClient.get_active_controller()
    if ssh_client.get_hostname() == 'controller-0':
        LOG.info("Already on controller-0. Do nothing.")
        return ssh_client
    con_0_ssh = SSHFromSSH(ssh_client=ssh_client, host='controller-0',
                           user=HostLinuxUser.get_user(),
                           password=HostLinuxUser.get_password(),
                           initial_prompt=Prompt.CONTROLLER_0)
    con_0_ssh.connect()
    return con_0_ssh


def get_cli_client(central_region=False):
    name = 'RegionOne' if central_region and ProjVar.get_var('IS_DC') else None
    return ControllerClient.get_active_controller(name=name)
