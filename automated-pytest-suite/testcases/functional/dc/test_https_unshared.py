#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from pytest import fixture

from consts.auth import Tenant
from consts.proj_vars import ProjVar
from keywords import security_helper, keystone_helper, dc_helper, container_helper, host_helper, \
    system_helper, common
from utils import cli
from utils.tis_log import LOG


@fixture(scope='module')
def revert_https(request):
    """
    Fixture for get the current http mode of the system, and if the test fails,
    leave the system in the same mode than before
    """
    central_auth = Tenant.get('admin_platform', dc_region='RegionOne')
    sub_auth = Tenant.get('admin_platform')
    use_dnsname = (bool(common.get_dnsname()) and
                   bool(common.get_dnsname(region=ProjVar.get_var('PRIMARY_SUBCLOUD'))))

    origin_https_sub = keystone_helper.is_https_enabled(auth_info=sub_auth)
    origin_https_central = keystone_helper.is_https_enabled(auth_info=central_auth)

    def _revert():
        LOG.fixture_step("Revert central https config to {}.".format(origin_https_central))
        security_helper.modify_https(enable_https=origin_https_central, auth_info=central_auth)

        LOG.fixture_step("Revert subcloud https config to {}.".format(origin_https_sub))
        security_helper.modify_https(enable_https=origin_https_central, auth_info=sub_auth)

        LOG.fixture_step("Verify cli's on subcloud and central region.".format(origin_https_sub))
        verify_cli(sub_auth, central_auth)

    request.addfinalizer(_revert)

    return origin_https_sub, origin_https_central, central_auth, sub_auth, use_dnsname


def test_dc_modify_https(revert_https):
    """
    Test enable/disable https

    Test Steps:
        - Ensure central region and subcloud admin endpoint are https
        - Ensure central region https to be different than subcloud
        - Wait for subcloud sync audit and ensure subcloud https is not changed
        - Verify cli's in subcloud and central region
        - Modify https on central and subcloud
        - Verify cli's in subcloud and central region
        - swact central and subcloud
        - Ensure central region and subcloud admin endpoint are https

    Teardown:
        - Revert https config on central and subcloud

    """
    origin_https_sub, origin_https_central, central_auth, sub_auth, use_dnsname = revert_https
    subcloud = ProjVar.get_var('PRIMARY_SUBCLOUD')

    LOG.tc_step(
        "Before testing, Ensure central region and subcloud admin internal endpoint are https")
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=central_auth), \
        "Central region admin internal endpoint is not https"
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=sub_auth), \
        "Subcloud admin internal endpoint is not https"

    new_https_sub = not origin_https_sub
    new_https_central = not origin_https_central

    LOG.tc_step("Ensure central region https to be different than {}".format(subcloud))
    security_helper.modify_https(enable_https=new_https_sub, auth_info=central_auth)

    LOG.tc_step('Check public endpoints accessibility for central region')
    security_helper.check_services_access(region='RegionOne', auth_info=central_auth,
                                          use_dnsname=use_dnsname)
    LOG.tc_step('Check platform horizon accessibility')
    security_helper.check_platform_horizon_access(use_dnsname=use_dnsname)

    LOG.tc_step("Wait for subcloud sync audit with best effort and ensure {} https is not "
                "changed".format(subcloud))
    dc_helper.wait_for_sync_audit(subclouds=subcloud, fail_ok=True, timeout=660)
    assert origin_https_sub == keystone_helper.is_https_enabled(auth_info=sub_auth), \
        "HTTPS config changed in subcloud"

    LOG.tc_step("Verify cli's in {} and central region".format(subcloud))
    verify_cli(sub_auth, central_auth)

    if new_https_central != new_https_sub:
        LOG.tc_step("Set central region https to {}".format(new_https_central))
        security_helper.modify_https(enable_https=new_https_central, auth_info=central_auth)
        LOG.tc_step("Ensure central region and subcloud admin internal endpoint are still https")
        assert keystone_helper.is_https_enabled(interface='admin', auth_info=central_auth), \
            "Central region admin internal endpoint is not https"
        assert keystone_helper.is_https_enabled(interface='admin', auth_info=sub_auth), \
            "Subcloud admin internal endpoint is not https"
        LOG.tc_step('Check public endpoints accessibility for central region')
        security_helper.check_services_access(region='RegionOne', auth_info=central_auth,
                                              use_dnsname=use_dnsname)
        LOG.tc_step('Check platform horizon accessibility')
        security_helper.check_platform_horizon_access(use_dnsname=use_dnsname)

    LOG.tc_step("Set {} https to {}".format(subcloud, new_https_sub))
    security_helper.modify_https(enable_https=new_https_sub, auth_info=sub_auth)
    LOG.tc_step('Check public endpoints accessibility for {} region'.format(subcloud))
    security_helper.check_services_access(region=subcloud, auth_info=sub_auth,
                                          use_dnsname=use_dnsname)

    LOG.tc_step("Ensure central region and subcloud admin internal endpoint are still https")
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=central_auth), \
        "Central region admin internal endpoint is not https"
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=sub_auth), \
        "Subcloud admin internal endpoint is not https"

    LOG.tc_step("Verify cli's in {} and central region after https modify on "
                "subcloud".format(subcloud))
    verify_cli(sub_auth, central_auth)

    LOG.tc_step("Swact on central region")
    host_helper.swact_host(auth_info=central_auth)

    LOG.tc_step(
        "Verify cli's in {} and central region after central region swact" .format(subcloud))
    verify_cli(sub_auth, central_auth)

    if not system_helper.is_aio_simplex(auth_info=sub_auth):
        LOG.tc_step("Swact on subcloud {}".format(subcloud))
        host_helper.swact_host(auth_info=sub_auth)
        LOG.tc_step("Verify cli's in {} and central region after subcloud swact".format(subcloud))
        verify_cli(sub_auth, central_auth)

    LOG.tc_step("Ensure after swact, central region and subcloud admin internal endpoint are https")
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=central_auth), \
        "Central region admin internal endpoint is not https"
    assert keystone_helper.is_https_enabled(interface='admin', auth_info=sub_auth), \
        "Subcloud admin internal endpoint is not https"


def verify_cli(sub_auth=None, central_auth=None):
    auths = [central_auth, sub_auth]
    auths = [auth for auth in auths if auth]

    for auth in auths:
        cli.system('host-list', fail_ok=False, auth_info=auth)
        cli.fm('alarm-list', fail_ok=False, auth_info=auth)
        if container_helper.is_stx_openstack_deployed(applied_only=True, auth_info=auth):
            cli.openstack('server list --a', fail_ok=False, auth_info=auth)
            cli.openstack('image list', fail_ok=False, auth_info=auth)
            cli.openstack('volume list --a', fail_ok=False, auth_info=auth)
            cli.openstack('user list', fail_ok=False, auth_info=auth)
            cli.openstack('router list', fail_ok=False, auth_info=auth)

    if sub_auth and container_helper.is_stx_openstack_deployed(applied_only=True,
                                                               auth_info=sub_auth):
        cli.openstack('stack list', fail_ok=False, auth_info=sub_auth)
        cli.openstack('alarm list', fail_ok=False, auth_info=sub_auth)
        cli.openstack('metric status', fail_ok=False, auth_info=sub_auth)
