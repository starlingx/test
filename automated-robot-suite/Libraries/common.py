"""Provides a library of useful utilities for Robot Framework"""

import os
import configparser
import logging
import yaml
from Utils import bash_utils as bash
from Config import config

# create the logger object
LOG = logging.getLogger(__name__)


def update_config_ini(**kwargs):
    """Update a specific config.ini

    This function update a the values from a specific config.ini file

    :param kwargs: this is a dict that will contains the following values:
        - config_ini: which is absolute path to the config.ini (obligatory
                      variable)
        - config_section: which is the section to modify the variables
                          (optional variable)
        - all others variables are dynamic and they are directly dependent of
        the existing values in the config.ini, e.g:

        *** How to use this function ***

        - Example 1:

        scenario : the config.ini has a unique variable in all sections

        update_config_ini(
            config_ini='path_to_config.init', LOG_PATH='some_value')

        where LOG_PATH is an existing value in the config.ini.
        You can use as many values you want, the only limitation is that
        these must exist in the config.init file.

        - Example 2:

        scenario: the config.ini has duplicates variables in several sections

        update_config_ini(
            config_ini='path_to_config.init',
            config_section='LOGICAL_INTERFACE_2', LOG_PATH='some_value')

        where LOGICAL_INTERFACE_2 is an existing section in the config.ini,
        please notice that the variables here must exists in the section
        specified.

    :return
        This function returns a tuple with the following values:
        - status: this can be the following values:
            1. True, if some values from config.ini were modified
            2. False, if there were no modifications
        - message: a message with descriptive information about the
            success/error
    """

    status = False
    message = None

    if len(kwargs) < 2:
        raise RuntimeError('a minimum of two variables are expected')

    # obligatory variable
    config_ini = kwargs['config_ini']
    # optional variable
    config_section = kwargs.get('config_section', False)

    if not os.path.exists(config_ini):
        raise IOError('{}: does not exists'.format(config_ini))

    configurations = configparser.ConfigParser()
    # preserve the variables from config.ini in upper case
    configurations.optionxform = lambda option: option.upper()
    configurations.read(config_ini)

    # ------------------------ validation section ---------------------------
    # checking if the section given is valid (if any)
    if config_section and config_section not in configurations.sections():
        message = '{}: section does not exists'.format(config_section)
        return status, message

    elif not config_section:
        # checking if the values are in more than one section
        duplicates = 0

        for key, value in kwargs.items():
            for section in configurations.sections():
                if configurations.has_option(section, key):
                    duplicates += 1
                if duplicates > 1:
                    status = False
                    message = ('{}: is in more than one section, please '
                               'set config_section'.format(key))
                    return status, message
            duplicates = 0
    # -----------------------------------------------------------------------

    blacklist_keys = ['config_ini', 'config_section']
    count = 0

    # ------------------- update config values section ----------------------
    if config_section:
        # (the user provides a config_section)
        # get a list of tuples without the values in the blacklist list
        values = [x for x in kwargs.items() if x[0] not in blacklist_keys]

        for _key, _value in values:
            try:
                _ = configurations[config_section][_key]
            except KeyError:
                message = '{}: key does not exists in the section :{}'.format(
                    _key, config_section)
                return status, message
            else:
                configurations[config_section][_key] = _value
                count += 1
        status = True

    else:
        # (the user does not provides a config_section only values)
        # modifying configurations according to the values
        for section in configurations.sections():
            for item in configurations.items(section):
                for key, value in kwargs.items():
                    if key == item[0]:
                        configurations[section][item[0]] = value
                        count += 1
    # -----------------------------------------------------------------------

    if count != 0:
        with open(config_ini, 'w') as configfile:
            configurations.write(configfile)
            status = True
        message = '{}: was updated successfully'.format(os.path.basename(
            config_ini))

    return status, message


def string_to_dict(string_table):
    """Convert string table to dictionary

    This function convert a string table output from a command executed in the
    controller node into a dictionary.
    Useful to parse the output in keys/values for Robot Framework.

    @param string_table: the string table to convert into a dictionary, it
        comes from the controller node through Robot Framework.
    :return:
        a dictionary with all the string table entries.
    """
    # string_table variable comes from Robot Framework into a dictionary list
    # in unicode format, so we need the following
    # 1. converting string_table variable from unicode to ascii code
    # 2. split in a list with line breaks
    line_breaks_list = string_table['stdout'].split('\n')

    robot_dictionary = {}

    try:
        # getting the table headers without empty spaces
        table_headers = [
            header.strip() for header in line_breaks_list[1].split('|')[1:-1]
        ]
    except IndexError:
        err_dict = {
            'summary': {
                'err': 'IndexError',
                'cause': 'the command did not return a table'
            }
        }
        robot_dictionary.update(err_dict)
        return robot_dictionary

    # the blacklist is used for build the body variable without the index on it
    blacklist = [0, 1, 2, len(line_breaks_list) - 1]
    body = list(filter(
        lambda item: line_breaks_list.index(item) not in blacklist,
        line_breaks_list))

    table_data = [[v.strip() for v in i.strip('|').split('|')] for i in body]
    robot_dictionary = {
        table_headers[0]: {
            i[0]: {
                k: v for k, v in zip(table_headers[1:], i[1:])
            } for i in table_data
        }
    }

    return robot_dictionary


def get_cmd_boot_line():
    """Get a cmd boot line.

    This function build a custom cmd line in order to boot the startlingx iso
    :return:
        cmd: the cmd line for boot the iso.
    """

    kernel_option = config.get('iso_installer', 'KERNEL_OPTION')
    vmlinuz = config.get('iso_installer', 'VMLINUZ')
    consoles = config.get('iso_installer', 'CONSOLES')
    serial = config.get('iso_installer', 'SERIAL')
    opts_1 = config.get('iso_installer', 'OPTS_1')
    sys_type_1 = config.get('iso_installer', 'SYS_TYPE_1')
    sys_type_2 = config.get('iso_installer', 'SYS_TYPE_2')
    sys_type_3 = config.get('iso_installer', 'SYS_TYPE_3')
    opts_2 = config.get('iso_installer', 'OPTS_2')
    sec_prof_1 = config.get('iso_installer', 'SEC_PROF_1')
    sec_prof_2 = config.get('iso_installer', 'SEC_PROF_2')
    initrd = config.get('iso_installer', 'INITRD')

    cmd = False

    serial = '{vmlinuz} {consoles} {ser} {opts}'.format(
        vmlinuz=vmlinuz, consoles=consoles, ser=serial, opts=opts_1)
    no_serial = '{vmlinuz} {consoles} {opts}'.format(
        vmlinuz=vmlinuz, consoles=consoles, opts=opts_1)

    if kernel_option == '0':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_1, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S0':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_1, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))
    elif kernel_option == '1':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_1, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S1':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_1, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))
    elif kernel_option == '2':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_2, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S2':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_2, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))
    elif kernel_option == '3':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_2, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S3':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_2, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))
    elif kernel_option == '4':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_3, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S4':
        cmd = ('{serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            serial=serial, sys_type=sys_type_3, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))
    elif kernel_option == '5':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_3, opts=opts_2,
            sec_prof=sec_prof_1, initrd=initrd))
    elif kernel_option == 'S5':
        cmd = ('{no_serial} {sys_type} {opts} {sec_prof} {initrd}'.format(
            no_serial=no_serial, sys_type=sys_type_3, opts=opts_2,
            sec_prof=sec_prof_2, initrd=initrd))

    return cmd


def grub_checker(iso, mode, grub_option, grub_cmd):
    """Check a grub cmd boot line against the ones in the StarlingX ISO file

    This function compare the grub cmd boot line built from get_cmd_boot_line
    function against a StarlingX ISO file in order to check if this is still
    valid.
    Basically check if all the arguments from the ISO contains them in the
    built one from the get_cmd_boot_line function.

    :param iso: the iso to mount.
    :param mode: the mode to check the grub cmd line, this can be vbios/uefi.
    :param grub_option: the boot line to compare which could have the
        following values:
        - 0: Standard Controller Configuration > Serial Console >
             Standard Security Boot Profile.
        - S0: Standard Controller Configuration > Serial Console > Extended
              Security Boot Profile
        - 1: Standard Controller Configuration > Graphical Console >
             Standard Security Boot Profile
        - S1: Standard Controller Configuration > Graphical Console >
              Extended Security Boot Profile
        - 2: All-in-one Controller Configuration > Serial Console >
             Standard Security Boot Profile
        - S2: All-in-one Controller Configuration > Serial Console >
              Extended Security Boot Profile
        - 3: All-in-one Controller Configuration > Graphical Console >
             Standard Security Boot Profile
        - S3 All-in-one Controller Configuration > Graphical Console >
             Extended Security Boot Profile
        - 4: All-in-one (lowlatency) Controller Configuration >
             Serial Console > Standard Security Boot Profile
        - S4: All-in-one (lowlatency) Controller Configuration >
              Serial Console > Extended Security Boot Profile
        - 5: All-in-one (lowlatency) Controller Configuration >
             Graphical Console > Standard Security Boot Profile
        - S5: All-in-one (lowlatency) Controller Configuration >
              Graphical Console > Extended Security Boot Profile
    :param grub_cmd: the cmd line built from get_cmd_boot_line function
    :return
        - match: if the grub_cmd has all the elements from the iso
        - mismatch: if the grub_cmd does not have all the elements from the iso
    """
    allowed_grub_options = [
        '0', 'S0', '1', 'S1', '2', 'S2', '3', 'S3', '4', 'S4', '5', 'S5']

    if grub_option not in allowed_grub_options:
        raise KeyError('grub boot number does not exists')

    mount_point = '/tmp/cdrom'

    if os.path.exists(mount_point) and os.path.ismount(mount_point):
        bash.run_command('sudo umount -l {}'.format(mount_point),
                         raise_exception=True)
    elif not os.path.exists(mount_point):
        os.makedirs(mount_point)

    # mounting the iso file
    bash.run_command('sudo mount -o loop {} {}'.format(iso, mount_point),
                     raise_exception=True)

    if mode == 'vbios':
        grub = '{}/syslinux.cfg'.format(mount_point)
        regex = '-e "label [0-9]" -e "label [A-Z][0-9]" -e append'
        grub_extracted_lines = bash.run_command('grep {} {}'.format(
            regex, grub))
        grub_option_list = grub_extracted_lines[1].decode('utf-8').split('\n')

        key_dict = []
        values_dict = []

        # Filling the lists
        for line in grub_option_list:
            current_line = line.strip()
            if current_line.startswith('label'):
                key_dict.append(current_line.replace('label ', ''))
            elif current_line.startswith('append'):
                values_dict.append(current_line)

        # zipping the list in only one as a list of tuples
        grub_list = zip(key_dict, values_dict)
        grub_dict = dict()

        # creating a dict with the grub entries
        for key, value in grub_list:
            grub_dict[key] = value

        # comparing the grub boot line from the ISO with the one obtained from
        # get_cmd_boot_line function
        iso_boot_line = grub_dict[grub_option].split()

        # removing blacklist elements from iso_boot_line
        blacklist = [
            i for i, word in enumerate(iso_boot_line)
            if word.startswith('console')
        ]

        for index in blacklist:
            del iso_boot_line[index]

        if set(grub_cmd.split()).issuperset(set(iso_boot_line)):
            status = 'match'
        else:
            status = 'mismatch'
            diff = [
                element for element in iso_boot_line
                if element not in grub_cmd.split()]
            LOG.warning('missed params from cmd grub line')
            for element in diff:
                LOG.warning(element)

    elif mode == 'uefi':
        raise NotImplementedError
    else:
        raise IndexError('{}: not allowed'.format(mode))

    # dismount the mount_point
    bash.run_command('sudo umount -l {}'.format(mount_point),
                     raise_exception=True)

    return status


def get_controllers_ip(env, config_file, config_type, lab_file):
    """Get IPs of the controllers from the specific stx configuration file

    Args:
        - config_file: The stx-configuration.ini file
        - config_type: The type of configuration selected from the command
                       line.

    Return:
        - controller_data: Dictionary with the key name and the IP of the
                          controllers
    """

    # Read Configurtion File
    conf = yaml.safe_load(open(config_file))

    cont_data = {}
    # Get Controllers IP's
    if config_type == 'simplex':
        cont_data['IP_UNIT_0_ADDRESS'] = conf['external_oam_floating_address']
        cont_data['IP_UNIT_1_ADDRESS'] = ''
    else:
        cont_data['IP_UNIT_0_ADDRESS'] = conf['external_oam_node_0_address']
        cont_data['IP_UNIT_1_ADDRESS'] = conf['external_oam_node_1_address']

    if env == 'baremetal':
        # Get phyisical interfaces
        conf_lab = yaml.safe_load(open(lab_file))

        cont_data['OAM_IF'] = conf_lab['nodes']['controller-0']['oam_if']
        cont_data['MGMT_IF'] = conf_lab['nodes']['controller-0']['mgmt_if']

    return cont_data
