#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark

from utils import cli
from utils.tis_log import LOG


@mark.sx_sanity
def test_add_host_simplex_negative(simplex_only):
    """
    Test add second controller is rejected on simplex system
    Args:
        simplex_only: skip if non-sx system detected

    Test Steps:
        - On simplex system, check 'system host-add -n controller-1' is rejected

    """
    LOG.tc_step("Check adding second controller is rejected on simplex system")
    code, out = cli.system('host-add', '-n controller-1', fail_ok=True)

    assert 1 == code, "Unexpected exitcode for 'system host-add " \
                      "controller-1': {}".format(code)
    assert 'Adding a host on a simplex system is not allowed' in out, \
        "Unexpected error message: {}".format(out)
