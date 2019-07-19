#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import pytest
from utils.tis_log import LOG
from utils.rest import Rest

from testcases.rest import rest_test_helper


@pytest.fixture(scope='module')
def sysinv_rest():
    r = Rest('sysinv', platform=True)
    return r


@pytest.mark.parametrize(
    'operation,resource', [
        ('GET', '/addrpools'),
        ('GET', '/ceph_mon'),
        ('GET', '/clusters'),
        ('GET', '/controller_fs'),
        ('GET', '/drbdconfig'),
        ('GET', '/event_log'),
        ('GET', '/event_suppression'),
        ('GET', '/health'),
        ('GET', '/health/upgrade'),
        ('GET', '/ialarms'),
        ('GET', '/icommunity'),
        ('GET', '/idns'),
        ('GET', '/iextoam'),
        ('GET', '/ihosts'),
        ('GET', '/ihosts/bulk_export'),
        ('GET', '/iinfra'),
        ('GET', '/intp'),
        ('GET', '/ipm'),
        ('GET', '/iprofiles'),
        ('GET', '/istorconfig'),
        ('GET', '/isystems'),
        ('GET', '/itrapdest'),
        ('GET', '/lldp_agents'),
        ('GET', '/lldp_neighbors'),
        ('GET', '/loads'),
        ('GET', '/networks'),
        ('GET', '/remotelogging'),
        ('GET', '/sdn_controller'),
        ('GET', '/servicegroup'),
        ('GET', '/servicenodes'),
        ('GET', '/service_parameter'),
        ('GET', '/services'),
        ('GET', '/storage_backend'),
        ('GET', '/storage_backend/usage'),
        ('GET', '/storage_ceph'),
        ('GET', '/storage_lvm'),
        # ('GET', '/tpmconfig'),
        ('GET', '/upgrade'),
        ('GET', '/')
    ]
)
def test_good_authentication(sysinv_rest, operation, resource):
    if operation == "GET":
        LOG.info("getting... {}".format(resource))
        rest_test_helper.get(sysinv_rest, resource=resource)
