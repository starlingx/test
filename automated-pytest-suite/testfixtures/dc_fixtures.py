#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from pytest import fixture

from consts.auth import Tenant
from keywords import system_helper, check_helper
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG


@fixture(scope='function')
def check_central_alarms(request):
    """
    Check system alarms before and after test case.

    Args:
        request: caller of this fixture. i.e., test func.
    """
    __verify_central_alarms(request=request, scope='function')


@fixture(scope='module')
def check_central_alarms_module(request):
    """
    Check system alarms before and after test session.

    Args:
        request: caller of this fixture. i.e., test func.
    """
    __verify_central_alarms(request=request, scope='module')


def __verify_central_alarms(request, scope):
    region = 'RegionOne'
    auth_info = Tenant.get('admin_platform', dc_region=region)
    con_ssh = ControllerClient.get_active_controller(name=region)
    LOG.fixture_step("({}) Gathering fm alarms in central region before test {} begins.".format(
        scope, scope))
    before_alarms = system_helper.get_alarms(fields=('Alarm ID', 'Entity ID', 'Severity'),
                                             auth_info=auth_info, con_ssh=con_ssh)

    def verify_alarms():
        LOG.fixture_step(
            "({}) Verifying system alarms in central region after test {} ended.".format(
                scope, scope))
        check_helper.check_alarms(before_alarms=before_alarms, auth_info=auth_info,
                                  con_ssh=con_ssh)
        LOG.info("({}) fm alarms verified in central region.".format(scope))
    request.addfinalizer(verify_alarms)
