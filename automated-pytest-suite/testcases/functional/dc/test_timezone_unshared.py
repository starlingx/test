#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import time
import random

from pytest import fixture, mark

from utils.tis_log import LOG
from consts.auth import Tenant
from consts.stx import TIMEZONES
from consts.proj_vars import ProjVar
from keywords import system_helper, dc_helper, host_helper


TIMEZONES = TIMEZONES[:-1]      # exclude UTC
TIMESTAMP_PATTERN = r'\d{4}-\d{2}-\d{2}[T| ]\d{2}:\d{2}:\d{2}'
DEFAULT_ZONE = 'UTC'


@fixture(scope='module', autouse=True)
def prev_check(request, check_central_alarms_module):

    LOG.fixture_step("(module) Ensure both central and subcloud are configured with {} timezone"
                     .format(DEFAULT_ZONE))
    subcloud = ProjVar.get_var('PRIMARY_SUBCLOUD')
    central_auth = Tenant.get('admin_platform', dc_region='RegionOne')
    sub_auth = Tenant.get('admin_platform', dc_region=subcloud)
    system_helper.modify_timezone(timezone=DEFAULT_ZONE, auth_info=central_auth)
    code = system_helper.modify_timezone(timezone=DEFAULT_ZONE, auth_info=sub_auth)[0]
    if code == 0:
        # allow sometime for change to apply
        time.sleep(30)

    prev_central_time = system_helper.get_host_values(host="controller-0", fields='created_at',
                                                      auth_info=central_auth)[0]
    prev_sub_time = system_helper.get_host_values(host="controller-0", fields='created_at',
                                                  auth_info=sub_auth)[0]
    LOG.fixture_step("prev_time: {}.".format(prev_central_time))
    central_zone, sub_zone = __select_two_timezones(current_zone=DEFAULT_ZONE)

    def _revert():
        LOG.fixture_step("Revert timezone to {} and ensure host created timestamp also reverted"
                         .format(DEFAULT_ZONE))
        system_helper.modify_timezone(timezone=DEFAULT_ZONE, auth_info=central_auth)
        system_helper.modify_timezone(timezone=DEFAULT_ZONE, auth_info=sub_auth)
        wait_for_timestamp_update(auth_info=central_auth, expt_time=prev_central_time)
        wait_for_timestamp_update(auth_info=sub_auth, expt_time=prev_sub_time)
    request.addfinalizer(_revert)

    return prev_central_time, prev_sub_time, central_zone, sub_zone, central_auth, sub_auth, \
           subcloud


def __select_two_timezones(current_zone=None):
    if not current_zone:
        current_zone = system_helper.get_timezone()

    zones = list(TIMEZONES)
    if current_zone in zones:
        zones.remove(current_zone)

    selected_zones = random.sample(zones, 2)
    LOG.info("Timezone selected to test: {}".format(selected_zones))
    return selected_zones


def wait_for_timestamp_update(auth_info, prev_timestamp=None, expt_time=None):
    timeout = time.time() + 60
    while time.time() < timeout:
        post_timestamp = system_helper.get_host_values(host='controller-0', fields='created_at',
                                                       auth_info=auth_info)[0]
        if prev_timestamp and prev_timestamp != post_timestamp:
            if prev_timestamp != post_timestamp:
                return post_timestamp
        elif expt_time:
            if post_timestamp == expt_time:
                return post_timestamp

        time.sleep(5)
    else:
        LOG.info("Timestamp for fm event did not change")
        return None


def test_dc_modify_timezone(prev_check):
    """
    Test timezone modify on system controller and subcloud. Ensure timezone change is not
    propagated.
    Setups:
        - Ensure both central and subcloud regions are configured with UTC
        - Get the timestamps for host created_at before timezone modify

    Test Steps
        - Change the timezone in central region and wait until the change is applied
        - Change the timezone to a different zone in subcloud and wait until the change is applied
        - Verify host created_at timestamp updated according to the local timezone for the region
        - Swact on subcloud and ensure timezone and host created_at timestamp persists locally
        - Swact central controller and ensure timezone and host created_at timestamp persists
          in central and subcloud

    Teardown
        - Change timezone to UTC in both central and subcloud regions
        - Ensure host created_at timestamp is reverted to original

    """
    prev_central_time, prev_sub_time, central_zone, sub_zone, central_auth, subcloud_auth, \
        subcloud = prev_check

    LOG.tc_step("Modify timezone to {} in central region".format(central_zone))
    system_helper.modify_timezone(timezone=central_zone, auth_info=central_auth)

    LOG.tc_step("Waiting for timestamp for host created_at to update in central region")
    post_central_time = wait_for_timestamp_update(prev_timestamp=prev_central_time,
                                                  auth_info=central_auth)
    assert post_central_time != prev_central_time, \
        "host created_at timestamp did not update after timezone changed " \
        "to {} in central region".format(central_zone)

    LOG.tc_step("Modify timezone to {} in {}".format(sub_zone, subcloud))
    system_helper.modify_timezone(timezone=sub_zone, auth_info=subcloud_auth)

    LOG.tc_step("Waiting for timestamp for same host created_at to update in {}".format(subcloud))
    post_sub_time = wait_for_timestamp_update(prev_timestamp=prev_sub_time,
                                              auth_info=subcloud_auth)
    assert post_sub_time != prev_sub_time, \
        "host created_at timestamp did not update after timezone changed to {} " \
        "in {}".format(sub_zone, subcloud)
    assert post_sub_time != post_central_time, \
        "Host created_at timestamp is the same on central and {} when configured with different " \
        "timezones".format(subcloud)

    LOG.tc_step("Ensure host created_at timestamp does not change after subcloud sync audit")
    dc_helper.wait_for_sync_audit(subclouds=subcloud, fail_ok=True, timeout=660)
    post_sync_sub_time = system_helper.get_host_values(host='controller-0', fields='created_at',
                                                       auth_info=subcloud_auth)[0]
    assert post_sub_time == post_sync_sub_time, \
        "Host created_at timestamp changed after sync audit on {}".format(subcloud)

    if not system_helper.is_aio_simplex():
        LOG.tc_step("Swact in {} region and verify timezone persists locally".format(subcloud))
        host_helper.swact_host(auth_info=subcloud_auth)
        post_swact_sub_zone = system_helper.get_timezone(auth_info=subcloud_auth)
        assert post_swact_sub_zone == sub_zone

        post_swact_sub_time = system_helper.get_host_values(host='controller-0',
                                                            fields='created_at',
                                                            auth_info=subcloud_auth)[0]
        assert post_swact_sub_time == post_sub_time

    if system_helper.get_standby_controller_name(auth_info=central_auth):
        LOG.tc_step("Swact in central region, and ensure timezone persists locally in central"
                    " and subcloud")
        host_helper.swact_host(auth_info=central_auth)

        # Verify central timezone persists
        post_swact_central_zone = system_helper.get_timezone(auth_info=central_auth)
        assert post_swact_central_zone == central_zone
        post_swact_central_time = system_helper.get_host_values(host='controller-0',
                                                                fields='created_at',
                                                                auth_info=central_auth)[0]
        assert post_swact_central_time == post_central_time

        # Verify subcloud timezone persists
        post_central_swact_sub_zone = system_helper.get_timezone(auth_info=subcloud_auth)
        assert post_central_swact_sub_zone == sub_zone
        post_central_swact_sub_time = system_helper.get_host_values(host='controller-0',
                                                                    fields='created_at',
                                                                    auth_info=subcloud_auth)[0]
        assert post_central_swact_sub_time == post_sub_time
