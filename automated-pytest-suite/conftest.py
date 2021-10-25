#
# Copyright (c) 2019, 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import logging
import os
from time import strftime, gmtime
# import threading    # Used for formatting logger


import pytest  # Don't remove. Used in eval

import setups
from consts.proj_vars import ProjVar
from utils.tis_log import LOG
from utils import parse_log

tc_start_time = None
tc_end_time = None
has_fail = False
repeat_count = -1
stress_count = -1
count = -1
no_teardown = False
tracebacks = []
region = None
test_count = 0
console_log = True

################################
# Process and log test results #
################################


class MakeReport:
    nodeid = None
    instances = {}

    def __init__(self, item):
        MakeReport.nodeid = item.nodeid
        self.test_pass = None
        self.test_results = {}
        MakeReport.instances[item.nodeid] = self

    def update_results(self, call, report):
        if report.failed:
            global has_fail
            has_fail = True
            msg = "***Failure at test {}: {}".format(call.when, call.excinfo)
            print(msg)
            LOG.debug(msg + "\n***Details: {}".format(report.longrepr))
            tracebacks.append(str(report.longrepr))
            self.test_results[call.when] = ['Failed', call.excinfo]
        elif report.skipped:
            sep = 'Skipped: '
            skipreason_list = str(call.excinfo).split(sep=sep)[1:]
            skipreason_str = sep.join(skipreason_list)
            self.test_results[call.when] = ['Skipped', skipreason_str]
        elif report.passed:
            self.test_results[call.when] = ['Passed', '']

    def get_results(self):
        return self.test_results

    @classmethod
    def get_report(cls, item):
        if item.nodeid == cls.nodeid:
            return cls.instances[cls.nodeid]
        else:
            return cls(item)


class TestRes:
    PASSNUM = 0
    FAILNUM = 0
    SKIPNUM = 0
    TOTALNUM = 0


def _write_results(res_in_tests, test_name):
    global tc_start_time
    with open(ProjVar.get_var("TCLIST_PATH"), mode='a', encoding='utf8') as f:
        f.write('\n{}\t{}\t{}'.format(res_in_tests, tc_start_time, test_name))
    global test_count
    test_count += 1
    # reset tc_start and end time for next test case
    tc_start_time = None


def pytest_runtest_makereport(item, call, __multicall__):
    report = __multicall__.execute()
    my_rep = MakeReport.get_report(item)
    my_rep.update_results(call, report)

    test_name = item.nodeid.replace('::()::',
                                    '::')  # .replace('testcases/', '')
    res_in_tests = ''
    res = my_rep.get_results()

    # Write final result to test_results.log
    if report.when == 'teardown':
        res_in_log = 'Test Passed'
        fail_at = []
        for key, val in res.items():
            if val[0] == 'Failed':
                fail_at.append('test ' + key)
            elif val[0] == 'Skipped':
                res_in_log = 'Test Skipped\nReason: {}'.format(val[1])
                res_in_tests = 'SKIP'
                break
        if fail_at:
            fail_at = ', '.join(fail_at)
            res_in_log = 'Test Failed at {}'.format(fail_at)

        # Log test result
        testcase_log(msg=res_in_log, nodeid=test_name, log_type='tc_res')

        if 'Test Passed' in res_in_log:
            res_in_tests = 'PASS'
        elif 'Test Failed' in res_in_log:
            res_in_tests = 'FAIL'
            if ProjVar.get_var('PING_FAILURE'):
                setups.add_ping_failure(test_name=test_name)

        if not res_in_tests:
            res_in_tests = 'UNKNOWN'

        # count testcases by status
        TestRes.TOTALNUM += 1
        if res_in_tests == 'PASS':
            TestRes.PASSNUM += 1
        elif res_in_tests == 'FAIL':
            TestRes.FAILNUM += 1
        elif res_in_tests == 'SKIP':
            TestRes.SKIPNUM += 1

        _write_results(res_in_tests=res_in_tests, test_name=test_name)

    if repeat_count > 0:
        for key, val in res.items():
            if val[0] == 'Failed':
                global tc_end_time
                tc_end_time = strftime("%Y%m%d %H:%M:%S", gmtime())
                _write_results(res_in_tests='FAIL', test_name=test_name)
                TestRes.FAILNUM += 1
                if ProjVar.get_var('PING_FAILURE'):
                    setups.add_ping_failure(test_name=test_name)

                try:
                    parse_log.parse_test_steps(ProjVar.get_var('LOG_DIR'))
                except Exception as e:
                    LOG.warning(
                        "Unable to parse test steps. \nDetails: {}".format(
                            e.__str__()))

                pytest.exit(
                    "Skip rest of the iterations upon stress test failure")

    if no_teardown and report.when == 'call':
        for key, val in res.items():
            if val[0] == 'Skipped':
                break
        else:
            pytest.exit("No teardown and skip rest of the tests if any")

    return report


def pytest_runtest_setup(item):
    global tc_start_time
    # tc_start_time = setups.get_tis_timestamp(con_ssh)
    tc_start_time = strftime("%Y%m%d %H:%M:%S", gmtime())
    print('')
    message = "Setup started:"
    testcase_log(message, item.nodeid, log_type='tc_setup')
    # set test name for ping vm failure
    test_name = 'test_{}'.format(
        item.nodeid.rsplit('::test_', 1)[-1].replace('/', '_'))
    ProjVar.set_var(TEST_NAME=test_name)
    ProjVar.set_var(PING_FAILURE=False)


def pytest_runtest_call(item):
    separator = \
        '++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++'
    message = "Test steps started:"
    testcase_log(message, item.nodeid, separator=separator, log_type='tc_start')


def pytest_runtest_teardown(item):
    print('')
    message = 'Teardown started:'
    testcase_log(message, item.nodeid, log_type='tc_teardown')


def testcase_log(msg, nodeid, separator=None, log_type=None):
    if separator is None:
        separator = '-----------'

    print_msg = separator + '\n' + msg
    logging_msg = '\n{}{} {}'.format(separator, msg, nodeid)
    if console_log:
        print(print_msg)
    if log_type == 'tc_res':
        global tc_end_time
        tc_end_time = strftime("%Y%m%d %H:%M:%S", gmtime())
        LOG.tc_result(msg=msg, tc_name=nodeid)
    elif log_type == 'tc_start':
        LOG.tc_func_start(nodeid)
    elif log_type == 'tc_setup':
        LOG.tc_setup_start(nodeid)
    elif log_type == 'tc_teardown':
        LOG.tc_teardown_start(nodeid)
    else:
        LOG.debug(logging_msg)


########################
# Command line options #
########################
@pytest.mark.tryfirst
def pytest_configure(config):
    config.addinivalue_line("markers",
                            "features(feature_name1, feature_name2, "
                            "...): mark impacted feature(s) for a test case.")
    config.addinivalue_line("markers",
                            "priorities(, cpe_sanity, p2, ...): mark "
                            "priorities for a test case.")
    config.addinivalue_line("markers",
                            "known_issue(LP-xxxx): mark known issue with "
                            "LP ID or description if no LP needed.")

    if config.getoption('help'):
        return

    # Common reporting params
    collect_all = config.getoption('collectall')
    always_collect = config.getoption('alwayscollect')
    session_log_dir = config.getoption('sessiondir')
    resultlog = config.getoption('resultlog')

    # Test case params on installed system
    testcase_config = config.getoption('testcase_config')
    lab_arg = config.getoption('lab')
    natbox_arg = config.getoption('natbox')
    tenant_arg = config.getoption('tenant')
    horizon_visible = config.getoption('horizon_visible')
    is_vbox = config.getoption('is_vbox')

    global repeat_count
    repeat_count = config.getoption('repeat')
    global stress_count
    stress_count = config.getoption('stress')
    global count
    if repeat_count > 0:
        count = repeat_count
    elif stress_count > 0:
        count = stress_count

    global no_teardown
    no_teardown = config.getoption('noteardown')
    if repeat_count > 0 or no_teardown:
        ProjVar.set_var(NO_TEARDOWN=True)

    collect_netinfo = config.getoption('netinfo')

    # Determine lab value.
    lab = natbox = None
    if lab_arg:
        lab = setups.get_lab_dict(lab_arg)
    if natbox_arg:
        natbox = setups.get_natbox_dict(natbox_arg)

    lab, natbox = setups.setup_testcase_config(testcase_config, lab=lab,
                                               natbox=natbox)
    tenant = tenant_arg.upper() if tenant_arg else 'TENANT1'

    # Log collection params
    collect_all = True if collect_all else False
    always_collect = True if always_collect else False

    # If floating ip cannot be reached, whether to try to ping/ssh
    # controller-0 unit IP, etc.
    if collect_netinfo:
        ProjVar.set_var(COLLECT_SYS_NET_INFO=True)

    horizon_visible = True if horizon_visible else False

    if session_log_dir:
        log_dir = session_log_dir
    else:
        # compute directory for all logs based on resultlog arg, lab,
        # and timestamp on local machine
        resultlog = resultlog if resultlog else os.path.expanduser("~")
        if '/AUTOMATION_LOGS' in resultlog:
            resultlog = resultlog.split(sep='/AUTOMATION_LOGS')[0]
        resultlog = os.path.join(resultlog, 'AUTOMATION_LOGS')
        lab_name = lab['short_name']
        time_stamp = strftime('%Y%m%d%H%M')
        log_dir = '{}/{}/{}'.format(resultlog, lab_name, time_stamp)
    os.makedirs(log_dir, exist_ok=True)

    # set global constants, which will be used for the entire test session, etc
    ProjVar.init_vars(lab=lab, natbox=natbox, logdir=log_dir, tenant=tenant,
                      collect_all=collect_all,
                      always_collect=always_collect,
                      horizon_visible=horizon_visible)

    if lab.get('central_region'):
        default_subloud = config.getoption('subcloud')
        subcloud_list = config.getoption('subcloud_list')
        if subcloud_list:
            if default_subloud not in subcloud_list:
                msg = ("default subcloud --subcloud=%s not in --subcloud_list=%s" %
                       (default_subloud, subcloud_list))
                LOG.error(msg)
                pytest.exit(msg)

        ProjVar.set_var(IS_DC=True, PRIMARY_SUBCLOUD=default_subloud, SUBCLOUD_LIST=subcloud_list)

    if is_vbox:
        ProjVar.set_var(IS_VBOX=True)

    config_logger(log_dir, console=console_log)

    # set resultlog save location
    config.option.resultlog = ProjVar.get_var("PYTESTLOG_PATH")

    # Repeat test params
    file_or_dir = config.getoption('file_or_dir')
    origin_file_dir = list(file_or_dir)
    if count > 1:
        print("Repeat following tests {} times: {}".format(count, file_or_dir))
        del file_or_dir[:]
        for f_or_d in origin_file_dir:
            for i in range(count):
                file_or_dir.append(f_or_d)


def pytest_addoption(parser):
    testconf_help = "Absolute path for testcase config file. Template can be " \
                    "found at automated-pytest-suite/stx-test_template.conf"
    lab_help = "STX system to connect to. Valid value: 1) short_name or name " \
               "of an existing dict entry in consts.Labs; Or 2) OAM floating " \
               "ip of the STX system under test"
    tenant_help = "Default tenant to use when unspecified. Valid values: " \
                  "tenant1, tenant2, or admin"
    natbox_help = "NatBox IP or name. If automated tests are executed from " \
                  "NatBox, --natbox=localhost can be used. " \
                  "If username/password are required to SSH to NatBox, " \
                  "please specify them in test config file."
    vbox_help = "Specify if StarlingX system is installed in virtual " \
                "environment."
    collect_all_help = "Run collect all on STX system at the end of test " \
                       "session if any test fails."
    logdir_help = "Directory to store test session logs. If this is " \
                  "specified, then --resultlog will be ignored."
    stress_help = "Number of iterations to run specified testcase(s). Abort " \
                  "rest of the test session on first failure"
    count_help = "Repeat tests x times - NO stop on failure"
    horizon_visible_help = "Display horizon on screen"
    no_console_log = 'Print minimal console logs'
    region_help = "Multi-region parameter. Use when connected region is " \
                  "different than region to test. " \
                  "e.g., creating vm on RegionTwo from RegionOne"
    subcloud_help = "Default subcloud used for automated test when boot vm, " \
                    "etc. 'subcloud1' if unspecified."
    subcloud_list_help = "Specifies subclouds for DC labs, e.g. --subcloud_list=subcloud1," \
                         "subcloud2. If unspecified the lab's subclouds from lab.py will " \
                         "be used."

    # Test session options on installed and configured STX system:
    parser.addoption('--testcase-config', action='store',
                     metavar='testcase_config', default=None,
                     help=testconf_help)
    parser.addoption('--lab', action='store', metavar='lab', default=None,
                     help=lab_help)
    parser.addoption('--tenant', action='store', metavar='tenantname',
                     default=None, help=tenant_help)
    parser.addoption('--natbox', action='store', metavar='natbox', default=None,
                     help=natbox_help)
    parser.addoption('--vm', '--vbox', action='store_true', dest='is_vbox',
                     help=vbox_help)

    # Multi-region or distributed cloud options
    parser.addoption('--region', action='store', metavar='region',
                     default=None, help=region_help)
    parser.addoption('--subcloud', action='store', metavar='subcloud',
                     default='subcloud1', help=subcloud_help)
    parser.addoption("--subcloud_list", action="store", default=None,
                     help=subcloud_list_help)

    # Debugging/Log collection options:
    parser.addoption('--sessiondir', '--session_dir', '--session-dir',
                     action='store', dest='sessiondir',
                     metavar='sessiondir', default=None, help=logdir_help)
    parser.addoption('--collectall', '--collect_all', '--collect-all',
                     dest='collectall', action='store_true',
                     help=collect_all_help)
    parser.addoption('--alwayscollect', '--always-collect', '--always_collect',
                     dest='alwayscollect',
                     action='store_true', help=collect_all_help)
    parser.addoption('--repeat', action='store', metavar='repeat', type=int,
                     default=-1, help=stress_help)
    parser.addoption('--stress', metavar='stress', action='store', type=int,
                     default=-1, help=count_help)
    parser.addoption('--no-teardown', '--no_teardown', '--noteardown',
                     dest='noteardown', action='store_true')
    parser.addoption('--netinfo', '--net-info', dest='netinfo',
                     action='store_true',
                     help="Collect system networking info if scp keyfile fails")
    parser.addoption('--horizon-visible', '--horizon_visible',
                     action='store_true', dest='horizon_visible',
                     help=horizon_visible_help)
    parser.addoption('--noconsolelog', '--noconsole', '--no-console-log',
                     '--no_console_log', '--no-console',
                     '--no_console', action='store_true', dest='noconsolelog',
                     help=no_console_log)


def config_logger(log_dir, console=True):
    # logger for log saved in file
    file_name = log_dir + '/TIS_AUTOMATION.log'
    logging.Formatter.converter = gmtime
    log_format = '[%(asctime)s] %(lineno)-5d%(levelname)-5s %(threadName)-8s ' \
                 '%(module)s.%(funcName)-8s:: %(message)s'
    tis_formatter = logging.Formatter(log_format)
    LOG.setLevel(logging.NOTSET)

    tmp_path = os.path.join(os.path.expanduser('~'), '.tmp_log')
    # clear the tmp log with best effort so it wont keep growing
    try:
        os.remove(tmp_path)
    except:
        pass
    logging.basicConfig(level=logging.NOTSET, format=log_format,
                        filename=tmp_path, filemode='w')

    # file handler:
    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(tis_formatter)
    file_handler.setLevel(logging.DEBUG)
    LOG.addHandler(file_handler)

    # logger for stream output
    console_level = logging.INFO if console else logging.CRITICAL
    stream_hdler = logging.StreamHandler()
    stream_hdler.setFormatter(tis_formatter)
    stream_hdler.setLevel(console_level)
    LOG.addHandler(stream_hdler)

    print("LOG DIR: {}".format(log_dir))


def pytest_unconfigure(config):
    # collect all if needed
    if config.getoption('help'):
        return

    try:
        natbox_ssh = ProjVar.get_var('NATBOX_SSH')
        natbox_ssh.close()
    except:
        pass

    version_and_patch = ''
    try:
        version_and_patch = setups.get_version_and_patch_info()
    except Exception as e:
        LOG.debug(e)
        pass
    log_dir = ProjVar.get_var('LOG_DIR')
    if not log_dir:
        try:
            from utils.clients.ssh import ControllerClient
            ssh_list = ControllerClient.get_active_controllers(fail_ok=True)
            for con_ssh_ in ssh_list:
                con_ssh_.close()
        except:
            pass
        return

    log_dir = ProjVar.get_var('LOG_DIR')
    if not log_dir:
        try:
            from utils.clients.ssh import ControllerClient
            ssh_list = ControllerClient.get_active_controllers(fail_ok=True)
            for con_ssh_ in ssh_list:
                con_ssh_.close()
        except:
            pass
        return

    try:
        tc_res_path = log_dir + '/test_results.log'
        build_info = ProjVar.get_var('BUILD_INFO')
        build_id = build_info.get('BUILD_ID', '')
        build_job = build_info.get('JOB', '')
        build_server = build_info.get('BUILD_HOST', '')
        system_config = ProjVar.get_var('SYS_TYPE')
        session_str = ''
        total_exec = TestRes.PASSNUM + TestRes.FAILNUM
        # pass_rate = fail_rate = '0'
        if total_exec > 0:
            pass_rate = "{}%".format(
                round(TestRes.PASSNUM * 100 / total_exec, 2))
            fail_rate = "{}%".format(
                round(TestRes.FAILNUM * 100 / total_exec, 2))
            with open(tc_res_path, mode='a', encoding='utf8') as f:
                # Append general info to result log
                f.write('\n\nLab: {}\n'
                        'Build ID: {}\n'
                        'Job: {}\n'
                        'Build Server: {}\n'
                        'System Type: {}\n'
                        'Automation LOGs DIR: {}\n'
                        'Ends at: {}\n'
                        '{}'  # test session id and tag
                        '{}'.format(ProjVar.get_var('LAB_NAME'), build_id,
                                    build_job, build_server, system_config,
                                    ProjVar.get_var('LOG_DIR'), tc_end_time,
                                    session_str, version_and_patch))
                # Add result summary to beginning of the file
                f.write(
                    '\nSummary:\nPassed: {} ({})\nFailed: {} ({})\nTotal '
                    'Executed: {}\n'.
                    format(TestRes.PASSNUM, pass_rate, TestRes.FAILNUM,
                           fail_rate, total_exec))
                if TestRes.SKIPNUM > 0:
                    f.write('------------\nSkipped: {}'.format(TestRes.SKIPNUM))

            LOG.info("Test Results saved to: {}".format(tc_res_path))
            with open(tc_res_path, 'r', encoding='utf8') as fin:
                print(fin.read())
    except Exception as e:
        LOG.exception(
            "Failed to add session summary to test_results.py. "
            "\nDetails: {}".format(e.__str__()))
    # Below needs con_ssh to be initialized
    try:
        from utils.clients.ssh import ControllerClient
        con_ssh = ControllerClient.get_active_controller()
    except:
        LOG.warning("No con_ssh found")
        return

    try:
        parse_log.parse_test_steps(ProjVar.get_var('LOG_DIR'))
    except Exception as e:
        LOG.warning(
            "Unable to parse test steps. \nDetails: {}".format(e.__str__()))

    if test_count > 0 and (ProjVar.get_var('ALWAYS_COLLECT') or (
            has_fail and ProjVar.get_var('COLLECT_ALL'))):
        # Collect tis logs if collect all required upon test(s) failure
        # Failure on collect all would not change the result of the last test
        # case.
        try:
            setups.collect_tis_logs(con_ssh)
        except Exception as e:
            LOG.warning("'collect all' failed. {}".format(e.__str__()))

    ssh_list = ControllerClient.get_active_controllers(fail_ok=True,
                                                       current_thread_only=True)
    for con_ssh_ in ssh_list:
        try:
            con_ssh_.close()
        except:
            pass


def pytest_collection_modifyitems(items):
    # print("Collection modify")
    move_to_last = []
    absolute_last = []

    for item in items:
        # re-order tests:
        trylast_marker = item.get_closest_marker('trylast')
        abslast_marker = item.get_closest_marker('abslast')

        if abslast_marker:
            absolute_last.append(item)
        elif trylast_marker:
            move_to_last.append(item)

        priority_marker = item.get_closest_marker('priorities')
        if priority_marker is not None:
            priorities = priority_marker.args
            for priority in priorities:
                item.add_marker(eval("pytest.mark.{}".format(priority)))

        feature_marker = item.get_closest_marker('features')
        if feature_marker is not None:
            features = feature_marker.args
            for feature in features:
                item.add_marker(eval("pytest.mark.{}".format(feature)))

        # known issue marker
        known_issue_mark = item.get_closest_marker('known_issue')
        if known_issue_mark is not None:
            issue = known_issue_mark.args[0]
            msg = "{} has a workaround due to {}".format(item.nodeid, issue)
            print(msg)
            LOG.debug(msg=msg)
            item.add_marker(eval("pytest.mark.known_issue"))

        # add dc maker to all tests start with test_dc_xxx
        dc_maker = item.get_marker('dc')
        if not dc_maker and 'test_dc_' in item.nodeid:
            item.add_marker(pytest.mark.dc)

    # add trylast tests to the end
    for item in move_to_last:
        items.remove(item)
        items.append(item)

    for i in absolute_last:
        items.remove(i)
        items.append(i)


def pytest_generate_tests(metafunc):
    # Prefix 'remote_cli' to test names so they are reported as a different
    # testcase
    if ProjVar.get_var('REMOTE_CLI'):
        metafunc.parametrize('prefix_remote_cli', ['remote_cli'])


##############################################################
# Manipulating fixture orders based on following pytest rules
# session > module > class > function
# autouse > non-autouse
# alphabetic after full-filling above criteria
#
# Orders we want on fixtures of same scope:
# check_alarms > delete_resources > config_host
#############################################################

@pytest.fixture(scope='session')
def check_alarms():
    LOG.debug("Empty check alarms")
    return


@pytest.fixture(scope='session')
def config_host_class():
    LOG.debug("Empty config host class")
    return


@pytest.fixture(scope='session')
def config_host_module():
    LOG.debug("Empty config host module")


@pytest.fixture(autouse=True)
def a1_fixture(check_alarms):
    return


@pytest.fixture(scope='module', autouse=True)
def c1_fixture(config_host_module):
    return


@pytest.fixture(scope='class', autouse=True)
def c2_fixture(config_host_class):
    return


@pytest.fixture(scope='session', autouse=True)
def prefix_remote_cli():
    return


def __params_gen(index):
    return 'iter{}'.format(index)


@pytest.fixture(scope='session')
def global_setup():
    os.makedirs(ProjVar.get_var('TEMP_DIR'), exist_ok=True)
    os.makedirs(ProjVar.get_var('PING_FAILURE_DIR'), exist_ok=True)
    os.makedirs(ProjVar.get_var('GUEST_LOGS_DIR'), exist_ok=True)

    if region:
        setups.set_region(region=region)


#####################################
# End of fixture order manipulation #
#####################################


def pytest_sessionfinish():
    if ProjVar.get_var('TELNET_THREADS'):
        threads, end_event = ProjVar.get_var('TELNET_THREADS')
        end_event.set()
        for thread in threads:
            thread.join()

    if repeat_count > 0 and has_fail:
        # _thread.interrupt_main()
        print('Printing traceback: \n' + '\n'.join(tracebacks))
        pytest.exit("\n========== Test failed - "
                    "Test session aborted without teardown to leave the "
                    "system in state ==========")

    if no_teardown:
        pytest.exit(
            "\n========== Test session stopped without teardown after first "
            "test executed ==========")
