"""Provides different network functions"""

import logging
import subprocess
from bash import bash

from elevate import elevate
from ifparser import Ifcfg
from pynetlinux import ifconfig
from pynetlinux import brctl

from Libraries.common import update_config_ini

LOG = logging.getLogger(__name__)


def delete_network_interfaces():
    """Delete network interfaces

    This function performs a clean up for the following network interfaces
    stxbr[1-4]
    """

    # elevate module re-launches the current process with root/admin privileges
    # using one of the following mechanisms : sudo (Linux, macOS)

    # becoming in root
    elevate(graphical=False)

    ifdata = Ifcfg(subprocess.check_output(['ifconfig', '-a']))

    # Destroy NAT network if exist
    try:
        bash('sudo virsh net-destroy {}'.format('stx-nat'))
        bash('sudo virsh net-undefine {}'.format('stx-nat'))
    except IOError:
        LOG.warning('NAT network not found')

    for interface in range(1, 5):
        current_interface = 'stxbr{}'.format(interface)

        if current_interface in ifdata.interfaces:
            # the network interface exists
            net_object = ifdata.get_interface(current_interface)
            net_up = net_object.get_values().get('UP')
            net_running = net_object.get_values().get('RUNNING')

            if net_up or net_running:
                # the network interface is up or running
                try:
                    # down and delete the network interface
                    ifconfig.Interface(current_interface).down()
                    brctl.Bridge(current_interface).delete()
                except IOError:
                    LOG.warning('[Errno 19] No such device: '
                                '%s', current_interface)


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
        if 'ERROR' in eval_cmd.stderr:
            LOG.error(eval_cmd.stderr)
            raise EnvironmentError(eval_cmd.stderr)

    # setting the ip tables
    iptables = ('sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -j '
                'MASQUERADE')

    eval_cmd = bash(iptables)
    if 'ERROR' in eval_cmd.stderr:
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
