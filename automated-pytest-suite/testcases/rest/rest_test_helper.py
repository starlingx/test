#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import skip

from utils.tis_log import LOG


def get(rest_client, resource, auth=True):
    """
    Test GET of <resource> with valid authentication.

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
    message = "Using requests GET {} with proper authentication"
    LOG.info(message.format(resource))

    status_code, text = rest_client.get(resource=resource, auth=auth)
    message = "Retrieved: status_code: {} message: {}"
    LOG.debug(message.format(status_code, text))

    if status_code == 404:
        skip("Unsupported resource in this configuration.")
    else:
        LOG.info("Determine if expected status_code of 200 is received")
        message = "Expected status_code of 200 - received {} and message {}"
        assert status_code == 200, message.format(status_code, text)
