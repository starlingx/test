"""Provides a library of useful utilities.

This module provides a list of general purpose utilities. Those functions that
are part of a larger domain, for example functions related to networking,
should be provided by a different module.

This module should only include functions that are not related with a
specific application, in other words these methods should be application
agnostic.
"""

from __future__ import print_function

import os
import timeit
import pwd

from bash import bash as ebash

from Config import config
import Utils.bash_utils as bash


def find_owner(element):
    """Find the owner of a file or folder

    :param element: which can be a file or folder to check
    :return
        - the user that own the file or folder
    """

    return pwd.getpwuid(os.stat(element).st_uid).pw_name


def isdir(path, sudo=True):
    """Validates if a directory exist in a host.

    :param path: the path of the directory to be validated
    :param sudo: this needs to be set to True for directories that require
    root permission
    :return: True if the directory exists, False otherwise
    """
    status, _ = bash.run_command(
        '{prefix}test -d {path}'.format(
            path=path, prefix='sudo ' if sudo else ''))
    exist = True if not status else False
    return exist


def isfile(path, sudo=True):
    """Validates if a file exist in a host.

    :param path: the absolute path of the file to be validated
    :param sudo: this needs to be set to True for files that require
    root permission
    :return: True if the file exists, False otherwise
    """
    status, _ = bash.run_command(
        '{prefix}test -f {path}'.format(
            path=path, prefix='sudo ' if sudo else ''))
    exist = True if not status else False
    return exist


def timer(action, print_elapsed_time=True):
    """Function that works as a timer, with a start/stop button.

    :param action: the action to perform, the valid options are:
        - start: start a counter for an operation
        - stop: stop the current time
    :param print_elapsed_time: if set to False the message is not printed to
    console, only returned
    :return: the elapsed_time string variable
    """
    elapsed_time = 0
    if action.lower() == 'start':
        start = timeit.default_timer()
        os.environ['START_TIME'] = str(start)
    elif action.lower() == 'stop':
        if 'START_TIME' not in os.environ:
            bash.message('err', 'you need to start the timer first')
            return None
        stop = timeit.default_timer()
        total_time = stop - float(os.environ['START_TIME'])
        del os.environ['START_TIME']

        # output running time in a nice format.
        minutes, seconds = divmod(total_time, 60)
        hours, minutes = divmod(minutes, 60)
        elapsed_time = 'elapsed time ({h}h:{m}m:{s}s)'.format(
            h=0 if round(hours, 2) == 0.0 else round(hours, 2),
            m=0 if round(minutes, 2) == 0.0 else round(minutes, 2),
            s=round(seconds, 2))
        if print_elapsed_time:
            bash.message('info', elapsed_time)
    else:
        bash.message('err', '{0}: not allowed'.format(action))

    return elapsed_time


def clean_qemu_environment():
    """Clean Qemu/Libvirt environment

    This function clean the environment in the current host fulfilling the
    following functions:
        1. shutting down the current VMs running
        2. removing them from Virtual Machine Manager
        3. delete their partitions
    """
    images_path = '/var/lib/libvirt/images'

    vms = ebash(
        "virsh list --all | awk 'NR>2 {print $2}'").stdout.strip().split()
    partitions = ebash('sudo ls {} | grep .img$'.format(
        images_path)).stdout.split()

    for vm in vms:
        # check if the current image is running to shutting down
        cmd = ebash('sudo virsh domstate {}'.format(vm.decode('utf-8')))
        stdout = cmd.stdout.strip().decode('utf-8')
        stderr = cmd.stderr.strip().decode('utf-8')

        if stdout == 'running' and 'failed to get domain' not in stderr:
            # the vm is running
            ebash('sudo virsh destroy {}'.format(vm.decode('utf-8')))

        # removing controller/compute from Virtual Machine Manager
        ebash(
            'sudo virsh undefine {} --remove-all-storage --snapshots-metadata'
            .format(vm.decode('utf-8')))

    for partition in partitions:
        ebash('sudo rm {}/{}'.format(images_path, partition.decode('utf-8')))


def qemu_configuration_files():
    """Custom Qemu configuration files"""

    xml = config.get('qemu', 'XML')
    config_file = config.get('qemu', 'CONFIG_FILE')

    if os.path.isfile(xml):
        # deleting default libvirt networks configuration
        ebash('sudo rm -rf {}'.format(xml))

    parameters = ['user = "root"', 'group = "root"']

    for param in parameters:
        stdout = ebash("sudo cat {0} | grep -w '^{1}'".format(
            config_file, param)).stdout
        if not stdout:
            # the param not in config_file
            ebash("echo '{0}' | sudo tee -a {1}".format(param, config_file))
