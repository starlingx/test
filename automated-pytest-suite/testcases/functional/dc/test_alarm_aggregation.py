#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import time

from pytest import fixture

from utils import cli
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient
from utils import table_parser
from consts.proj_vars import ProjVar
from consts.auth import Tenant
from consts.stx import SubcloudStatus, EventLogID
from consts.timeout import DCTimeout
from keywords import dc_helper, system_helper

# Set the level of stress you want to test
ALARMS_NO = 500


@fixture(scope="module")
def subcloud_to_test():
    check_alarm_summary_match_subcloud(ProjVar.get_var('PRIMARY_SUBCLOUD'))
    return ProjVar.get_var('PRIMARY_SUBCLOUD')


def check_alarm_summary_match_subcloud(subcloud, timeout=400):
    LOG.info("Ensure alarm summary on SystemController with subcloud {}".format(subcloud))
    subcloud_auth = Tenant.get('admin_platform', dc_region=subcloud)
    central_auth = Tenant.get('admin_platform', dc_region='RegionOne')

    severities = ["critical_alarms", "major_alarms", "minor_alarms", "warnings"]
    central_alarms = subcloud_alarms = None
    end_time = time.time() + timeout
    while time.time() < end_time:
        output_central = cli.dcmanager('alarm summary', auth_info=central_auth, fail_ok=False)[1]
        output_sub = cli.fm("alarm-summary", auth_info=subcloud_auth, fail_ok=False)[1]

        central_alarms = table_parser.get_multi_values(table_parser.table(output_central),
                                                       fields=severities, **{"NAME": subcloud})
        subcloud_alarms = table_parser.get_multi_values(table_parser.table(output_sub), severities)

        if central_alarms == subcloud_alarms:
            LOG.info("'dcmanager alarm summary' output for {} matches 'fm alarm-summary' on "
                     "{}".format(subcloud, subcloud))
            return

        time.sleep(30)

    assert central_alarms == subcloud_alarms, \
        "'dcmanager alarm summary did not match 'fm alarm-summary' on {} " \
        "within {}s".format(subcloud, timeout)


def alarm_summary_add_and_del(subcloud):
    try:
        # Test adding alarm on subcloud
        ssh_client = ControllerClient.get_active_controller(name=subcloud)
        LOG.info("Wait for alarm raised on subcloud {}".format(subcloud))
        system_helper.wait_for_alarm(alarm_id=EventLogID.PROVIDER_NETWORK_FAILURE,
                                     con_ssh=ssh_client)
        LOG.tc_step("Ensure alarm summary match nn Central with subcloud: {}".format(subcloud))
        check_alarm_summary_match_subcloud(subcloud)

        # Test clearing alarm on subcloud
        LOG.tc_step("Clear alarm on subcloud: {}".format(subcloud))
        ssh_client.exec_cmd('fmClientCli -D host=testhost-0', fail_ok=False)
        LOG.info("Wait for alarm clear on subcloud {}".format(subcloud))
        system_helper.wait_for_alarm_gone(alarm_id=EventLogID.PROVIDER_NETWORK_FAILURE,
                                          con_ssh=ssh_client)
        check_alarm_summary_match_subcloud(subcloud)
    finally:
        ssh_client = ControllerClient.get_active_controller(name=subcloud)
        LOG.info("Clear alarm on subcloud: {}".format(subcloud))
        ssh_client.exec_cmd('fmClientCli -D host=testhost-0')


def add_routes_to_subcloud(subcloud, subcloud_table, fail_ok=False):
    LOG.debug("Add routes back to subcloud: {}".format(subcloud))
    ssh_client = ControllerClient.get_active_controller(name=subcloud)
    for host_id in subcloud_table:
        comm_args = table_parser.get_multi_values(subcloud_table[host_id],
                                                  ["ifname", "network", "prefix", "gateway"])
        command = "host-route-add {} {} {} {} {}".format(host_id, comm_args[0][0],
                                                         comm_args[1][0], comm_args[2][0],
                                                         comm_args[3][0])
        code, output = cli.system("host-route-list {}".format(host_id))
        uuid_list = table_parser.get_values(table_parser.table(output), "uuid")
        if table_parser.get_values(subcloud_table[host_id], "uuid")[0] not in uuid_list:
            cli.system(command, ssh_client=ssh_client, fail_ok=fail_ok)


def test_dc_alarm_aggregation_managed(subcloud_to_test):
    """
    Test Alarm Aggregation on Distributed Cloud
    Args:
        subcloud_to_test (str): module fixture

    Setups:
        - Make sure there is consistency between alarm summary on
        Central Cloud and on subclouds

    Test Steps:
        - Raise an alarm at subcloud;
        - Ensure relative alarm raised on subcloud
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        - Clean alarm at subcloud
        - Ensure relative alarm cleared on subcloud
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
    """

    ssh_client = ControllerClient.get_active_controller(name=subcloud_to_test)
    LOG.tc_step("Raise alarm on subcloud: {}".format(subcloud_to_test))
    ssh_client.exec_cmd(
        "fmClientCli -c \"### ###300.005###clear###system.vm###host=testhost-0"
        "### ###critical### ###processing-error###cpu-cycles-limit-exceeded### ###"
        "True###True###'\"", fail_ok=False)

    alarm_summary_add_and_del(subcloud_to_test)


def test_dc_fault_scenario(subcloud_to_test):
    """
    Test Fault Scenario on Distributed Cloud
    Args:
        subcloud_to_test (str): module fixture

    Setup:
        - Make sure there is consistency between alarm summary on
        Central Cloud and on subclouds

    Test Steps:
        - Make subcloud offline (e. g. delete route)
        Step1:
        - Ensure suncloud shows offline
        Step2:
        - Raise alarm on subcloud
        - Ensure relative alarm raised on subcloud,
        - Ensure system alarm-summary on subcloud has changed
        - Ensure  dcmanager alarm summary on system controller has no change
        Step3:
        - Resume connectivity to subcloud (e. g. add route back)
        - Ensure suncloud shows online and in-sync
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        controller
        Step4:
        - Clean alarm on subcloud
        - Ensure relative alarm cleared on subcloud
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        controller
    """
    ssh_central = ControllerClient.get_active_controller(name="RegionOne")
    ssh_subcloud = ControllerClient.get_active_controller(name=subcloud_to_test)
    subcloud_table = {}
    try:
        code, output = cli.dcmanager("subcloud show {}".format(subcloud_to_test),
                                     ssh_client=ssh_central)
        gateway = table_parser.get_value_two_col_table(table_parser.table(output),
                                                       "management_gateway_ip")
        code, hosts_raw = cli.system("host-list", ssh_client=ssh_subcloud)
        hosts_id = table_parser.get_values(table_parser.table(hosts_raw), 'id')
        for host_id in hosts_id:
            code, route_raw = cli.system("host-route-list {}".format(host_id),
                                         ssh_client=ssh_subcloud)
            route_table = table_parser.filter_table(table_parser.table(route_raw),
                                                    **{'gateway': gateway})
            subcloud_table[host_id] = route_table

        LOG.tc_step("Delete route for subcloud: {} and wait for it to go offline.".format(
            subcloud_to_test))
        ssh_subcloud = ControllerClient.get_active_controller(name=subcloud_to_test)
        for host_id in subcloud_table:
            command = "host-route-delete {}".format(table_parser.get_values(
                subcloud_table[host_id], "uuid")[0])
            cli.system(command, ssh_client=ssh_subcloud)

        dc_helper.wait_for_subcloud_status(subcloud_to_test,
                                           avail=SubcloudStatus.AVAIL_OFFLINE,
                                           timeout=DCTimeout.SYNC, con_ssh=ssh_central)

        LOG.tc_step("Raise alarm on subcloud: {}".format(subcloud_to_test))
        ssh_subcloud = ControllerClient.get_active_controller(name=subcloud_to_test)
        code_sub_before, output_sub_before = cli.fm("alarm-summary", ssh_client=ssh_subcloud)
        code_central_before, output_central_before = cli.dcmanager('alarm summary')
        ssh_subcloud.exec_cmd(
            "fmClientCli -c \"### ###300.005###clear###system.vm###host="
            "testhost-0### ###critical### ###processing-error###cpu-cycles-limit-exceeded"
            "### ###True###True###'\"", fail_ok=False)
        LOG.info("Ensure relative alarm was raised at subcloud: {}".format(subcloud_to_test))
        system_helper.wait_for_alarm(alarm_id=EventLogID.PROVIDER_NETWORK_FAILURE,
                                     con_ssh=ssh_subcloud)
        code_sub_after, output_sub_after = cli.fm("alarm-summary", ssh_client=ssh_subcloud)
        code_central_after, output_central_after = cli.dcmanager('alarm summary')
        LOG.info("Ensure fm alarm summary on subcloud: {} has changed but dcmanager alarm"
                 "summary has not changed".format(subcloud_to_test))
        assert output_central_before == output_central_after and output_sub_before != \
            output_sub_after

        add_routes_to_subcloud(subcloud_to_test, subcloud_table)

        dc_helper.wait_for_subcloud_status(subcloud_to_test, avail=SubcloudStatus.AVAIL_ONLINE,
                                           sync=SubcloudStatus.SYNCED, timeout=DCTimeout.SYNC,
                                           con_ssh=ssh_central)
        alarm_summary_add_and_del(subcloud_to_test)

    finally:
        cli.dcmanager("subcloud show {}".format(subcloud_to_test),
                      ssh_client=ssh_central, fail_ok=True)
        add_routes_to_subcloud(subcloud_to_test, subcloud_table, fail_ok=True)
        LOG.info("Clear alarm on subcloud: {}".format(subcloud_to_test))
        ssh_subcloud.exec_cmd('fmClientCli -D host=testhost-0')
        check_alarm_summary_match_subcloud(subcloud=subcloud_to_test)


def test_dc_stress_alarm(subcloud_to_test):
    """
    Test Stress Scenario on Distributed Cloud
    Args:
        subcloud_to_test (str): module fixture

    Setup:
        - Make sure there is consistency between alarm summary on
        Central Cloud and on subclouds

    Test Steps:
        Step1:
        - Trigger large amount of alarms, quickly on one subcloud
        - ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        controller
        Step2:
        - Trigger large amount of alarms quickly for a long time on all subclouds
        - Each alarm summary updates once every 30 seconds until the event is over
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        controller
        Step3:
        - Clear all alarms
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        controller
    """
    ssh_client = ControllerClient.get_active_controller(name=subcloud_to_test)

    # Step 1
    LOG.tc_step("Trigger large amount of alarms, quickly on one subcloud")
    try:
        for i in range(1, ALARMS_NO + 1):
            ssh_client.exec_cmd(
                "fmClientCli -c \"### ###300.005###clear###system.vm###host="
                "testhost-{}### ###critical### ###processing-error###cpu-cycles-limit-exceeded"
                "### ###True###True###'\"".format(i), fail_ok=False)
    finally:
        for i in range(1, ALARMS_NO + 1):
            ssh_client.exec_cmd('fmClientCli -D host=testhost-{}'.format(i))

    check_alarm_summary_match_subcloud(subcloud_to_test)

    # Step 2
    ssh_client_list = {}
    for subcloud in dc_helper.get_subclouds(mgmt='managed'):
        ssh_client_list[subcloud] = ControllerClient.get_active_controller(name=subcloud_to_test)

    try:
        LOG.tc_step("Trigger large amount of alarms quickly for a long time on all subclouds")
        for subcloud in ssh_client_list:
            subcloud_ssh = ssh_client_list[subcloud]
            for i in range(1, ALARMS_NO + 1):
                subcloud_ssh.exec_cmd(
                    "fmClientCli -c \"### ###300.005###clear###"
                    "system.vm###host=testhost-{}### ###critical### ###processing-error###"
                    "cpu-cycles-limit-exceeded### ###True###True###'\"".format(i),
                    fail_ok=False)

        for subcloud in ssh_client_list:
            check_alarm_summary_match_subcloud(subcloud)
    finally:
        # Step 3
        LOG.tc_step("Clear all alarms on all subclouds")
        for subcloud in ssh_client_list:
            subcloud_ssh = ssh_client_list[subcloud]
            for i in range(1, ALARMS_NO + 1):
                subcloud_ssh.exec_cmd('fmClientCli -D host=testhost-{}'.format(i))

        for subcloud in ssh_client_list:
            check_alarm_summary_match_subcloud(subcloud)
