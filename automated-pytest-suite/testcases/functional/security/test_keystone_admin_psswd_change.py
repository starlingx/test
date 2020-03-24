#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import time
from pytest import mark, fixture, skip, param

from keywords import host_helper, system_helper, keystone_helper, security_helper
from utils.tis_log import LOG
from consts.auth import Tenant
from consts.reasons import SkipSysType


@fixture()
def _revert_admin_pw(request):
    prev_pswd = Tenant.get('admin')['password']

    def _revert():
        # revert password
        LOG.fixture_step("Reverting admin password to '{}'".format(prev_pswd))
        keystone_helper.set_user('admin', password=prev_pswd,
                                 auth_info=Tenant.get('admin_platform'))

        LOG.fixture_step("Sleep for 180 seconds after admin password change")
        time.sleep(180)
        assert prev_pswd == security_helper.get_admin_password_in_keyring()
    request.addfinalizer(_revert)


@fixture(scope='module')
def less_than_two_cons(no_openstack):
    return len(system_helper.get_controllers()) < 2


@mark.usefixtures('check_alarms')
@mark.parametrize(('scenario'), [
    # param('lock_standby_change_pswd', marks=mark.p1),
    param('change_pswd_swact', marks=mark.p1),
])
# disable the  test cases for now due to password change for admin is not ready yet
def test_admin_password(scenario, less_than_two_cons, _revert_admin_pw):
    """
    Test the admin password change

    Test Steps:
        - lock standby controller change password and unlock
        - change password and swact
        - check alarms

    """
    if 'swact' in scenario and less_than_two_cons:
        skip(SkipSysType.LESS_THAN_TWO_CONTROLLERS)

    host = system_helper.get_standby_controller_name()
    assert host, "No standby controller on system"

    if scenario == "lock_standby_change_pswd":
        # lock the standby
        LOG.tc_step("Attempting to lock {}".format(host))
        res, out = host_helper.lock_host(host=host)
        LOG.tc_step("Result of the lock was: {}".format(res))

    # change password
    prev_pswd = Tenant.get('admin')['password']
    post_pswd = '!{}9'.format(prev_pswd)

    LOG.tc_step('Changing admin password to {}'.format(post_pswd))
    keystone_helper.set_user('admin', password=post_pswd, auth_info=Tenant.get(
        'admin_platform'))

    # assert "Warning: 'admin' password changed. Please wait 5 minutes before Locking/Unlocking
    # the controllers" in output
    LOG.tc_step("Sleep for 180 seconds after admin password change")
    time.sleep(180)

    LOG.tc_step("Check admin password is updated in keyring")
    assert post_pswd == security_helper.get_admin_password_in_keyring()

    if scenario == "change_pswd_swact":
        LOG.tc_step("Swact active controller")
        host_helper.swact_host()
    else:
        LOG.tc_step("Unlock host {}".format(host))
        res = host_helper.unlock_host(host)
        LOG.info("Unlock hosts result: {}".format(res))

    LOG.tc_step("Check admin password is updated in keyring")
    assert post_pswd == security_helper.get_admin_password_in_keyring()
