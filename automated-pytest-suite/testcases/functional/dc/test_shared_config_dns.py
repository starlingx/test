#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from pytest import fixture, skip, mark

from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient
from consts.proj_vars import ProjVar
from consts.auth import Tenant
from keywords import dc_helper, system_helper, host_helper


@fixture(scope='module')
def subclouds_to_test(request):

    LOG.info("Gather DNS config and subcloud management info")
    sc_auth = Tenant.get('admin_platform', dc_region='SystemController')
    dns_servers = system_helper.get_dns_servers(auth_info=sc_auth)

    subcloud = ProjVar.get_var('PRIMARY_SUBCLOUD')

    def revert():
        LOG.fixture_step("Manage {} if unmanaged".format(subcloud))
        dc_helper.manage_subcloud(subcloud)

        LOG.fixture_step("Revert DNS config if changed")
        system_helper.set_dns_servers(nameservers=dns_servers, auth_info=sc_auth)
    request.addfinalizer(revert)

    managed_subclouds = dc_helper.get_subclouds(mgmt='managed', avail='online')
    if subcloud in managed_subclouds:
        managed_subclouds.remove(subcloud)

    ssh_map = ControllerClient.get_active_controllers_map()
    managed_subclouds = [subcloud for subcloud in managed_subclouds if subcloud in ssh_map]

    return subcloud, managed_subclouds


def compose_new_dns_servers(scenario, prev_dns_servers):
    dns_servers = list(prev_dns_servers)
    unreachable_dns_server_ip = "8.4.4.4"

    if scenario == 'add_unreachable_server':
        dns_servers.append(unreachable_dns_server_ip)
    elif scenario == 'unreachable_server':
        dns_servers = [unreachable_dns_server_ip]
    else:
        if len(dns_servers) < 2:
            skip('Less than two DNS servers configured.')

        if scenario == 'change_order':
            dns_servers.append(dns_servers.pop(0))
        elif scenario == 'remove_one_server':
            dns_servers.append(dns_servers.pop(0))
            dns_servers.pop()
        else:
            raise ValueError("Unknown scenario: {}".format(scenario))

    return dns_servers


@fixture()
def ensure_synced(subclouds_to_test, check_central_alarms):
    primary_subcloud, managed_subclouds = subclouds_to_test

    LOG.fixture_step(
        "Ensure {} is managed and DNS config is valid and synced".format(primary_subcloud))
    subcloud_auth = Tenant.get('admin_platform', dc_region=primary_subcloud)
    subcloud_dns = system_helper.get_dns_servers(con_ssh=None, auth_info=subcloud_auth)
    sc_dns = system_helper.get_dns_servers(con_ssh=None,
                                           auth_info=Tenant.get('admin_platform',
                                                                dc_region='SystemController'))

    if subcloud_dns != sc_dns:
        dc_helper.manage_subcloud(subcloud=primary_subcloud, check_first=True)
        dc_helper.wait_for_subcloud_dns_config(subcloud=primary_subcloud, expected_dns=sc_dns)
        verify_dns_on_central_and_subcloud(primary_subcloud)

    return primary_subcloud, managed_subclouds, sc_dns


@mark.parametrize('scenario', (
    'add_unreachable_server',
    'change_order',
    'remove_one_server',
))
def test_dc_dns_modify(ensure_synced, scenario):
    """
    Update DNS servers on central region and check it is propagated to subclouds
    Args:
        ensure_synced: test fixture
        scenario: DNS change scenario

    Setups:
        - Ensure primary subcloud is managed and DNS config is valid and synced

    Test Steps:
        - Un-manage primary subcloud
        - Configure DNS servers on central region to new value based on given scenario
        - Wait for new DNS config to sync over to managed online subclouds
        - Ensure DNS config is not updated on unmanaged primary subcloud
        - Re-manage primary subcloud and ensure DNS config syncs over
        - Verify nslookup works in Central Region and primary subcloud

    Teardown:
        - Reset DNS servers to original value (module)

    """
    primary_subcloud, managed_subclouds, prev_dns_servers = ensure_synced
    new_dns_servers = compose_new_dns_servers(scenario=scenario, prev_dns_servers=prev_dns_servers)

    LOG.tc_step("Unmanage {}".format(primary_subcloud))
    dc_helper.unmanage_subcloud(subcloud=primary_subcloud, check_first=True)

    LOG.tc_step("Reconfigure DNS servers on central region from {} to {}".
                format(prev_dns_servers, new_dns_servers))
    system_helper.set_dns_servers(new_dns_servers,
                                  auth_info=Tenant.get('admin_platform',
                                                       dc_region='SystemController'))

    LOG.tc_step("Wait for new DNS config to sync over to managed online subclouds")
    for managed_sub in managed_subclouds:
        dc_helper.wait_for_subcloud_dns_config(subcloud=managed_sub, expected_dns=new_dns_servers)

    LOG.tc_step("Ensure DNS config is not updated on unmanaged subcloud: {}".
                format(primary_subcloud))
    code = dc_helper.wait_for_subcloud_dns_config(subcloud=primary_subcloud,
                                                  expected_dns=new_dns_servers,
                                                  timeout=60, fail_ok=True)[0]
    assert 1 == code, "Actual return code: {}".format(code)

    LOG.tc_step('Re-manage {} and ensure DNS config syncs over'.format(primary_subcloud))
    dc_helper.manage_subcloud(subcloud=primary_subcloud, check_first=False)
    dc_helper.wait_for_subcloud_dns_config(subcloud=primary_subcloud, expected_dns=new_dns_servers)

    LOG.tc_step('Verify nslookup works in Central Region and {}'.format(primary_subcloud))
    verify_dns_on_central_and_subcloud(primary_subcloud)


def test_dc_dns_override_local_change(ensure_synced):
    """
    Verify DNS modification on subcloud will be overridden by central region config
    Args:
        ensure_synced: test fixture

    Setups:
        - Ensure primary subcloud is managed and DNS config is valid and synced

    Test Steps:
        - Un-manage primary subcloud
        - Configure DNS servers on primary subcloud to a unreachable ip address (8.4.4.4)
        - Wait for sync log for any managed subcloud with best effort
        - Ensure DNS config is not updated on unmanaged primary subcloud
        - Verify nslookup passes on central region and fails on primary subcloud
        - Re-manage primary subcloud and ensure DNS config syncs over
        - Verify nslookup in Central Region and primary subcloud are working as expected

    Teardown:
        - Manage primary subcloud if not managed (module)
        - Reset DNS servers to original value on central region (module)

    """
    primary_subcloud, managed_subclouds, sc_dns = ensure_synced
    new_dns_servers = compose_new_dns_servers(scenario='unreachable_server',
                                              prev_dns_servers=sc_dns)

    LOG.tc_step("Unmanage {}".format(primary_subcloud))
    dc_helper.unmanage_subcloud(subcloud=primary_subcloud, check_first=True)

    LOG.tc_step("Reconfigure DNS on {} from {} to {}".format(
        primary_subcloud, sc_dns, new_dns_servers))
    system_helper.set_dns_servers(new_dns_servers, auth_info=Tenant.get('admin_platform',
                                                                        dc_region=primary_subcloud))

    managed_cloud = managed_subclouds[0] if managed_subclouds else ''
    LOG.tc_step("Wait for sync update log for managed subcloud {} with best effort".format(
        managed_cloud))
    dc_helper.wait_for_sync_audit(subclouds=managed_cloud, fail_ok=True, timeout=660)

    LOG.tc_step("Ensure DNS config is not updated on unmanaged subcloud: {}".format(
        primary_subcloud))
    code = dc_helper.wait_for_subcloud_dns_config(subcloud=primary_subcloud, expected_dns=sc_dns,
                                                  fail_ok=True, timeout=60)[0]
    assert 1 == code, "Actual return code: {}".format(code)

    LOG.tc_step("Verify nslookup fails on {}".format(primary_subcloud))
    central_res, local_res = verify_dns_on_central_and_subcloud(primary_subcloud, fail_ok=True,
                                                                sc_dns=sc_dns)
    assert 0 == central_res, "nslookup failed on central region"
    assert 1 == local_res, "nslookup succeeded on {} with unreachable DNS servers configured".\
        format(primary_subcloud)

    central_auth = Tenant.get('admin_platform', dc_region='RegionOne')
    if system_helper.get_standby_controller_name(auth_info=central_auth):
        LOG.tc_step("Swact in central region")
        host_helper.swact_host(auth_info=central_auth)

    LOG.tc_step('Re-manage {} and ensure local DNS config is overridden by central config'.
                format(primary_subcloud))
    dc_helper.manage_subcloud(subcloud=primary_subcloud, check_first=False)
    dc_helper.wait_for_subcloud_dns_config(subcloud=primary_subcloud, expected_dns=sc_dns)

    LOG.tc_step('Verify nslookup works in Central Region and {}'.format(primary_subcloud))
    verify_dns_on_central_and_subcloud(primary_subcloud, sc_dns=sc_dns)


def verify_dns_on_central_and_subcloud(primary_subcloud, fail_ok=False, sc_dns=None):
    res = []
    for region in ('RegionOne', primary_subcloud):
        # take snapshot
        orig_dns_servers = system_helper.get_dns_servers(auth_info=Tenant.get('admin_platform',
                                                                              dc_region=region))
        if not sc_dns or set(sc_dns) <= set(orig_dns_servers):
            LOG.info("Modify dns server to public dns")
            system_helper.set_dns_servers(nameservers=['8.8.8.8'],
                                          auth_info=Tenant.get('admin_platform',
                                                               dc_region=region))
        LOG.info("Check dns on {}".format(region))
        con_ssh = ControllerClient.get_active_controller(name=region)
        code, out = con_ssh.exec_cmd('nslookup -timeout=1 www.google.com', fail_ok=fail_ok,
                                     expect_timeout=30)
        res.append(code)
        # revert
        system_helper.set_dns_servers(nameservers=orig_dns_servers,
                                      auth_info=Tenant.get('admin_platform',
                                                           dc_region=region))
    return res
