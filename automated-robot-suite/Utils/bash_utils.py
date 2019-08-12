"""Manages execution of bash commands.

Executes bash commands in the underlying system and formats the output
in a consistent manner.

The functions that belong to this package are the ones that meet this criteria:
- All those that rely on running a command in the shell (bash) to work.
- All those related to printing/formatting messages for the console.
- This module should only include functions that are not related with a
specific application.

Note: Since a lot of functions in this package need to run a in a shell, this
package should most of the times only be used in Linux.
"""

from __future__ import print_function

import os
import re
import subprocess

# Defines a color schema for messages.
PURPLE = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
GREY = '\033[90m'
BLACK = '\033[90m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
DEFAULT = '\033[99m'
END = '\033[0m'

# --------------------------------------------------------
# Functions for printing formatted messages in the console
# --------------------------------------------------------


def message(message_type, msg, end_string=None):
    """Wrapper that provides format to messages based on message type.

    The function prints messages of the following type:
    '>>> (success) hello world'
    '>>> (err) bye bye world'

    :param message_type: specifies the type of message
    :param msg: the message to be formatted
    :param end_string: specifies a different character to end the
    message, if None is specified it uses a newline
    """
    if message_type == 'err':
        print(RED + '>>> (err) ' + END + msg, end=end_string)
    elif message_type == 'warn':
        print(YELLOW + '>>> (warn) ' + END + msg, end=end_string)
    elif message_type == 'info':
        print(BLUE + '>>> (info) ' + END + msg, end=end_string)
    elif message_type == 'ok':
        print(GREEN + '>>> (success) ' + END + msg, end=end_string)
    elif message_type == 'statistics':
        print(CYAN + '>>> (data) ' + END + msg, end=end_string)
    elif message_type == 'cmd':
        print(CYAN + '>>> (cmd) ' + END + msg, end=end_string)
    elif message_type == 'skip':
        print(
            BLUE + '>>> (info) ' + END + msg + ' ... [' + YELLOW + 'SKIP' +
            END + ']', end=end_string)
    else:
        raise ValueError('Invalid argument.')


def load_openrc_env_variables():
    """Loading OpenStack credentials

    This function will load environment variables needed to run OpenStack
    commands through CLI and will return this variables to robot framework

    :returns: dictionary -- with environment variables containing OpenStack
    credentials loaded.
    """
    command = ['bash', '-c', 'source /etc/nova/openrc && env']

    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, executable='/bin/bash')

    for line in proc.stdout:
        (key, _, value) = line.partition('=')
        os.environ[key] = value[:-1]

    return dict(os.environ)


# -------------------------------------------
# Functions for running commands in the shell
# -------------------------------------------


def run_command(command, raise_exception=False):
    """Runs a shell command in the host.

    :param command: the command to be executed
    :param raise_exception: if is setup as True it will raise a exception if
        the command was not executed correctly
    :return: a tuple that contains the exit code of the command executed,
    and the output message of the command.
    """
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
        executable='/bin/bash')
    output, error = proc.communicate()
    output = output.strip() if output else output
    error = error.strip() if error else error

    if raise_exception and proc.returncode != 0:
        raise RuntimeError('{}: {}'.format(command, error or output))

    return proc.returncode, error or output


# ---------------------------------------------
# Functions that rely on running shell commands
# ---------------------------------------------


def is_process_running(process, pid_to_exclude=''):
    """Checks if a process is running.

    :param process: the process to check. This can either be a PID or the
    command used to start the process
    :param pid_to_exclude: int values are accepted only. If this param is set,
    this function will exclude the pid on this variable.
    :return:
        True: if the process is still running.
        False: if the process has finished (was not found)
    """
    ps_aux = subprocess.Popen(['ps', 'axw'], stdout=subprocess.PIPE)
    for element in ps_aux.stdout:
        if re.search(process, element.decode('utf-8')):
            pid = int(element.split()[0])
            if pid_to_exclude and pid == pid_to_exclude:
                continue
            else:
                return True
    return False
