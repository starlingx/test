"""Provides different network functions"""

import logging
import re
import subprocess
from bash import bash

from elevate import elevate
from pynetlinux import ifconfig
from pynetlinux import brctl

from Libraries.common import update_config_ini

LOG = logging.getLogger(__name__)

class NetInterface:
    """ Represent the status of a network interface."""
    def __init__(self, name, flags):
        self.name = name
        self.up = False
        self.running = False
        self.set_flags(flags)

    def set_flags(self, flags):
        if "UP" in flags:
            self.up = True
        if "RUNNING" in flags:
            self.running = True

class NetIfs:
    """ Retrieves the list of network interfaces in the system."""
    def __init__(self):
        self.interfaces = []
        output = subprocess.check_output(['ifconfig', '-a'])
        # Regex to get the interface line from ifconfig
        regex = re.compile(r"(\w+?\-*\w+):\sflags=\d+<(.*)>\s+mtu\s\d+")
        for o in output.decode('utf-8').split('\n'):
            m = regex.match(o)
            if m:
                new_interface = NetInterface(m.group(1), m.group(2))
                self.interfaces.append(new_interface)

    def is_up(self, if_name):
        idx = self.interfaces.index(if_name)
        return self.interfaces[idx].up

    def is_running(self, if_name):
        idx = self.interfaces.index(if_name)
        return self.interfaces[idx].running


def delete_network_interfaces():
    """Delete network interfaces

    This function performs a clean up for the following network interfaces
    stxbr[1-4]
    """

    # elevate module re-launches the current process with root/admin privileges
    # using one of the following mechanisms : sudo (Linux, macOS)

    # becoming in root
    elevate(graphical=False)

    ifdata = NetIfs()

    # Destroy NAT network if exist
    try:
        bash('sudo virsh net-destroy {}'.format('stx-nat'))
        bash('sudo virsh net-undefine {}'.format('stx-nat'))
    except IOError:
        LOG.warning('NAT network not found')

    for interface in range(1, 5):
        net_if = 'stxbr{}'.format(interface)

        if net_if in ifdata.interfaces:

            if ifdata.is_up(net_if) or \
               ifdata.is_running(net_if):
                # the network interface is up or running
                try:
                    # down and delete the network interface
                    ifconfig.Interface(net_if).down()
                    brctl.Bridge(net_if).delete()
                except IOError:
                    LOG.warning('[Errno 19] No such device: '
                                '%s', net_if)


def configure_network_interfaces():
    """Configure network interfaces

    This function configure the following network interfaces stxbr[1-4]
    """

    for interface in range(1, 5):
        current_interface = 'stxbr{}'.format(interface)
        # adding the network interface
        try:
            brctl.addbr(current_interface)
        except IOError:
            LOG.warning('[Errno 17] File exists %s', current_interface)

    networks = ['stxbr1 10.10.10.1/24', 'stxbr2 192.168.204.1/24',
                'stxbr3', 'stxbr4']

    for net in networks:
        eval_cmd = bash('sudo ifconfig {} up'.format(net))
        if 'ERROR'.encode('utf-8') in eval_cmd.stderr:
            LOG.error(eval_cmd.stderr)
            raise EnvironmentError(eval_cmd.stderr)

    # setting the ip tables
    iptables = ('sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -j '
                'MASQUERADE')

    eval_cmd = bash(iptables)
    if 'ERROR'.encode('utf-8') in eval_cmd.stderr:
        LOG.error(eval_cmd.stderr)
        raise EnvironmentError(eval_cmd.stderr)


def update_networks_config(
        network_interfaces, configuration_file, configuration_type):
    """Update a config.ini with the networks from the controller

    :param network_interfaces: the network interfaces from the controller
    :param configuration_file: the absolute path to the config.ini to be
           updated
    :param configuration_type: the type of configuration to be updated
    """

    if configuration_type == 'simplex':
        update_config_ini(config_ini=configuration_file,
                          config_section='logical_interface',
                          OAM=network_interfaces[0])
    else:
        update_config_ini(config_ini=configuration_file,
                          config_section='logical_interface',
                          MGMT=network_interfaces[1])
        update_config_ini(config_ini=configuration_file,
                          config_section='logical_interface',
                          OAM=network_interfaces[0])
