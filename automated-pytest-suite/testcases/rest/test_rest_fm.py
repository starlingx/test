#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture, mark
from utils.tis_log import LOG
from utils.rest import Rest

from testcases.rest import rest_test_helper


@fixture(scope='module')
def fm_rest():
    r = Rest('fm', platform=True)
    return r


@mark.parametrize('resource', (
    '/alarms',
    '/event_suppression',
    '/invalid_resource'
))
def test_rest_fm_get(resource, fm_rest):
    LOG.tc_step("Get fm resource {}".format(resource))
    rest_test_helper.get(rest_client=fm_rest, resource=resource)
