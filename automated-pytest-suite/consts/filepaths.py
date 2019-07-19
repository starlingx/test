#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


class StxPath:
    TIS_UBUNTU_PATH = '~/userdata/ubuntu_if_config.sh'
    TIS_CENTOS_PATH = '~/userdata/centos_if_config.sh'
    USERDATA = '~/userdata/'
    IMAGES = '~/images/'
    HEAT = '~/heat/'
    BACKUPS = '/opt/backups'
    CUSTOM_HEAT_TEMPLATES = '~/custom_heat_templates/'
    HELM_CHARTS_DIR = '/www/pages/helm_charts/'
    DOCKER_CONF = '/etc/docker-distribution/registry/config.yml'
    DOCKER_REPO = '/var/lib/docker-distribution/docker/registry/v2/repositories'


class VMPath:
    VM_IF_PATH_UBUNTU = '/etc/network/interfaces.d/'
    ETH_PATH_UBUNTU = '/etc/network/interfaces.d/{}.cfg'
    # Below two paths are common for CentOS, OpenSUSE, and RHEL
    VM_IF_PATH_CENTOS = '/etc/sysconfig/network-scripts/'
    ETH_PATH_CENTOS = '/etc/sysconfig/network-scripts/ifcfg-{}'

    # Centos paths for ipv4:
    RT_TABLES = '/etc/iproute2/rt_tables'
    ETH_RT_SCRIPT = '/etc/sysconfig/network-scripts/route-{}'
    ETH_RULE_SCRIPT = '/etc/sysconfig/network-scripts/rule-{}'
    ETH_ARP_ANNOUNCE = '/proc/sys/net/ipv4/conf/{}/arp_announce'
    ETH_ARP_FILTER = '/proc/sys/net/ipv4/conf/{}/arp_filter'


class UserData:
    ADDUSER_TO_GUEST = 'cloud_config_adduser.txt'
    DPDK_USER_DATA = 'dpdk_user_data.txt'


class TestServerPath:
    USER_DATA = '/home/svc-cgcsauto/userdata/'
    TEST_SCRIPT = '/home/svc-cgcsauto/test_scripts/'
    CUSTOM_HEAT_TEMPLATES = '/sandbox/custom_heat_templates/'
    CUSTOM_APPS = '/sandbox/custom_apps/'


class PrivKeyPath:
    OPT_PLATFORM = '/opt/platform/id_rsa'
    SYS_HOME = '~/.ssh/id_rsa'


class SysLogPath:
    DC_MANAGER = '/var/log/dcmanager/dcmanager.log'
    DC_ORCH = '/var/log/dcorch/dcorch.log'
