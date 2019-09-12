#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import getpass
import os
import re
import socket
import sys
import time

import pexpect

from consts.proj_vars import ProjVar
from consts.stx import PING_LOSS_RATE
from utils import exceptions
from utils.clients.ssh import SSHClient
from utils.tis_log import LOG

LOCAL_HOST = socket.gethostname()
LOCAL_USER = getpass.getuser()
LOCAL_PROMPT = re.escape('{}@{}$ '.format(
    LOCAL_USER, LOCAL_HOST.split(sep='.wrs.com')[0])).replace(r'\$ ', r'.*\$')
COUNT = 0


def get_unique_name(name_str):
    global COUNT
    COUNT += 1
    return '{}-{}'.format(name_str, COUNT)


class LocalHostClient(SSHClient):
    def __init__(self, initial_prompt=None, timeout=60,
                 session=None, searchwindowsisze=None, name=None,
                 connect=False):
        """

        Args:
            initial_prompt
            timeout
            session
            searchwindowsisze
            connect (bool)

        Returns:

        """
        if not initial_prompt:
            initial_prompt = LOCAL_PROMPT
        if not name:
            name = 'localclient'
        self.name = get_unique_name(name)
        super(LocalHostClient, self).__init__(
            host=LOCAL_HOST, user=LOCAL_USER,
            password=None,
            force_password=False,
            initial_prompt=initial_prompt,
            timeout=timeout, session=session,
            searchwindownsize=searchwindowsisze)

        if connect:
            self.connect()

    def connect(self, retry=False, retry_interval=3, retry_timeout=300,
                prompt=None,
                use_current=True, timeout=None):
        # Do nothing if current session is connected and force_close is False:
        if use_current and self.is_connected():
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
        end_time = time.time() + retry_timeout
        while time.time() < end_time:
            try:
                LOG.debug(
                    "Attempt to connect to localhost - {}".format(self.host))
                self.session = pexpect.spawnu(command='bash', timeout=timeout,
                                              maxread=100000)

                self.logpath = self._get_logpath()
                if self.logpath:
                    self.session.logfile = open(self.logpath, 'w+')

                # Set prompt for matching
                self.set_prompt(prompt)
                self.send(r'export PS1="\u@\h\$ "')
                self.expect()
                LOG.debug("Connected to localhost!")
                return

            except (OSError, pexpect.TIMEOUT, pexpect.EOF):
                if not retry:
                    raise

            self.close()
            LOG.debug("Retry in {} seconds".format(retry_interval))
            time.sleep(retry_interval)

        else:
            raise exceptions.LocalHostError(
                "Unable to spawn pexpect object on {}. Expected prompt: "
                "{}".format(self.host, self.prompt))

    def remove_virtualenv(self, venv_name=None, venv_dir=None, fail_ok=False,
                          deactivate_first=True,
                          python_executable=None):

        if not python_executable:
            python_executable = sys.executable

        if not venv_name:
            venv_name = ProjVar.get_var('RELEASE')
        venv_dir = _get_virtualenv_dir(venv_dir)

        if deactivate_first:
            self.deactivate_virtualenv(venv_name=venv_name)

        LOG.info("Removing virtualenv {}/{}".format(venv_dir, venv_name))
        cmd = "export WORKON_HOME={}; export VIRTUALENVWRAPPER_PYTHON={}; " \
              "source virtualenvwrapper.sh". \
            format(venv_dir, python_executable)
        code, output = self.exec_cmd(cmd=cmd, fail_ok=fail_ok)
        if code == 0:
            code = self.exec_cmd("rmvirtualenv {}".format(venv_name),
                                 fail_ok=fail_ok)[0]
            if code == 0:
                # Remove files generated by virtualwrapper
                for line in output.splitlines():
                    if 'user_scripts creating ' in line:
                        new_file = output.split('user_scripts creating ')[-1].\
                            strip()
                        self.exec_cmd('rm -f {}'.format(new_file))
                LOG.info('virtualenv {} removed successfully'.format(venv_name))
                return True

        return False

    def create_virtualenv(self, venv_name=None, venv_dir=None, activate=True,
                          fail_ok=False, check_first=True,
                          python_executable=None):
        if not venv_name:
            venv_name = ProjVar.get_var('RELEASE')
        venv_dir = _get_virtualenv_dir(venv_dir)

        if check_first:
            if self.file_exists(
                    os.path.join(venv_dir, venv_name, 'bin', 'activate')):
                if activate:
                    self.activate_virtualenv(venv_name=venv_name,
                                             venv_dir=venv_dir, fail_ok=fail_ok)
                return

        if not python_executable:
            python_executable = sys.executable

        LOG.info("Creating virtualenv {}/{}".format(venv_dir, venv_name))
        os.makedirs(venv_dir, exist_ok=True)
        cmd = "cd {}; virtualenv --python={} {}".format(venv_dir,
                                                        python_executable,
                                                        venv_name)
        code = self.exec_cmd(cmd=cmd, fail_ok=fail_ok)[0]
        if code == 0:
            LOG.info('virtualenv {} created successfully'.format(venv_name))
            if activate:
                self.activate_virtualenv(venv_name=venv_name, venv_dir=venv_dir,
                                         fail_ok=fail_ok)

        return venv_name, venv_dir, python_executable

    def activate_virtualenv(self, venv_name=None, venv_dir=None, fail_ok=False):
        if not venv_name:
            venv_name = ProjVar.get_var('RELEASE')
        venv_dir = _get_virtualenv_dir(venv_dir)
        assert os.path.exists(venv_dir)

        LOG.info("Activating virtualenv {}/{}".format(venv_dir, venv_name))
        code = self.exec_cmd(
            'cd {}; source {}/bin/activate'.format(venv_dir, venv_name),
            fail_ok=fail_ok)[0]
        if code == 0:
            new_prompt = r'\({}\) {}'.format(venv_name, self.get_prompt())
            self.set_prompt(prompt=new_prompt)
            LOG.info('virtualenv {} activated successfully'.format(venv_name))

        time.sleep(3)
        code, output = self.exec_cmd('pip -V')
        if code != 0:
            LOG.warning('pip is not working properly. Listing env variables.')
            all_env = self.exec_cmd('declare -p')[1]
            LOG.info("declare -p: \n{}".format(all_env))

    def deactivate_virtualenv(self, venv_name, new_prompt=None):
        # determine on the new prompt
        if not new_prompt:
            if venv_name in self.prompt:
                new_prompt = self.prompt.split(r'\({}\) '.format(venv_name))[-1]
            else:
                new_prompt = self.initial_prompt

        LOG.info("Deactivating virtualenv {}".format(venv_name))
        self.set_prompt(new_prompt)
        code, output = self.exec_cmd('deactivate', fail_ok=True)
        if code == 0 or 'command not found' in output:
            LOG.info('virtualenv {} deactivated successfully'.format(venv_name))
        else:
            raise exceptions.LocalHostError(
                "Unable to deactivate venv. Output: {}".format(output))

    def get_ssh_key(self, ssh_key_path=None):
        if not ssh_key_path:
            ssh_key_path = os.path.expanduser('~/.ssh/id_rsa_stxauto')
        # KNOWN_HOSTS_PATH = SSH_DIR + "/known_hosts"
        # REMOVE_HOSTS_SSH_KEY_CMD = "ssh-keygen -f {} -R {}"
        if not self.file_exists(ssh_key_path):
            self.exec_cmd("ssh-keygen -f {} -t rsa -N ''".format(ssh_key_path),
                          fail_ok=False)
        ssh_key = self.exec_cmd(
            "ssh-keygen -y -f {} -P ''".format(ssh_key_path), fail_ok=False)

        return ssh_key

    def ping_server(self, server, ping_count=5, timeout=60, fail_ok=False,
                    retry=0):
        """

        Args:
            server (str): server ip to ping
            ping_count (int):
            timeout (int): max time to wait for ping response in seconds
            fail_ok (bool): whether to raise exception if packet loss rate is
            100%
            retry (int):

        Returns (int): packet loss percentile, such as 100, 0, 25

        """
        output = packet_loss_rate = None
        for i in range(max(retry + 1, 1)):
            cmd = 'ping -c {} {}'.format(ping_count, server)
            code, output = self.exec_cmd(cmd=cmd, expect_timeout=timeout,
                                         fail_ok=True)
            if code != 0:
                packet_loss_rate = 100
            else:
                packet_loss_rate = re.findall(PING_LOSS_RATE, output)[-1]

            packet_loss_rate = int(packet_loss_rate)
            if packet_loss_rate < 100:
                if packet_loss_rate > 0:
                    LOG.warning(
                        "Some packets dropped when ping from {} ssh session "
                        "to {}. Packet loss rate: {}%".
                        format(self.host, server, packet_loss_rate))
                else:
                    LOG.info("All packets received by {}".format(server))
                break

            LOG.info("retry in 3 seconds")
            time.sleep(3)
        else:
            msg = "Ping from {} to {} failed.".format(self.host, server)
            if not fail_ok:
                raise exceptions.LocalHostError(msg)
            else:
                LOG.warning(msg)

        untransmitted_packets = re.findall(r"(\d+) packets transmitted,",
                                           output)
        if untransmitted_packets:
            untransmitted_packets = int(ping_count) - int(
                untransmitted_packets[0])
        else:
            untransmitted_packets = ping_count

        return packet_loss_rate, untransmitted_packets


def _get_virtualenv_dir(venv_dir=None):
    if not venv_dir:
        if ProjVar.get_var('LOG_DIR'):
            lab_logs_dir = os.path.dirname(ProjVar.get_var(
                'LOG_DIR'))  # e.g., .../AUTOMATION_LOGS/ip_18_19/
            venv_dir = os.path.join(lab_logs_dir, '.virtualenvs')
        else:
            venv_dir = os.path.expanduser('~')
    return venv_dir