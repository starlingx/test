#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture

from utils import table_parser, cli
from utils.tis_log import LOG
from keywords import host_helper, system_helper


@fixture(scope='function', autouse=True)
def hosts_recover_func(request):
    def recover_():
        hosts = HostsToRecover._get_hosts_to_recover(scope='function')
        if hosts:
            HostsToRecover._reset('function')
            HostsToRecover._recover_hosts(hosts, 'function')

    request.addfinalizer(recover_)


@fixture(scope='class', autouse=True)
def hosts_recover_class(request):
    def recover_hosts():
        hosts = HostsToRecover._get_hosts_to_recover(scope='class')
        if hosts:
            HostsToRecover._reset('class')
            HostsToRecover._recover_hosts(hosts, 'class')

    request.addfinalizer(recover_hosts)


@fixture(scope='module', autouse=True)
def hosts_recover_module(request):
    def recover_hosts():
        hosts = HostsToRecover._get_hosts_to_recover(scope='module')
        if hosts:
            HostsToRecover._reset('module')
            HostsToRecover._recover_hosts(hosts, 'module')

    request.addfinalizer(recover_hosts)


class HostsToRecover():
    __hosts_to_recover = {
        'function': [],
        'class': [],
        'module': [],
    }

    @classmethod
    def __check_scope(cls, scope):
        valid_scope = cls.__hosts_to_recover.keys()
        if scope not in valid_scope:
            raise ValueError(
                "scope has to be one of the following: {}".format(valid_scope))

    @classmethod
    def add(cls, hostnames, scope='function'):
        """
        Add host(s) to recover list. Will wait for host(s) to recover as test
        teardown.

        Args:
            hostnames (str|list):
            scope

        """
        if scope is None:
            return

        cls.__check_scope(scope)
        if isinstance(hostnames, str):
            hostnames = [hostnames]

        cls.__hosts_to_recover[scope] += hostnames

    @classmethod
    def remove(cls, hostnames, scope='function'):
        """
        Remove host(s) from recover list. Only remove one instance if host
        has multiple occurances in the recover list.

        Args:
            hostnames (str|list|tuple):
            scope:

        """
        if scope is None:
            return

        cls.__check_scope(scope)

        if isinstance(hostnames, str):
            hostnames = [hostnames]

        for host in hostnames:
            cls.__hosts_to_recover[scope].remove(host)

    @classmethod
    def _reset(cls, scope):
        cls.__hosts_to_recover[scope] = []

    @classmethod
    def _get_hosts_to_recover(cls, scope):
        return list(cls.__hosts_to_recover[scope])

    @staticmethod
    def _recover_hosts(hostnames, scope):
        if system_helper.is_aio_simplex():
            LOG.fixture_step('{} Recover simplex host'.format(scope))
            host_helper.recover_simplex(fail_ok=False)
            return

        # Recover hosts for non-simplex system
        hostnames = sorted(set(hostnames))
        table_ = table_parser.table(cli.system('host-list')[1])
        table_ = table_parser.filter_table(table_, hostname=hostnames)

        # unlocked_hosts = table_parser.get_values(table_, 'hostname',
        # administrative='unlocked')
        locked_hosts = table_parser.get_values(table_, 'hostname',
                                               administrative='locked')

        err_msg = []
        if locked_hosts:
            LOG.fixture_step(
                "({}) Unlock hosts: {}".format(scope, locked_hosts))
            # Hypervisor state will be checked later in wait_for_hosts_ready
            # which handles platform only deployment
            res1 = host_helper.unlock_hosts(hosts=locked_hosts, fail_ok=True,
                                            check_hypervisor_up=False)
            for host in res1:
                if res1[host][0] not in [0, 4]:
                    err_msg.append(
                        "Not all host(s) unlocked successfully. Detail: "
                        "{}".format(res1))

        host_helper.wait_for_hosts_ready(hostnames)
