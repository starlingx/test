#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import re
from os import path

write_command_pattern = r"^(?!.*((" \
                        r"system|nova|cinder|fm|openstack|ceilometer|heat" \
                        r"|glance|gnocchi).*(show|list)|echo " \
                        r"\$\?|whoami|hostname|exit|stat|ls|Send '')).*"
test_steps_pattern = r"^=+ (Setup|Test|Teardown) Step \d+"


def _get_failed_test_names(log_dir):
    """
        Parses test_results for names of failed tests

        Args:
            log_dir: directory the log is located

        Returns (list):
            [test_name, test_name, ...]

    """
    test_res_path = "{}/test_results.log".format(log_dir)
    if not path.exists(test_res_path):
        return []

    with open(test_res_path, 'r') as file:
        failed_tests = []

        for line in file:
            if line.startswith("FAIL"):
                test_name = 'test_' + line.split('::test_', 1)[1].replace('\n',
                                                                          '')
                failed_tests.append(test_name)

        return failed_tests


def get_tracebacks_from_pytestlog(log_dir, traceback_lines=10,
                                  search_forward=False):
    """
        Parses pytestlog for the traceback of any failures up to a specified
        line count

        Args:
            log_dir (str): directory the log is located
            traceback_lines (int): Number of lines to record before the point
            of failure
            search_forward (bool): whether to search forward from last '> '
            or search backward from first '> '

        Returns (dict):
            {test_name:traceback, test_name:traceback, ...}

    """
    failed_tests = _get_failed_test_names(log_dir)
    traceback_dict = {}
    if not failed_tests:
        return traceback_dict

    new_test_pattern = r'(E|F|.|S) \S'
    current_failure = None
    next_failure = failed_tests.pop(0)
    traceback_for_test = []
    with open(path.join(log_dir, 'pytestlog.log'), 'r') as file:
        for line in file:
            if current_failure is not None:
                if re.match(new_test_pattern, line):
                    traceback = parse_traceback(traceback_for_test,
                                                traceback_lines=traceback_lines,
                                                search_forward=search_forward)
                    traceback_dict[current_failure] = traceback
                    current_failure = None
                    try:
                        next_failure = failed_tests.pop(0)
                    except IndexError:
                        break
                else:
                    traceback_for_test.append(line[1:].strip())
                    continue

            if next_failure in line:
                current_failure = next_failure
        else:
            # Meaning last test is a failed test
            traceback = parse_traceback(traceback_for_test,
                                        traceback_lines=traceback_lines,
                                        search_forward=search_forward)
            traceback_dict[current_failure] = traceback

    return traceback_dict


def parse_traceback(traceback, traceback_lines=10, search_forward=False):
    """
        Parses traceback for a failure up to a specified line count

        Args:
            traceback (str|list): traceback from log file / running test
            traceback_lines (int): Number of lines to record
            search_forward (bool): whether to search forward from last '> '
            or search backward from first '> '

        Returns (str): traceback trimmed to specified line count

    """
    collected_lines = []

    if isinstance(traceback, str):
        traceback = traceback.splitlines()
    else:
        traceback = list(traceback)

    if search_forward:
        traceback.reverse()
    for line in traceback:
        collected_lines.append(line.strip())
        if line.startswith('>  '):
            collected_lines = collected_lines[-traceback_lines:]
            if search_forward:
                collected_lines.reverse()
            collected_lines.insert(0, '---FAILURE TRACEBACK---')
            break

    return '\n'.join(collected_lines)


def parse_test_steps(log_dir, failures_only=True):
    """
        Parses TIS_AUTOMATION for test steps

        Args:
            log_dir (str):          Directory the log is located
            failures_only (bool):   True  - Parses only failed tests
                                    False - Parses all tests

    """
    failed_tests = []
    if failures_only:
        failed_tests = _get_failed_test_names(log_dir)
    test_found = False
    test_steps_length = 0
    test_steps = []

    if failures_only and not failed_tests:
        return

    with open("{}/TIS_AUTOMATION.log".format(log_dir), 'r') as file, \
            open("{}/test_steps.log".format(log_dir), 'w') as log:
        for line in file:

            if test_steps_length >= 500:
                log.write(''.join(test_steps))
                test_steps_length = 0
                test_steps = []

            if not test_found:
                if "Setup started for:" in line:
                    if failures_only:
                        split_line = line.split('::test_', 1)
                        if len(split_line) == 2:
                            test_name = 'test_' + split_line[1].replace('\n',
                                                                        '')
                            if test_name in failed_tests:
                                test_found = True
                                test_steps.append(line)
                                test_steps_length += 1
                    else:
                        test_found = True
                        test_steps.append(line)
                        test_steps_length += 1
                continue

            if ":: Send " in line:
                if re.search(write_command_pattern, line):
                    test_steps.append(line)
                    test_steps_length += 1
                continue

            if " started for:" in line:
                test_steps.append("\n" + line)
                test_steps_length += 1
                continue

            if "***Failure at" in line:
                test_steps.append("\n" + line)
                test_steps_length += 1
                continue

            if re.search(test_steps_pattern, line):
                test_steps.append(line)
                test_steps_length += 1
                continue

            if "Test Result for:" in line:
                test_found = False
                test_steps.append("\n\n\n\n\n\n")
                test_steps_length += 6

        log.write(''.join(test_steps))
