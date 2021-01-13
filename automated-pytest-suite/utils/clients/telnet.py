#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import os
import re
import time
from telnetlib import Telnet, theNULL, DO, DONT, WILL, WONT, NOOPT, IAC, \
    SGA, ECHO, SE, SB

from consts.auth import HostLinuxUser
from consts.stx import DATE_OUTPUT, Prompt
from consts.proj_vars import ProjVar
from utils import exceptions
from utils.clients.ssh import PASSWORD_PROMPT, EXIT_CODE_CMD
from utils.tis_log import get_tis_logger, LOG


def telnet_logger(host):
    log_dir = ProjVar.get_var('LOG_DIR')
    if log_dir:
        log_dir = '{}/telnet'.format(log_dir)
        os.makedirs(log_dir, exist_ok=True)
        logpath = log_dir + '/telnet_' + host + ".log"
    else:
        logpath = None

    logger = get_tis_logger(logger_name='telnet_{}'.format(host),
                            log_path=logpath)

    return logger


LOGIN_REGEX = re.compile(r'^(.*[\w]+-[\d]+)( login:|:~\$)'.encode(),
                         re.MULTILINE)
TELNET_LOGIN_PROMPT = re.compile(r'^(?![L|l]ast).*[L|l]ogin:[ ]?$'.encode(),
                                 re.MULTILINE)
NEWPASSWORD_PROMPT = ''
LOGGED_IN_REGEX = re.compile(r'^(.*-[\d]+):~\$ '.encode(), re.MULTILINE)

# VT100 values
ESC = bytes([27])  # Escape character
VT100_DEVICE_STATUS = bytes([27, 91, 53, 110])  # Device Status Query
VT100_DEVICE_OK = bytes([27, 91, 48, 110])  # Device OK


class TelnetClient(Telnet):

    def __init__(self, host, prompt=None, port=0, timeout=30, hostname=None,
                 user=HostLinuxUser.get_user(),
                 password=HostLinuxUser.get_password(), negotiate=False,
                 vt100query=False, console_log_file=None):

        self.logger = LOG
        super(TelnetClient, self).__init__(host=host, port=port,
                                           timeout=timeout)

        if not hostname:
            self.send('\r\n\r\n')
            prompts = [LOGIN_REGEX, LOGGED_IN_REGEX]
            index, re_obj, matched_text = super().expect(prompts, timeout=10)
            if index in (0, 1):
                hostname = prompts[index].search(matched_text).group(1).decode(
                    errors='ignore')

        if not prompt:
            prompt = r':~\$ '

        # -- mod begins
        self.console_log_file = self.get_log_file(console_log_file)
        self.negotiate = negotiate
        self.vt100query = vt100query
        if self.vt100query:
            self.vt100querybuffer = b''  # Buffer for VT100 queries
        # -- mod ends

        self.flush(timeout=1)
        self.logger = telnet_logger(hostname) if hostname else telnet_logger(
            host + ":" + str(port))
        self.hostname = hostname
        self.prompt = prompt
        self.cmd_output = ''
        self.cmd_sent = ''
        self.timeout = timeout
        self.user = user
        self.password = password

        self.logger.info(
            'Telnet connection to {}:{} ({}) is established'.format(host, port,
                                                                    hostname))

    def connect(self, timeout=None, login=True, login_timeout=10,
                fail_ok=False):
        timeout_arg = {'timeout': timeout} if timeout else {}
        if self.eof:
            self.logger.info(
                "Re-open telnet connection to {}:{}".format(self.host,
                                                            self.port))
            self.open(host=self.host, port=self.port, **timeout_arg)

        if login:
            self.login(fail_ok=fail_ok, expect_prompt_timeout=login_timeout)

        return self.sock

    def login(self, expect_prompt_timeout=10, fail_ok=False,
              handle_init_login=False):
        self.write(b'\r\n')
        index = self.expect(blob_list=[TELNET_LOGIN_PROMPT, self.prompt],
                            timeout=expect_prompt_timeout,
                            fail_ok=fail_ok, searchwindowsize=50)
        self.flush()
        code = 0
        if index == 0:
            self.send(self.user)
            self.expect(PASSWORD_PROMPT, searchwindowsize=50,
                        timeout=expect_prompt_timeout)
            self.send(self.password)
            index = self.expect([self.prompt, TELNET_LOGIN_PROMPT],
                                searchwindowsize=50,
                                timeout=expect_prompt_timeout)
            if index == 1:
                if not handle_init_login:
                    raise exceptions.TelnetError(
                        'Unable to login to {} with credential {}/{}'.
                        format(self.hostname, self.user, self.password))
                self.send(self.user)
                self.expect(PASSWORD_PROMPT, searchwindowsize=50,
                            timeout=expect_prompt_timeout)
                self.send(
                    self.user)  # in initial login, assume password=username
                self.expect(PASSWORD_PROMPT, searchwindowsize=50,
                            timeout=expect_prompt_timeout)
                self.send(self.user)  # enter original password
                self.expect(PASSWORD_PROMPT, searchwindowsize=50,
                            timeout=expect_prompt_timeout)
                self.send(self.password)  # enter new password
                self.expect(PASSWORD_PROMPT, searchwindowsize=50,
                            timeout=expect_prompt_timeout)
                self.send(self.password)  # confirm new password
                self.expect(searchwindowsize=50, timeout=expect_prompt_timeout)

        elif index < 0:
            self.logger.warning(
                "System is not in login page and default prompt is not found "
                "either")
            code = 1

        return code

    def write(self, buffer, log=True):
        if log:
            self.logger.debug(
                'Write: {}'.format(buffer.decode(errors='ignore')))
        super(TelnetClient, self).write(buffer=buffer)

    def send(self, cmd='', reconnect=False, reconnect_timeout=300, flush=False):
        if reconnect:
            self.connect(timeout=reconnect_timeout)
        if flush:
            self.flush(timeout=1)

        cmd_for_exitcode = (cmd == EXIT_CODE_CMD)
        is_read_only_cmd = (not cmd) or re.search('show|list|cat', cmd)

        if cmd_for_exitcode or is_read_only_cmd:
            self.logger.debug("Send: {}".format(cmd))
        else:
            self.logger.info("Send: {}".format(cmd))

        self.cmd_sent = cmd
        if not cmd.endswith('\n'):
            cmd = '{}\n'.format(cmd)

        cmd = cmd.replace('\r\n', '\n')
        # cmd = cmd.replace('\n', '\r\n')
        self.write(cmd.encode(), log=False)

    def send_control(self, char='c'):
        valid_chars = ["[", "\\", "]", "^", "_"]
        if char.isalpha() or char in valid_chars:
            code = chr(ord(char.upper()) - 64)
        else:
            raise NotImplementedError("ctrl+{} is not supported".format(char))
        self.logger.info("Send: ctrl+{}".format(char))
        self.write(code.encode())

    def _process_output(self, output, rm_date=False):
        output_list = output.splitlines()
        if isinstance(output, bytes):
            output_list = [line.decode(errors='ignore') for line in output_list]

        if self.cmd_sent != '':
            output_list[0] = ''  # do not display the sent command
            if rm_date:  # remove date output if any
                if re.search(DATE_OUTPUT, output_list[-1]):
                    output_list = output_list[:-1]

        output = '\n'.join(output_list)
        self.cmd_sent = ''  # Make sure sent line is only removed once

        self.cmd_output = output
        return output

    def expect(self, blob_list=None, timeout=None, fail_ok=False, rm_date=False,
               searchwindowsize=None):
        if timeout is None:
            timeout = self.timeout
        if not blob_list:
            blob_list = self.prompt
        if isinstance(blob_list, (str, bytes)):
            blob_list = [blob_list]

        blobs = []
        for blob in blob_list:
            if isinstance(blob, str):
                blob = blob.encode()
            blobs.append(blob)

        try:
            # index, re_obj, matched_text = super(TelnetClient, self).expect(
            # list=blobs, timeout=timeout)
            index, re_obj, matched_text = super(TelnetClient, self).expect(
                blobs, timeout=timeout)
            # Reformat the output
            output = self._process_output(output=matched_text, rm_date=rm_date)
            if index >= 0:
                # Match found
                self.logger.debug("Found: {}".format(output))
                return index

            # Error handling
            self.logger.debug(
                "No match found for: {}. Actual output: {}".format(blob_list,
                                                                   output))
            if self.eof:
                err_msg = 'EOF encountered before {} appear. '.format(blob_list)
                index = -1
            else:
                err_msg = "Timed out waiting for {} to appear. ".format(
                    blob_list)
                index = -2

        except EOFError:
            err_msg = 'EOF encountered and before receiving anything. '
            index = -1

        if fail_ok:
            self.logger.warning(err_msg)
            return index

        if index == -1:
            raise exceptions.TelnetEOF(err_msg)
        elif index == -2:
            raise exceptions.TelnetTimeout(err_msg)
        else:
            raise exceptions.TelnetError(
                "Unknown error! Please update telnet expect method")

    def flush(self, timeout=3):
        time.sleep(timeout)  # Wait for given time before reading.
        buffer = self.read_very_eager()
        if buffer:
            output = '\n'.join(
                [line.decode(errors='ignore') for line in buffer.splitlines()])
            self.logger.debug("Flushed: \n{}".format(output))
        return buffer

    def exec_cmd(self, cmd, expect_timeout=None, reconnect=False,
                 reconnect_timeout=300, err_only=False, rm_date=False,
                 fail_ok=True, get_exit_code=True, blob=None, force_end=False,
                 searchwindowsize=None):
        if blob is None:
            blob = self.prompt
        if expect_timeout is None:
            expect_timeout = self.timeout

        self.logger.debug("Executing command...")
        if err_only:
            cmd += ' 1> /dev/null'
        self.send(cmd, reconnect, reconnect_timeout)
        try:
            self.expect(blob_list=blob, timeout=expect_timeout,
                        searchwindowsize=searchwindowsize)
        except exceptions.TelnetTimeout as e:
            self.send_control()
            self.expect(fail_ok=True, timeout=5)
            self.flush(timeout=1)
            if fail_ok:
                self.logger.warning(e)
            else:
                raise

        code, output = self._process_exec_result(rm_date,
                                                 get_exit_code=get_exit_code)

        self.__force_end(force_end)

        if code > 0 and not fail_ok:
            raise exceptions.SSHExecCommandFailed(
                "Non-zero return code for cmd: {}".format(cmd))

        return code, output

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
            raise exceptions.TelnetError(
                "Non-zero return code for sudo cmd: {}. Output: "
                "{}".format(cmd, output))

        return code, output

    def msg(self, msg, *args):
        return

    def _process_exec_result(self, rm_date=False, get_exit_code=True):

        cmd_output_list = self.cmd_output.splitlines()[0:-1]  # exclude prompt
        if rm_date:  # remove date output if any
            if re.search(DATE_OUTPUT, cmd_output_list[-1]):
                cmd_output_list = cmd_output_list[:-1]

        cmd_output = '\n'.join(cmd_output_list)

        if get_exit_code:
            exit_code = self.get_exit_code()
        else:
            exit_code = -1
            self.logger.debug("Actual exit code is unknown")

        cmd_output = cmd_output.strip()
        return exit_code, cmd_output

    def get_exit_code(self):
        self.flush(timeout=1)
        self.send(EXIT_CODE_CMD)
        self.expect(timeout=10)
        # LOG.debug("echo output: {}".format(self.cmd_output))
        matches = re.findall("\n([-+]?[0-9]+)\n", self.cmd_output)
        # LOG.debug("matches: {}".format(matches))
        return int(matches[-1])

    def __force_end(self, force):
        if force:
            self.flush(timeout=1)
            self.send_control('c')
            self.flush()

    def set_prompt(self, prompt):
        self.prompt = prompt

    def get_hostname(self):
        return self.exec_cmd('hostname')[1].splitlines()[0]

    def process_rawq(self):
        """Transfer from raw queue to cooked queue.

        Set self.eof when connection is closed.  Don't block unless in
        the midst of an IAC sequence.

        """
        buf = [b'', b'']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if not self.iacseq:
                    if c == theNULL:
                        continue
                    if c == b"\021":
                        continue
                        # -- mod begins
                    # deal with vt100 escape sequences
                    if self.vt100query:
                        if self.vt100querybuffer:
                            self.vt100querybuffer += c
                            if len(self.vt100querybuffer) > 10:
                                self.vt100querybuffer = b''  # too long, ignore
                            elif self.vt100querybuffer == VT100_DEVICE_STATUS:
                                self.sock.sendall(VT100_DEVICE_OK)
                                self.vt100querybuffer = b''
                        if not self.vt100querybuffer and c == ESC:
                            self.vt100querybuffer += c
                    # deal with IAC sequences
                    # -- mod ends
                    if c != IAC:
                        buf[self.sb] = buf[self.sb] + c
                        continue
                    else:
                        self.iacseq += c
                elif len(self.iacseq) == 1:
                    # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
                    if c in (DO, DONT, WILL, WONT):
                        self.iacseq += c
                        continue

                    self.iacseq = b''
                    if c == IAC:
                        buf[self.sb] = buf[self.sb] + c
                    else:
                        if c == SB:  # SB ... SE start.
                            self.sb = 1
                            self.sbdataq = b''
                        elif c == SE:
                            self.sb = 0
                            self.sbdataq = self.sbdataq + buf[1]
                            buf[1] = b''
                        if self.option_callback:
                            # Callback is supposed to look into
                            # the sbdataq
                            self.option_callback(self.sock, c, NOOPT)
                        else:
                            # We can't offer automatic processing of
                            # suboptions. Alas, we should not get any
                            # unless we did a WILL/DO before.
                            self.msg('IAC %d not recognized' % ord(c))
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1:2]
                    self.iacseq = b''
                    opt = c
                    if cmd in (DO, DONT):
                        self.msg('IAC %s %d', cmd == DO and 'DO' or 'DONT',
                                 ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            # -- mod begins
                            if self.negotiate:
                                # do some limited logic to use SGA if asked
                                if cmd == DONT and opt == SGA:
                                    self.sock.sendall(IAC + WILL + opt)
                                elif cmd == DO and opt == SGA:
                                    self.sock.sendall(IAC + WILL + opt)
                                else:
                                    self.sock.sendall(IAC + WONT + opt)
                            else:
                                # -- mod ends
                                self.sock.sendall(IAC + WONT + opt)
                    elif cmd in (WILL, WONT):
                        self.msg('IAC %s %d', cmd == WILL and 'WILL' or 'WONT',
                                 ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            # -- mod begins
                            if self.negotiate:
                                # do some limited logic to use SGA if asked
                                if cmd == WONT and opt == SGA:
                                    self.sock.sendall(IAC + DO + opt)
                                elif cmd == WILL and opt == SGA:
                                    self.sock.sendall(IAC + DO + opt)
                                elif cmd == WILL and opt == ECHO:
                                    self.sock.sendall(IAC + DO + opt)
                                else:
                                    self.sock.sendall(IAC + DONT + opt)
                            else:
                                # -- mod ends
                                self.sock.sendall(IAC + DONT + opt)
        except EOFError:  # raised by self.rawq_getchar()
            self.iacseq = b''  # Reset on EOF
            self.sb = 0
            pass
        self.cookedq = self.cookedq + buf[0]
        # -- mod begins
        self.log_write(buf[0])
        # -- mod ends
        self.sbdataq = self.sbdataq + buf[1]

    def log_write(self, text):
        if not text:
            return

        try:
            if not isinstance(text, str):
                text = text.decode('utf-8', 'ignore')
        except AttributeError as e:
            print('log_write exception: ', e)
            pass

        if self.console_log_file:
            try:
                self.console_log_file.write(text)
                self.console_log_file.flush()

            except UnicodeEncodeError:
                pass
                # -- mod ends

    def get_log_file(self, log_dir):

        if log_dir:
            logfile = open(log_dir, 'a')
        else:
            logfile = None

        return logfile
