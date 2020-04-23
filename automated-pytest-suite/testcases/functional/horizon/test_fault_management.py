#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time

from pytest import fixture, mark

from utils.horizon.regions import messages
from utils.horizon.pages.admin.fault_management import eventssuppressionpage

from utils.tis_log import LOG
from consts import horizon


@fixture(scope='function')
def events_suppression_pg(admin_home_pg, request):
    LOG.fixture_step('Go to Admin > Fault Management > Events Suppression')
    events_suppression_pg = eventssuppressionpage.EventsSuppressionPage(admin_home_pg.driver)
    events_suppression_pg.go_to_target_page()

    def teardown():
        LOG.fixture_step('Back to Events Suppression page')
        events_suppression_pg.go_to_target_page()

    request.addfinalizer(teardown)
    return events_suppression_pg


def test_suppress_event(events_suppression_pg):
    """
    Test Steps:
        - Suppress event
        - Check for success message
        - Unsuppress event
        - Check for success message
    """
    event_id = '100.101'
    LOG.tc_step('Suppress event {}.'.format(event_id))
    events_suppression_pg.suppress_event(event_id)
    end_time = time.time()
    while time.time() < end_time:
        if events_suppression_pg.find_message_and_dismiss(messages.SUCCESS):
            break
        elif events_suppression_pg.find_message_and_dismiss(messages.ERROR):
            assert "Failed to suppress event: {}".format(event_id)

    LOG.tc_step('Unsuppress event {}.'.format(event_id))
    events_suppression_pg.unsuppress_event(event_id)
    end_time = time.time()
    while time.time() < end_time:
        if events_suppression_pg.find_message_and_dismiss(messages.SUCCESS):
            break
        elif events_suppression_pg.find_message_and_dismiss(messages.ERROR):
            assert "Failed to unsuppress event: {}".format(event_id)

    horizon.test_result = True
