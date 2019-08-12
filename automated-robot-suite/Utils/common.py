"""Provides Useful functions for Robot Framework"""

from __future__ import print_function

import configparser
import datetime
import errno
import os

from robot.api import TestData


class Suite(object):
    """Implement a series of suite attributes

    To define properties of a suite recognized by robot-framework.

    """

    def __init__(self, name, main_suite_path):
        self.name = name
        self.main_suite = TestData(source=main_suite_path)
        self.path = self.__get_suite_path(self.main_suite)
        try:
            self.data = TestData(source=self.path)
        except TypeError as err:
            print('ERROR: Suite {0} not found'.format(self.name))
            raise err

    def __get_suite_path(self, main_suite):
        """Return path of an specific test suite

           Args:
               main_suite = main suite test Data
           Returns:
               found_path = path of the suite found

        """

        if main_suite.name == self.name:
            return main_suite.source
        for child in main_suite.children:
            found_path = self.__get_suite_path(child)
            if found_path:
                return found_path


def get_config():
    """Read configuration file defined on execution directory

       Returns:
           config = Instance with configuration values parsed
                    from specified file

    """

    config = configparser.ConfigParser()
    config.read('stx.config')
    return config


def check_results_dir(suite_dir):
    """Check if results directory already exist, if not, create it

       Args:
           suite_dir = Path to the main suite
       Returns:
           resdir = Directory where results will be stored

    """

    results_dir = os.path.join(suite_dir, 'Results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    return results_dir


def create_output_dir(res_dir, suite_name):
    """Create directory under results to store the execution results

       Args:
           res_dir = Results dir where the results will be stored
           suite_name = Name of the suite under execution
       Returns:
           out_dir = Path to the dir created with the results
    """
    start_time = datetime.datetime.now()
    frmt = '%Y%m%d%H%M%S'
    out_dir = '{}/{}_{}'.format(res_dir, start_time.strftime(frmt), suite_name)
    os.makedirs(out_dir)

    return out_dir


def link_latest_run(suite_dir, out_dir):
    """Create a symlink to point to the latest execution results

       Args:
           suite_dir = Path to the main suite on the execution dir
           out_dir = Output dir where the most recent execution results
                     are stored

       Return:
           latest_run = Path of created file with a symlink

    """
    latest_run = os.path.join(suite_dir, 'latest-results')

    try:
        os.symlink(out_dir, latest_run)
    except OSError as err:
        if err.errno == errno.EEXIST:
            os.remove(latest_run)
            os.symlink(out_dir, latest_run)
        else:
            raise err

    return latest_run


def list_suites(suite, tree_format):
    """Print in a readable format the list of suites and test cases

       Args:
           suite = Specific suite data
           tree_format = format to be displayed on stdout

    """

    print('[S] {}{}'.format(tree_format, suite.name))
    if suite.testcase_table.tests:
        tree_format += '.....'
        for test in suite.testcase_table:
            print('(T) {}{}'.format(tree_format, test.name))
    else:
        tree_format += '....|'
    for child in suite.children:
        list_suites(child, tree_format)
