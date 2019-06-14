#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import pytest

from utils.tis_log import LOG
from utils.rest import Rest
from keywords import system_helper
import string


@pytest.fixture(scope='module')
def sysinv_rest():
    r = Rest('sysinv', platform=True)
    return r


def test_GET_ihosts_host_id_shortUUID(sysinv_rest):
    """
    Test GET of <resource> with valid authentication and upper
         case UUID values.
         RFC 4122 covers the need for uppercase UUID values

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    path = "/ihosts/{}/addresses"
    r = sysinv_rest
    LOG.info(path)
    LOG.info(system_helper.get_hosts())
    for host in system_helper.get_hosts():
        uuid = system_helper.get_host_values(host, 'uuid')[0]
        LOG.info("host: {} uuid: {}".format(host, uuid))
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(path))

        short_uuid = uuid[:-1]
        status_code, text = r.get(resource=path.format(short_uuid),
                                  auth=True)
        message = "Retrieved: status_code: {} message: {}"
        LOG.info(message.format(status_code, text))
        LOG.tc_step("Determine if expected code of 400 is received")
        message = "Expected code of 400 - received {} and message {}"
        assert status_code == 400, message.format(status_code, text)


def test_GET_ihosts_host_id_invalidUUID(sysinv_rest):
    """
    Test GET of <resource> with valid authentication and upper
         case UUID values.
         RFC 4122 covers the need for uppercase UUID values

    Args:
        n/a

    Prerequisites: system is running
    Test Setups:
        n/a
    Test Steps:
        - Using requests GET <resource> with proper authentication
        - Determine if expected status_code of 200 is received
    Test Teardown:
        n/a
    """
    path = "/ihosts/{}/addresses"
    r = sysinv_rest
    LOG.info(path)
    LOG.info(system_helper.get_hosts())
    for host in system_helper.get_hosts():
        uuid = system_helper.get_host_values(host, 'uuid')[0]
        LOG.info("host: {} uuid: {}".format(host, uuid))
        message = "Using requests GET {} with proper authentication"
        LOG.tc_step(message.format(path))

        # shift a->g, b->h, etc - all to generate invalid uuid
        shifted_uuid = \
            ''.join(map(lambda x: chr((ord(x) - ord('a') + 6) % 26 + ord(
                'a')) if x in string.ascii_lowercase else x, uuid.lower()))
        status_code, text = r.get(resource=path.format(shifted_uuid),
                                  auth=True)
        message = "Retrieved: status_code: {} message: {}"
        LOG.info(message.format(status_code, text))
        LOG.tc_step("Determine if expected code of 400 is received")
        message = "Expected code of 400 - received {} and message {}"
        assert status_code == 400, message.format(status_code, text)
