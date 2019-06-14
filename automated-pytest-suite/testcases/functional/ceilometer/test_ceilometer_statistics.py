#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time
import random
from datetime import datetime, timedelta
from pytest import mark, skip

from utils.tis_log import LOG

from consts.stx import GuestImages
from consts.auth import Tenant
from keywords import common, ceilometer_helper, network_helper, \
    glance_helper, system_helper, gnocchi_helper


def _wait_for_measurements(meter, resource_type, extra_query, start_time,
                           overlap=None, timeout=1860,
                           check_interval=60):
    end_time = time.time() + timeout

    while time.time() < end_time:
        values = gnocchi_helper.get_aggregated_measures(
            metrics=meter, resource_type=resource_type, start=start_time,
            overlap=overlap, extra_query=extra_query)[1]
        if values:
            return values

        time.sleep(check_interval)


@mark.cpe_sanity
@mark.sanity
@mark.sx_nightly
@mark.parametrize('meter', [
    'image.size'
])
def test_measurements_for_metric(meter):
    """
    Validate statistics for one meter

    """
    LOG.tc_step('Get ceilometer statistics table for image.size meter')

    now = datetime.utcnow()
    start = (now - timedelta(minutes=10))
    start = start.strftime("%Y-%m-%dT%H:%M:%S")
    image_name = GuestImages.DEFAULT['guest']
    resource_type = 'image'
    extra_query = "name='{}'".format(image_name)
    overlap = None

    code, output = gnocchi_helper.get_aggregated_measures(
        metrics=meter, resource_type=resource_type, start=start,
        extra_query=extra_query, fail_ok=True)
    if code > 0:
        if "Metrics can't being aggregated" in output:
            # there was another glance image that has the same
            # string in its name
            overlap = '0'
        else:
            assert False, output

    values = output
    if code == 0 and values:
        assert len(values) <= 4, "Incorrect count for {} {} metric via " \
                                 "'openstack metric measures aggregation'". \
            format(image_name, meter)
    else:
        values = _wait_for_measurements(meter=meter,
                                        resource_type=resource_type,
                                        extra_query=extra_query,
                                        start_time=start, overlap=overlap)
        assert values, "No measurements for image.size for 25+ minutes"

    LOG.tc_step('Check that values are larger than zero')
    for val in values:
        assert 0 <= float(val), "{} {} value in metric measurements " \
                                "table is less than zero".format(
            image_name, meter)


def check_event_in_tenant_or_admin(resource_id, event_type):
    for auth_ in (None, Tenant.get('admin')):
        traits = ceilometer_helper.get_events(event_type=event_type,
                                              header='traits:value',
                                              auth_info=auth_)
        for trait in traits:
            if resource_id in trait:
                LOG.info("Resource found in ceilometer events using "
                         "auth: {}".format(auth_))
                break
        else:
            continue
        break
    else:
        assert False, "{} event for resource {} was not found under admin or " \
                      "tenant".format(event_type, resource_id)
