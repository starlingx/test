###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Performs basic host management operations: Lock unlock hosts, switch controllers
# Author(s): Oliver Lovaszi oliver.lovaszi@intel.com
###

import os
from pytest import mark, skip

from keywords import container_helper, host_helper, kube_helper
from keywords import keystone_helper, network_helper, system_helper
from testfixtures.pre_checks_and_configs import no_simplex, no_duplex, simplex_only
from consts.proj_vars import ProjVar
from consts.stx import AppStatus, EventLogID, SysType
from utils import cli
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient

PHYSNET0 = "physnet0"
PHYSNET1 = "physnet1"
EXTERNALNET = "external-net0"
PUBLICNET = "public-net0"
PRIVATENET = "private-net0"
INTERNALNET = "internal-net0"
PUBLICSUBNET = "public-subnet0"
PRIVATESUBNET = "private-subnet0"
INTERNALSUBNET = "internal-subnet0"
EXTERNALSUBNET = "external-subnet0"
PUBLICROUTER = "public-router0"
PRIVATEROUTER = "private-router0"


@mark.robotsanity
def test_host_status():
    """
    System overview
    """
    active_controller_host = system_helper.get_active_controller_name()
    LOG.info("Active Controller: {}".format(active_controller_host))
    standby_controller_host = system_helper.get_standby_controller_name()
    LOG.info("Standby Controller {}".format(standby_controller_host))
    host_list = system_helper.get_hosts()
    for host in host_list:
        LOG.info("Host: {}".format(host))


@mark.robotsanity
def test_add_controller_host(simplex_only):
    """
    Add controller host - it must fail on simplex
    LOG.info(system_helper.get_hosts())
    """
    # TODO: helper function needs to be implemented
    # host_helper.add_host(host="controller-1")


@mark.robotsanity
def test_swact_controller_host():
    """
    SWACT Controller host - it must fail on simplex
    """
    active_controller_host = system_helper.get_active_controller_name()
    LOG.info("Active Controller Before SWACT: {}".format(active_controller_host))
    standby_controller_host = system_helper.get_standby_controller_name()
    LOG.info("Standby Controller Before SWACT: {}".format(standby_controller_host))

    # On simplex swact must fail
    host_helper.swact_host(fail_ok=system_helper.is_aio_simplex())
    # host_helper.wait_for_swact_complete(before_host=active_controller_host)

    active_controller_host = system_helper.get_active_controller_name()
    LOG.info("Active Controller After SWACT: {}".format(active_controller_host))
    standby_controller_host = system_helper.get_standby_controller_name()
    LOG.info("Standby Controller After SWACT: {}".format(standby_controller_host))

    # Re-SWACT only if duplex
    if not system_helper.is_aio_simplex():
        host_helper.swact_host()
        # host_helper.wait_for_swact_complete(before_host=active_controller_host)


@mark.robotsanity
def test_lock_unlock_active_controller():
    """
    Lock - Unlock an active controller
    """
    active_conroller_host = system_helper.get_active_controller_name()
    LOG.info("Active Controller Host: {}".format(active_conroller_host))
    if system_helper.is_aio_simplex():
        host_helper.lock_host(host=active_conroller_host, fail_ok=False)
        rc, output = host_helper.unlock_host(host=active_conroller_host, fail_ok=True)
        if rc == 1 and "Not patch current" in output:
            con_ssh = ControllerClient.get_active_controller()
            cmd = "sw-patch host-install controller-0"
            con_ssh.exec_sudo_cmd(cmd=cmd)
            host_helper.unlock_host(host=active_conroller_host, fail_ok=False)
    else:
        rc, output = host_helper.lock_host(host=active_conroller_host, fail_ok=True)
        assert rc == 1
        assert "Can not lock an active controller" in output


@mark.robotsanity
def test_lock_unlock_standby_controller(no_simplex):
    """
    Lock - Unlock standby controller
    """
    standby_controller_host = system_helper.get_standby_controller_name()
    LOG.info("Standby Controller Host: {}".format(standby_controller_host))
    assert standby_controller_host, "Standby controller not found"

    # Lock
    host_helper.lock_host(host=standby_controller_host, fail_ok=False)

    container_helper.wait_for_apps_status(apps="stx-openstack", status=AppStatus.APPLIED,
                                          timeout=600, check_interval=60)
    # Unlock
    host_helper.unlock_host(host=standby_controller_host, fail_ok=False)
    host_helper.wait_for_hosts_ready(hosts=standby_controller_host)


@mark.robotsanity
def test_lock_unlock_compute_hosts(no_simplex, no_duplex):
    """
    Lock - Unlock Compute Hosts
    """
    compute_hosts = system_helper.get_computes()
    LOG.info(" Compute nodes found: {}".format(len(compute_hosts)))

    for host in compute_hosts:
        LOG.info("Compute Host: {}".format(host))

        # Lock
        host_helper.lock_host(host=host, fail_ok=False)
        host_helper.wait_for_hosts_ready(hosts=host)

        container_helper.wait_for_apps_status(apps="stx-openstack", status=AppStatus.APPLIED,
                                              timeout=600, check_interval=60)
        # Unlock
        host_helper.unlock_host(host=host, fail_ok=False)
        host_helper.wait_for_hosts_ready(hosts=host)


@mark.robotsanity
def test_lock_unlock_storage_hosts(no_simplex, no_duplex):
    """
    Lock - Unlock Storage Hosts
    """
    if ProjVar.get_var('SYS_TYPE') != SysType.STORAGE:
        skip('Only applicable to Standard-external system')

    storage_hosts = system_helper.get_storage_nodes()
    LOG.info(" Storage nodes found: {}".format(len(storage_hosts)))

    for host in storage_hosts:
        LOG.info("Storage Host: {}".format(host))

        # Lock
        host_helper.lock_host(host=host, fail_ok=False)
        host_helper.wait_for_hosts_ready(hosts=host)

        container_helper.wait_for_apps_status(apps="stx-openstack", status=AppStatus.APPLIED,
                                              timeout=600, check_interval=60)
        # Unlock
        host_helper.unlock_host(host=host, fail_ok=False)
        host_helper.wait_for_hosts_ready(hosts=host)


@mark.robotsanity
def test_reboot_standby_controller(no_simplex):
    active, standby = system_helper.get_active_standby_controllers()
    LOG.tc_step("'sudo reboot -f' from {}".format(standby))
    host_helper.reboot_hosts(standby, wait_for_offline=True,
                             wait_for_reboot_finish=True, force_reboot=True)
    system_helper.wait_for_hosts_states(standby,
                                        timeout=360,
                                        check_interval=30,
                                        availability=['available'])
    kube_helper.wait_for_pods_healthy(check_interval=30,
                                      all_namespaces=True)

@mark.robotsanity
def test_reboot_active_controller(no_simplex):
    active, standby = system_helper.get_active_standby_controllers()
    LOG.tc_step("'sudo reboot -f' from {}".format(active))
    host_helper.reboot_hosts(active, wait_for_offline=True,
                             wait_for_reboot_finish=True, force_reboot=True)
    system_helper.wait_for_hosts_states(standby,
                                        timeout=360,
                                        check_interval=30,
                                        availability=['available'])
    kube_helper.wait_for_pods_healthy(check_interval=30,
                                      all_namespaces=True)
    container_helper.wait_for_apps_status(apps="stx-openstack", status=AppStatus.APPLIED,
                                              timeout=600, check_interval=60)
    host_helper.swact_host(hostname=standby)


@mark.robotsanity
def test_reapply_openstack():
    container_helper.wait_for_apps_status(apps="stx-openstack", status=AppStatus.APPLIED,
                                          timeout=600, check_interval=60)
    container_helper.remove_app(app_name="stx-openstack", check_first=True)
    alarm_id = EventLogID.CONFIG_OUT_OF_DATE
    if system_helper.wait_for_alarm(alarm_id=alarm_id,
                                    entity_id='controller',
                                    timeout=15, fail_ok=True)[0]:
        system_helper.wait_for_alarm_gone(alarm_id=alarm_id,
                                          entity_id='controller',
                                          timeout=120,
                                          check_interval=10)
    container_helper.apply_app(app_name="stx-openstack", check_first=False,
                               check_interval=300, applied_timeout=5400)
    provider_network_setup(PHYSNET0, PHYSNET1)
    tenant_networking_setup(physnet0=PHYSNET0, physnet1=PHYSNET1, externalnet=EXTERNALNET,
                            publicnet=PUBLICNET, privatenet=PRIVATENET, internalnet=INTERNALNET,
                            publicsubnet=PUBLICSUBNET, privatesubnet=PRIVATESUBNET,
                            internalsubnet=INTERNALSUBNET, externalsubnet=EXTERNALSUBNET,
                            publicrouter=PUBLICROUTER, privaterouter=PRIVATEROUTER)


def provider_network_setup(physnet0, physnet1):
    adminid = keystone_helper.get_projects(name='admin')[0]
    cli.openstack('network segment range create {}-a '
                  '--network-type vlan '
                  '--physical-network {} '
                  '--minimum 400 --maximum 499 '
                  '--private '
                  '--project {}'.format(physnet0, physnet0, adminid), fail_ok=False)
    cli.openstack('network segment range create {}-b '
                  '--network-type vlan '
                  '--physical-network {} '
                  '--minimum 10 --maximum 10'.format(physnet0, physnet0), fail_ok=False)
    cli.openstack('network segment range create {}-a '
                  '--network-type vlan '
                  '--physical-network {} '
                  '--minimum 500 --maximum 599 '
                  '--private '
                  '--project {}'.format(physnet1, physnet1, adminid))


def tenant_networking_setup(physnet0, physnet1, externalnet, publicnet, privatenet, internalnet,
                            publicsubnet, privatesubnet, internalsubnet, externalsubnet,
                            publicrouter, privaterouter):
    adminid = keystone_helper.get_projects(name='admin')[0]
    cli.openstack('network create --project {} '
                  '--provider-network-type=vlan '
                  '--provider-physical-network={} '
                  '--provider-segment=10 '
                  '--share --external {}'.format(adminid, physnet0, externalnet))
    cli.openstack('network create --project {} '
                  '--provider-network-type=vlan '
                  '--provider-physical-network={} '
                  '--provider-segment=400 {}'.format(adminid, physnet0, publicnet))
    cli.openstack('network create --project {} '
                  '--provider-network-type=vlan '
                  '--provider-physical-network={} '
                  '--provider-segment=500 {}'.format(adminid, physnet1, privatenet))
    cli.openstack('network create --project {} {}'.format(adminid, internalnet))
    # publicnetid = network_helper.get_networks(full_name=publicnet)[0]
    # privatenetid = network_helper.get_networks(full_name=privatenet)[0]
    # internalnetid = network_helper.get_networks(full_name=internalnet)[0]
    externalnetid = network_helper.get_networks(full_name=externalnet)[0]
    cli.openstack('subnet create --project {} '
                  '{} '
                  '--network {} '
                  '--subnet-range 192.168.101.0/24'.format(adminid, publicsubnet, publicnet))
    cli.openstack('subnet create --project {} '
                  '{} '
                  '--network {} '
                  '--subnet-range 192.168.201.0/24'.format(adminid, privatesubnet, privatenet))
    cli.openstack('subnet create --project {} '
                  '{} '
                  '--gateway none '
                  '--network {} '
                  '--subnet-range 10.1.1.0/24'.format(adminid, internalsubnet, internalnet))
    cli.openstack('subnet create --project {} '
                  '{} '
                  '--gateway 192.168.1.1 '
                  '--network {} '
                  '--subnet-range 192.168.1.0/24 '
                  '--ip-version 4'.format(adminid, externalsubnet, externalnet))
    publicrouterid = network_helper.create_router(name=publicrouter)[1]
    privaterouterid = network_helper.create_router(name=privaterouter)[1]
    cli.openstack('router set {} '
                  '--external-gateway {} '
                  '--disable-snat'.format(publicrouterid, externalnetid))
    cli.openstack('router set {} '
                  '--external-gateway {} '
                  '--disable-snat'.format(privaterouterid, externalnetid))
    cli.openstack('router add subnet {} {}'.format(publicrouter, publicsubnet))
    cli.openstack('router add subnet {} {}'.format(privaterouter, privatesubnet))
