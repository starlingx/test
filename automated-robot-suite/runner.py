#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Runner for StarlingX test suite"""

from __future__ import print_function

import argparse
import getpass
import os
from shutil import copy
from Config import config
import sys

import robot
import Utils.common as common
from Libraries.common import update_config_ini, get_controllers_ip

# Global variables
CURRENT_USER = getpass.getuser()
SUITE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SUITE = os.path.join(SUITE_DIR, 'Tests')
LOG_NAME = 'debug.log'

# Set PYHTHONPATH variable
os.environ["PYTHONPATH"] = SUITE_DIR


def update_general_config_file(configuration, config_type, env, config_file,
                               yaml_file):
    """Update general configuration file with selected options

    Args:
        - configuration: The configuration to be setup, the possible options
          are:
              1. for simplex configuration
              2. for duplex configuration
              3. for multinode controller storage configuration
              4. for multinode dedicated storage configuration
        - config_type: The type of configuration selected from the command
                       line
        - env: The environment selected from the command line
        - config_file: The stx-configuration.ini file to be setup in
                       the controller
    """
    config_path = os.path.join(SUITE_DIR, 'Config', 'config.ini')
    # Get Controller(s) IPs from the stx specific config file
    stx_config_path = os.path.join(SUITE_DIR, 'Config', config_file)
    if env == 'baremetal':
        lab_yaml = ('{}.yaml').format(config_type)
        lab_config = os.path.join(SUITE_DIR, 'baremetal', 'configs', lab_yaml)
    else:
        lab_config = os.path.join(SUITE_DIR, yaml_file)

    unit_ips = get_controllers_ip(env, stx_config_path, config_type,
                                  lab_config)
    # Update configuration info
    if env == 'baremetal':
        update_config_ini(config_ini=config_path, KERNEL_OPTION=configuration,
                          CONFIGURATION_TYPE=config_type, ENVIRONMENT=env,
                          CONFIGURATION_FILE=config_file,
                          IP_UNIT_0_ADDRESS=unit_ips['IP_UNIT_0_ADDRESS'],
                          IP_UNIT_1_ADDRESS=unit_ips['IP_UNIT_1_ADDRESS'],
                          OAM=unit_ips['OAM_IF'],
                          MGMT=unit_ips['MGMT_IF'],
                          ENV_YAML_FILE=yaml_file)
    else:
        update_config_ini(config_ini=config_path, KERNEL_OPTION=configuration,
                          CONFIGURATION_TYPE=config_type, ENVIRONMENT=env,
                          CONFIGURATION_FILE=config_file,
                          IP_UNIT_0_ADDRESS=unit_ips['IP_UNIT_0_ADDRESS'],
                          IP_UNIT_1_ADDRESS=unit_ips['IP_UNIT_1_ADDRESS'],
                          ENV_YAML_FILE=yaml_file)

    if ARGS.update:
        print('''Suite Updated !!!
Following values are now set on Config/config.ini file
-----
KERNEL_OPTION={}
CONFIGURATION_TYPE={}
ENVIRONMENT={}
CONFIGURATION_FILE={}
IP_UNIT_0_ADDRESS={}
IP_UNIT_1_ADDRESS={}
ENV_YAML_FILE={}'''.format(configuration, config_type, env, config_file,
                           unit_ips['IP_UNIT_0_ADDRESS'],
                           unit_ips['IP_UNIT_1_ADDRESS'],
                           yaml_file))
        if env == 'baremetal':
            print('''
OAM={}
MGMT={}'''.format(unit_ips['OAM_IF'], unit_ips['MGMT_IF']))


        # Only update configuration hence exit
        sys.exit(0)

def update_yaml_file(config_opt, env):
    """Overwrite the yaml file for specific yaml file used

    This function overwrite the current yaml file into environment folder
    for a specific configuration file from environment/configs.

    :param config_opt: the argument from the command line given by the user
    :param env: environemnt argument from the command line given by the user
    :return
        - conf_type: the type of configuration selected from the
        command line
        - conf_file: the configuration to be use during config controller
        command in the node
    """

    conf_type = ''
    conf_file = ''

    if config_opt == '1':
        conf_type = 'simplex'
        conf_file = 'stx-simplex.yml'
    elif config_opt == '2':
        conf_type = 'duplex'
        conf_file = 'stx-duplex.yml'
    elif config_opt == '3':
        conf_type = 'multinode_controller_storage'
        conf_file = 'stx-multinode.yml'
    elif config_opt == '4':
        conf_type = 'multinode_dedicated_storage'
        conf_file = 'stx-multinode.yml'

    # Update yaml file of selected environment
    if env == 'virtual':
        env_dir = 'Qemu'
        env_setup_file = 'qemu_setup.yaml'
    else:
        env_dir = 'baremetal'
        env_setup_file = 'baremetal_setup.yaml'

    origin = os.path.join(SUITE_DIR, '{}/configs/{}.yaml'
                          .format(env_dir, conf_type))
    destination = os.path.join(SUITE_DIR, '{}/{}'
                               .format(env_dir, env_setup_file))
    copy(origin, destination)


    return {'ctype': conf_type, 'cfile': conf_file,
            'eyaml': '{}/{}'.format(env_dir, env_setup_file,)}


def kernel_option(configuration):
    """Return the correct kernel option

    This function return the kernel option to install the correct
    configuration selected by the user

    :param configuration: the argument from the command line given by the user
    :return:
        - kernel_opt: which is the kernel option for boot the controller-0
    """

    kernel_opt = ''

    if configuration == '1' or configuration == '2':
        kernel_opt = '3'
    elif configuration == '3' or configuration == '4':
        kernel_opt = '1'

    return kernel_opt


def get_args():
    """Define and handle arguments with options to run the script

    Return:
        parser.parse_args(): list arguments as objects assigned
            as attributes of a namespace
    """

    description = 'Script used to run sxt-test-suite'
    parser = argparse.ArgumentParser(description=description)
    # optional args
    parser.add_argument(
        '--list-suites', dest='list_suite_name',
        nargs='?', const=os.path.basename(MAIN_SUITE),
        help=(
            'List the suite and sub-suites including test cases of the '
            'specified suite, if no value is given the entire suites tree '
            'is displayed.'))
    # groups args
    group = parser.add_argument_group(
        'Execution Suite', 'One of this arguments is mandatory - Suite(s) to '
                           'be run')
    group.add_argument('--run-all', dest='run_all',
                       action='store_true', help='Run all available suites')
    group.add_argument('--run-suite', dest='run_suite_name',
                       help='Run the specified suite')
    group_configuration = parser.add_argument_group(
        'Execution Environment and Configuration',
        'Environment and Configuration to be run in the host'
        '- This option is only required if `--run-suite` is equal to `Setup`')
    group_configuration.add_argument(
        '--environment', dest='environment', choices=['virtual', 'baremetal'],
        help=('The environment where the suite will run'))
    group_configuration.add_argument(
        '--configuration', dest='configuration', choices=['1', '2', '3', '4'],
        help=(
            '{}: will deploy configurations for the host. '
            '1=simplex, 2=duplex, 3=multinode-controller-storage, 4='
            'multinode-dedicated-storage')
        .format(__file__))
    group_configuration.add_argument(
        '--update-only', dest='update', action='store_true',
        help=('Update execution parameters on the suite.'))
    group_extras = parser.add_argument_group(
        'Execution Extras', 'Extra options to be used on the suite execution.')
    group_extras.add_argument(
        '--include', dest='tags',
        help=(
            'Executes only the test cases with specified tags.'
            'Tags and patterns can also be combined together with `AND`, `OR`,'
            'and `NOT` operators.'
            'Examples: --include foo --include bar* --include foo AND bar*'))
    group_extras.add_argument(
        '--test', dest='tests', nargs='+', default='*',
        help=(
            'Select test cases to run by name. '
            'Name is case and space insensitive. '
            'Test cases should be separated by a blank space, '
            'if the test case has spaces on the name send it beetwen "". '
            'Examples: --test "TEST 1" TEST_2 "Test 3"'))

    return parser.parse_args()

def list_suites_option(suite_to_list):
    """Display the suite tree including test cases

        Args:
            suite_to_list: name of the suite to display on stdout
    """

    # Get suite details
    suite = common.Suite(suite_to_list, MAIN_SUITE)
    print(
        '''
Suite is located at: {}
=== INFORMATION ====
[S] = Suite
(T) = Test Case
====================

=== SUITE TREE ====
    '''.format(suite.path))

    common.list_suites(suite.data, '')

def get_config_tag(configuration):
    """Associate to the configuration selected wit a tag

     Args:
         configuration: Configuration selected
     Return:
         tag: Tag ssociate to the configuration
    """

    tags_dict = {
        'simplex': 'Simplex',
        'duplex': 'Duplex',
        'multinode_controller_storage': 'MN-Local',
        'multinode_dedicated_storage': 'MN-External'
    }

    return tags_dict.get(configuration)

def get_iso_name():
    """Check real name of the ISO used on the deployment

     Return:
         real_name: ISO real name
    """

    name = config.get('general', 'STX_ISO_FILE')
    # Check if synlink was used instead of updating config file
    try:
        real_name = os.readlink('{}/{}'.format(SUITE_DIR, name))
    except OSError:
        real_name = name

    return real_name

def get_metadata():
    """Construct default metadata to be displayed on reports

     Return:
         metadata_list: List with names and values to be added as metadata
    """

    metadata_list = []
    system = ('System:{}'.format(config.get('general', 'CONFIGURATION_TYPE')))
    iso = ('ISO:{}'.format(get_iso_name()))
    metadata_list.extend([system, iso])

    return metadata_list

def run_suite_option(suite_name):
    """Run Specified Test Suite and creates the results structure

    Args:
    - suite_name: name of the suite that will be executed
    """

    # Get suite details
    suite = common.Suite(suite_name, MAIN_SUITE)
    # Create results directory if does not exist
    results_dir = common.check_results_dir(SUITE_DIR)
    # Create output directory to store execution results
    output_dir = common.create_output_dir(results_dir, suite.name)
    # Create a link pointing to the latest run
    common.link_latest_run(SUITE_DIR, output_dir)
    # Updating config.ini LOG_PATH variable with output_dir
    config_path = os.path.join(SUITE_DIR, 'Config', 'config.ini')
    update_config_ini(config_ini=config_path, LOG_PATH=output_dir)
    # Get configuration and environent from general config file
    config_type = config.get('general', 'CONFIGURATION_TYPE')
    env = config.get('general', 'ENVIRONMENT')
    env_yaml = config.get('general', 'ENV_YAML_FILE')
    # Check configuration and add it as default to the tags
    default_tag = get_config_tag(config_type)
    # Select tags to be used, empty if not set to execute all
    include_tags = ('{0}AND{1}'.format(default_tag, ARGS.tags)
                    if ARGS.tags else default_tag)
    if ARGS.run_suite_name == 'Setup':
        include_tags = ('{0}AND{1}'.format(include_tags, ARGS.environment))
    metadata_list = get_metadata()
    # Run sxt-test-suite using robot framework
    return robot.run(suite.path, outputdir=output_dir, debugfile=LOG_NAME,
              test=ARGS.tests,
              variable=['CONFIGURATION_TYPE :{}'.format(default_tag),
                        'ENVIRONMENT :{}'.format(env),
                        'ENV_YAML :{}'.format(env_yaml)],
              include=include_tags, tagstatinclude=include_tags,
              metadata=metadata_list)


if __name__ == '__main__':
    if CURRENT_USER == 'root':
        raise RuntimeError('DO NOT RUN AS ROOT')
    # Validate if script is called with at least one argument
    # Get args variables
    ARGS = get_args()

    if not (ARGS.run_suite_name or ARGS.run_all or ARGS.list_suite_name):
        sys.exit('Execution Suite could not be empty')

    env_configuration = (
        False if not (ARGS.environment and ARGS.configuration) else True)

    if ARGS.run_suite_name == 'Setup':
        if not env_configuration:
            sys.exit('Execution Environment arguments are required')
        else:
            config_dict = update_yaml_file(ARGS.configuration,
                                           ARGS.environment)
        configuration_type = config_dict['ctype']
        configuration_file = config_dict['cfile']
        environment_yaml = config_dict['eyaml']
        # Update configuration file with values selected from command line
        update_general_config_file(kernel_option(ARGS.configuration),
                                   configuration_type, ARGS.environment,
                                   configuration_file, environment_yaml)

    # Check options selected
    if ARGS.list_suite_name:
        list_suites_option(ARGS.list_suite_name)
    elif ARGS.run_all:
        sys.exit(run_suite_option(ARGS.run_suite_name))
    elif ARGS.run_suite_name:
        sys.exit(run_suite_option(ARGS.run_suite_name))
