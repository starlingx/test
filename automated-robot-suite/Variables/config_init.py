"""Provides a library of useful utilities for Robot Framework"""

import configparser


def get_variables(var_name, config_file):
    """Get variables from a config.ini

    This function  parse a config.ini file and return a dict
    with their values for use with Robot Framework as variables
    :param var_name: the variable used for make reference in robot, e.g:

    *** Settings ***
    Variables  Variables/ConfigInit.py  Config  %{PYTHONPATH}/Config/config.ini

    *** Variables ***
    ${kernel_option}   ${CONFIG.iso_installer.KERNEL_OPTION}

    :param config_file: the config.ini to parse
    :return
        - variables: the dict with all values from config.init
    """
    configurations = configparser.ConfigParser()
    configurations.read(config_file)

    variables = dict()
    for section in configurations.sections():
        for key, value in configurations.items(section):
            var = '{}.{}.{}'.format(var_name, section, key)
            variables[var] = str(value)

    return variables
