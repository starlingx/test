#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import random
import re
import os
import time
from pexpect import EOF
from string import ascii_lowercase, ascii_uppercase, digits

from consts.auth import Tenant, HostLinuxUser, CliAuth
from consts.stx import Prompt, EventLogID
from consts.proj_vars import ProjVar
from utils.tis_log import LOG
from utils import exceptions
from utils.clients.ssh import ControllerClient, SSHClient, SSHFromSSH
from keywords import system_helper, keystone_helper, common

MIN_LINUX_PASSWORD_LEN = 7
SPECIAL_CHARACTERS = r'!@#$%^&*()<>{}+=_\\\[\]\-?|~`,.;:'

# use this simple "dictionary" for now, because no english dictionary
# installed on test server
SIMPLE_WORD_DICTIONARY = '''
and is being proof-read and supplemented by volunteers from around the
world.  This is an unfunded project, and future enhancement of this
dictionary will depend on the efforts of volunteers willing to help build
this free resource into a comprehensive body of general information.  New
definitions for missing words or words senses and longer explanatory notes,
as well as images to accompany the articles are needed.  More modern
illustrative quotations giving recent examples of usage of the words in
their various senses will be very helpful, since most quotations in the
original 1913 dictionary are now well over 100 years old
'''


class LinuxUser:
    users = {HostLinuxUser.get_user(): HostLinuxUser.get_password()}
    con_ssh = None

    def __init__(self, user, password, con_ssh=None):
        self.user = user
        self.password = password
        self.added = False
        self.con_ssh = con_ssh if con_ssh is not None else \
            ControllerClient.get_active_controller()

    def add_user(self):
        self.added = True
        LinuxUser.users[self.user] = self.password
        raise NotImplementedError

    def modify_password(self):
        raise NotImplementedError

    def delete_user(self):
        raise NotImplementedError

    def login(self):
        raise NotImplementedError

    @classmethod
    def get_user_password(cls):
        raise NotImplementedError

    @classmethod
    def get_current_user_password(cls, con_ssh=None):
        if con_ssh:
            cls.con_ssh = con_ssh
        elif not cls.con_ssh:
            cls.con_ssh = ControllerClient.get_active_controller()
        user = cls.con_ssh.get_current_user()
        return user, cls.users[user]


class Singleton(type):
    """
    A singleton used to make sure only one instance of a class is allowed to
    create
    """

    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super(Singleton, cls).__call__(*args,
                                                                  **kwargs)
        return cls.__instances[cls]


def get_ldap_user_manager():
    """
    Get the only instance of the LDAP User Manager

    Returns (LdapUserManager):
        the only instance of the LDAP User Manager
    """
    return LdapUserManager()


class LdapUserManager(object, metaclass=Singleton):
    """
    The LDAP User Manager

    """

    LINUX_ROOT_PASSWORD = HostLinuxUser.get_password()
    KEYSTONE_USER_NAME = Tenant.get('admin')['user']
    KEYSTONE_USER_DOMAIN_NAME = 'Default'
    KEYSTONE_PASSWORD = Tenant.get('admin')['password']
    PROJECT_NAME = 'admin'
    PROJECT_DOMAIN_NAME = 'Default'

    def __init__(self, ssh_con=None):
        if ssh_con is not None:
            self.ssh_con = ssh_con
        else:
            self.ssh_con = ControllerClient.get_active_controller()

        self.users_info = {}

    def ssh_to_host(self, host=None):
        """
        Get the ssh connection to the active controller or the specified host
        (if it's the case)

        Args:
            host (str):     the host to ssh to, using the active controller
            if it's unset or None

        Returns (object):
            the ssh connection session to the active controller

        """
        if host is None:
            return self.ssh_con
        else:
            return SSHClient(host=host)

    def get_ldap_admin_password(self):
        """
        Get the LDAP Administrator's password

        Args:

        Returns (str):
            The password of the LDAP Administrator

        """
        cmd = 'grep "credentials" /etc/openldap/slapd.conf.backup'
        self.ssh_con.flush()
        code, output = self.ssh_con.exec_sudo_cmd(cmd)

        if 0 == code and output.strip():
            for line in output.strip().splitlines():
                if 'credentials' in line and '=' in line:
                    password = line.split('=')[1]
                    return password

        return ''

    def get_ldap_user_password(self, user_name):
        """
        Get the password of the LDAP User

        Args:
            user_name (str):
                    the user name

        Returns (str):
            the password of the user
        """
        if user_name in self.users_info and \
                self.users_info[user_name]['passwords']:
            return self.users_info[user_name]['passwords'][-1]

        return None

    def login_as_ldap_user_first_time(self, user_name, new_password=None,
                                      host=None):
        """
        Login with the specified LDAP User for the first time,
            during which change the initial password as a required step.

        Args:
            user_name (str):        user name of the LDAP user
            new_password (str):     password of the LDAP user
            host (str):             host name to which the user will login

        Returns (tuple):
            results (bool):         True if success, otherwise False
            password (str):         new password of the LDAP user

        """

        hostname_ip = 'controller-1' if host is None else host

        if new_password is not None:
            password = new_password
        else:
            password = 'new_{}_Li69nux!'.format(
                ''.join(random.sample(user_name, len(user_name))))

        cmd_expected = [
            (
                'ssh -l {} -o UserKnownHostsFile=/dev/null {}'.format(
                    user_name, hostname_ip),
                (r'Are you sure you want to continue connecting (yes/no)?',),
                ('Failed to get "continue connecting" prompt',)
            ),
            (
                'yes',
                # ("{}@{}'s password:".format(user_name, hostname_ip),),
                (r".*@.*'s password: ".format(hostname_ip),),
                ('Failed to get password prompt',)
            ),
            (
                '{}'.format(user_name),
                (r'\(current\) LDAP Password: ',),
                ('Failed to get password prompt for current password',)
            ),
            (
                '{}'.format(user_name),
                ('New password: ',),
                ('Failed to get password prompt for new password',)
            ),
            (
                '{}'.format(password),
                ('Retype new password: ',),
                ('Failed to get confirmation password prompt for new password',)
            ),
            (
                '{}'.format(password),
                (
                    'passwd: all authentication tokens updated successfully.',
                    'Connection to controller-1 closed.',
                ),
                ('Failed to change to new password for current user:{}'.format(
                    user_name),)
            ),
            (
                '',
                (self.ssh_con.get_prompt(),),
                (
                    'Failed in last step of first-time login as LDAP '
                    'User:{}'.format(user_name),)
            ),
        ]

        result = True
        self.ssh_con.flush()
        for cmd, expected, errors in cmd_expected:
            self.ssh_con.send(cmd)
            index = self.ssh_con.expect(blob_list=list(expected + errors))
            if len(expected) <= index:
                result = False
                break

        self.ssh_con.flush()

        return result, password

    def find_ldap_user(self, user_name):
        """
        Find the LDAP User with the specified name

        Args:
            user_name (str):            - user name of the LDAP User to
            search for

        Returns:
            existing_flag (boolean)     - True, the LDAP User with the
            specified name existing
                                        - False, cannot find a LDAP User with
                                        the specified name

            user_info (dict):           - user information
        """

        cmd = 'ldapfinger -u {}'.format(user_name)
        self.ssh_con.flush()
        code, output = self.ssh_con.exec_sudo_cmd(cmd, fail_ok=True,
                                                  strict_passwd_prompt=True)

        found = False
        user_info = {}
        if output.strip():
            for line in output.strip().splitlines():
                if line.startswith('dn: '):
                    user_info['dn'] = line.split()[1].strip()
                elif line.startswith('cn: '):
                    user_info['cn'] = line.split()[1].strip()
                elif line.startswith('uid: '):
                    user_info['uid'] = line.split()[1].strip()
                elif line.startswith('uidNumber: '):
                    user_info['uid_number'] = int(line.split()[1].strip())
                elif line.startswith('gidNumber: '):
                    user_info['gid_number'] = int(line.split()[1].strip())
                elif line.startswith('homeDirectory: '):
                    user_info['home_directory'] = line.split()[1].strip()
                elif line.startswith('userPassword:: '):
                    user_info['user_password'] = line.split()[1].strip()
                elif line.startswith('loginShell: '):
                    user_info['login_shell'] = line.split()[1].strip()
                elif line.startswith('shadowMax: '):
                    user_info['shadow_max'] = int(line.split()[1].strip())
                elif line.startswith('shadowWarning: '):
                    user_info['shadow_warning'] = int(line.split()[1].strip())
                else:
                    pass
            else:
                found = True

        return found, user_info

    def rm_ldap_user(self, user_name):
        """
        Delete the LDAP User with the specified name

        Args:
            user_name:

        Returns (tuple):
            code   -   0    successfully deleted the specified LDAP User
                        otherwise: failed
            output  -   message from the deleting CLI
        """

        cmd = 'ldapdeleteuser {}'.format(user_name)

        self.ssh_con.flush()
        code, output = self.ssh_con.exec_sudo_cmd(cmd, fail_ok=True)

        if 0 == code and user_name in self.users_info:
            del self.users_info[user_name]

        return code, output

    @staticmethod
    def validate_user_settings(secondary_group=False,
                               secondary_group_name=None,
                               password_expiry_days=90,
                               password_expiry_warn_days=2
                               ):
        """
        Validate the settings to be used as attributes of a LDAP User

        Args:
            secondary_group (bool):
                True    -   Secondary group to add user to
                False   -   No secondary group
            secondary_group_name (str):     Name of secondary group (will be
            ignored if secondary_group is False
            password_expiry_days (int):
            password_expiry_warn_days (int):

        Returns:

        """

        try:
            opt_expiry_days = int(password_expiry_days)
            opt_expiry_warn_days = int(password_expiry_warn_days)
            bool(secondary_group)
            str(secondary_group_name)
        except ValueError:
            return 1, 'invalid input: {}, {}'.format(password_expiry_days,
                                                     password_expiry_warn_days)

        if opt_expiry_days <= 0:
            return 4, 'invalid password expiry days:{}'.format(opt_expiry_days)

        if opt_expiry_warn_days <= 0:
            return 5, 'invalid password expiry days:{}'.format(
                opt_expiry_warn_days)

        return 0, ''

    def create_ldap_user(self,
                         user_name,
                         sudoer=False,
                         secondary_group=False,
                         secondary_group_name=None,
                         password_expiry_days=90,
                         password_expiry_warn_days=2,
                         delete_if_existing=True,
                         check_if_existing=True):
        """

        Args:
            user_name (str):        user name of the LDAP User
            sudoer (boo)
                True    -   Add the user to sudoer list
                False   -   Do not add the user to sudoer list
            secondary_group (bool):
                True    -   Secondary group to add user to
                False   -   No secondary group
            secondary_group_name (str):     Name of secondary group (will be
            ignored if secondary_group is False
            password_expiry_days (int):
            password_expiry_warn_days (int):
            delete_if_existing (bool):
                True    -   Delete the user if it is already existing
                False   -   Return the existing LDAP User
            check_if_existing (bool):
                True    -   Check if the LDAP User existing with the
                specified name
                False   -   Do not check if any LDAP Users with the specified
                name existing

        Returns tuple(code, user_infor):
            code (int):
                -1   -- a LDAP User already existing with the same name (
                don't care other attributes for now)
                0   -- successfully created a LDAP User withe specified name
                and attributes
                1  -- a LDAP User already existing but fail_on_existing
                specified
                2  -- CLI to create a user succeeded but cannot find the user
                after
                3  -- failed to create a LDAP User (the CLI failed)
                4  -- failed to change the initial password and login the
                first time
                5  -- invalid inputs
        """
        password_expiry_days = 90 if password_expiry_days is None else \
            password_expiry_days
        password_expiry_warn_days = 2 if password_expiry_warn_days is None \
            else password_expiry_warn_days
        secondary_group = False if secondary_group is None else secondary_group
        secondary_group_name = '' if secondary_group_name is None else \
            secondary_group_name

        code, message = self.validate_user_settings(
            secondary_group=secondary_group,
            secondary_group_name=secondary_group_name,
            password_expiry_days=password_expiry_days,
            password_expiry_warn_days=password_expiry_warn_days)
        if 0 != code:
            return 5, {}

        if check_if_existing:
            existing, user_info = self.find_ldap_user(user_name)
            if existing:
                if delete_if_existing:
                    code, message = self.rm_ldap_user(user_name)
                    if 0 != code:
                        return 1, user_info
                else:
                    return -1, user_info
        cmds_expectings = [
            (
                'sudo ldapusersetup',
                (r'Enter username to add to LDAP:',),
                ()
            ),
            (
                '{}'.format(user_name),
                (r'Add {} to sudoer list? (yes/NO): '.format(user_name),),
                ('Critical setup error: cannot add user.*',),
            ),
            (
                'yes' if sudoer else 'NO',
                (r'Add .* to secondary user group\? \(yes/NO\):',),
                ()
            ),
        ]

        if secondary_group:
            cmds_expectings += [
                (
                    'yes',
                    (r'Secondary group to add user to? [wrs_protected]: ',),
                    ()
                ),
                (
                    '{}'.format(secondary_group_name),
                    (
                        r'Enter days after which user password must be changed '
                        r'\[{}\]:'.format(password_expiry_days),),
                    ()
                )

            ]
        else:
            cmds_expectings += [
                (
                    'NO',
                    (
                        r'Enter days after which user password must be changed '
                        r'\[{}\]:'.format(password_expiry_days),),
                    (),
                ),
            ]

        cmds_expectings += [
            (
                '{}'.format(password_expiry_days),
                (
                    r'Enter days before password is to expire that user is '
                    r'warned \[{}\]:'.format(password_expiry_warn_days),),
                (),
            ),
            (
                '{}'.format(password_expiry_warn_days),
                (
                    'Successfully modified user entry uid=m-user01,ou=People,'
                    'dc=cgcs,dc=local in LDAP',
                    'Updating password expiry to {} days'.format(
                        password_expiry_warn_days),
                ),
                (),
            )
        ]

        created = True
        self.ssh_con.flush()
        for cmd, outputs, errors in cmds_expectings:
            self.ssh_con.send(cmd)
            expected_outputs = list(outputs + errors)

            index = self.ssh_con.expect(blob_list=expected_outputs,
                                        fail_ok=True)
            if len(outputs) <= index:
                created = False
                break
            expected_outputs[:] = []

        time.sleep(3)

        user_info = {}
        if created:
            existing, user_info = self.find_ldap_user(user_name)
            if existing:
                success, password = self.login_as_ldap_user_first_time(
                    user_name)
                if not success:
                    code = 4
                else:
                    user_info['passwords'] = [password]
                    self.users_info[user_name] = user_info
                    code = 0
            else:
                code = 2
        else:
            code = 3

        return code, user_info

    def login_as_ldap_user(self, user_name, password, host=None,
                           pre_store=False, disconnect_after=False):
        """
        Login as the specified user name and password onto the specified host

        Args:
            user_name (str):        user name
            password (str):         password
            host (str):             host to login to
            pre_store (bool):
                    True    -       pre-store keystone user credentials for
                    session
                    False   -       chose 'N' (by default) meaning do not
                    pre-store keystone user credentials
            disconnect_after (bool):
                    True    -       disconnect the logged in session
                    False   -       keep the logged in session

        Returns (tuple):
            logged_in (bool)    -   True if successfully logged into the
            specified host
                                    using the specified user/password
            password (str)      -   the password used to login
            ssh_con (object)    -   the ssh session logged in
        """
        if not host:
            host = 'controller-1'
            if system_helper.is_aio_simplex():
                host = 'controller-0'

        prompt_keystone_user_name = r'Enter Keystone username \[{}\]: '.format(
            user_name)
        cmd_expected = (
            (
                'ssh -l {} -o UserKnownHostsFile=/dev/null {}'.format(user_name,
                                                                      host),
                (r'Are you sure you want to continue connecting \(yes/no\)\?',),
                (
                    'ssh: Could not resolve hostname {}: Name or service not '
                    'known'.format(host),),
            ),
            (
                'yes',
                (r'{}@{}\'s password: '.format(user_name, host),),
                (),
            ),
            (
                '{}'.format(password),
                (prompt_keystone_user_name, Prompt.CONTROLLER_PROMPT,),
                (r'Permission denied, please try again\.',),
            ),
        )

        logged_in = False
        self.ssh_con.flush()
        for i in range(len(cmd_expected)):
            cmd, expected, errors = cmd_expected[i]
            LOG.info('cmd={}\nexpected={}\nerrors={}\n'.format(cmd, expected,
                                                               errors))
            self.ssh_con.send(cmd)

            index = self.ssh_con.expect(blob_list=list(expected + errors))
            if len(expected) <= index:
                break
            elif 3 == i:
                if expected[index] == prompt_keystone_user_name:
                    assert pre_store, \
                        'pre_store is False, while selecting "y" to ' \
                        '"Pre-store Keystone user credentials ' \
                        'for this session!"'
                else:
                    logged_in = True
                    break
        else:
            logged_in = True

        if logged_in:
            if disconnect_after:
                self.ssh_con.send('exit')

        return logged_in, password, self.ssh_con

    def change_ldap_user_password(self, user_name, password, new_password,
                                  change_own_password=True,
                                  check_if_existing=True, host=None,
                                  disconnect_after=False):
        """
        Modify the password of the specified user to the new one

        Args:
            user_name (str):
                -   name of the LDAP User

            password (str):
                -   password of the LDAP User

            new_password (str):
                -   new password to change to
            change_own_password (bool):

            check_if_existing (bool):
                -   True:   check if the user already existing first
                    False:  change the password without checking the
                    existence of the user

            host (str):
                -   The host to log into

            disconnect_after (bool)
                -   True:   disconnect the ssh connection after changing the
                password
                -   False:  keep the ssh connection

        Returns (bool):
                True if successful, False otherwise
        """

        if check_if_existing:
            found, user_info = self.find_ldap_user(user_name)
            if not found:
                return False

        if not change_own_password:
            return False

        logged_in, password, ssh_con = \
            self.login_as_ldap_user(user_name,
                                    password=password,
                                    host=host,
                                    disconnect_after=False)

        if not logged_in or not password or not ssh_con:
            return False, ssh_con

        cmds_expected = (
            (
                'passwd',
                (r'\(current\) LDAP Password: ',),
                (),
            ),
            (
                password,
                ('New password: ',),
                ('passwd: Authentication token manipulation error', EOF,),
            ),
            (
                new_password,
                ('Retype new password: ',),
                (
                    'BAD PASSWORD: The password is too similar to the old one',
                    'BAD PASSWORD: No password supplied',
                    'passwd: Have exhausted maximum number of retries for '
                    'service',
                    EOF,
                ),
            ),
            (
                new_password,
                ('passwd: all authentication tokens updated successfully.',),
                (),
            ),
        )

        changed = True
        ssh_con.flush()
        for cmd, expected, errors in cmds_expected:
            ssh_con.send(cmd)
            index = ssh_con.expect(blob_list=list(expected + errors))
            if len(expected) <= index:
                changed = False
                break

        if disconnect_after:
            ssh_con.send('exit')

        return changed, ssh_con


def get_admin_password_in_keyring(con_ssh=None):
    """
    Get admin password via 'keyring get CGCS admin'
    Args:
        con_ssh (SSHClient): active controller client

    Returns (str): admin password returned

    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    admin_pswd = con_ssh.exec_cmd('keyring get CGCS admin', fail_ok=False)[1]
    return admin_pswd


def change_linux_user_password(password, new_password, user=None,
                               host=None):
    if not user:
        user = HostLinuxUser.get_user()

    LOG.info(
        'Attempt to change password, from password:{}, to new-password:{}, '
        'on host:{}'.format(
            password, new_password, host))

    input_outputs = (
        (
            'passwd',
            (r'\(current\) UNIX password: ',),
            (),
        ),
        (
            password,
            ('New password: ',),
            (': Authentication token manipulation error', EOF,),
        ),
        (
            new_password,
            ('Retype new password:',),
            (
                'BAD PASSWORD: The password is too similar to the old one',
                'BAD PASSWORD: No password supplied',
                'passwd: Have exhausted maximum number of retries for service',
                EOF,
            ),
        ),
        (
            new_password,
            (': all authentication tokens updated successfully.',
             Prompt.CONTROLLER_PROMPT,),
            (),
        ),
    )
    conn_to_ac = ControllerClient.get_active_controller()
    initial_prompt = r'.*{}\:~\$ '.format(host)
    LOG.info('Will login as user:"{}", password:"{}", to host:"{}"'.format(
        user, password, host))

    conn = SSHFromSSH(conn_to_ac, host, user, password, force_password=True,
                      initial_prompt=initial_prompt)
    passed = True
    try:
        conn.connect(retry=False, use_password=True)
        for cmd, expected, errors in input_outputs:
            # conn.flush()
            LOG.info("Send '{}'\n".format(cmd))
            conn.send(cmd)
            blob_list = list(expected) + list(errors)
            LOG.info("Expect: {}\n".format(blob_list))
            index = conn.expect(blob_list=blob_list)
            LOG.info('returned index:{}\n'.format(index))
            if len(expected) <= index:
                passed = False
                break

    except Exception as e:
        LOG.warn(
            'Caught exception when connecting to host:{} as user:{} with '
            'pasword:{}\n{}\n'.format(
                host, user, password, e))

        raise

    finally:
        if user != HostLinuxUser.get_user():
            conn.close()

    # flush the output to the cli so the next cli is correctly registered
    conn.flush()
    LOG.info(
        'Successfully changed password from:\n{}\nto:{} for user:{} on '
        'host:{}'.format(password, new_password, user, host))

    return passed, new_password


def gen_linux_password(exclude_list=None, length=32):
    if exclude_list is None:
        exclude_list = []

    if not isinstance(exclude_list, list):
        exclude_list = [exclude_list]

    if length < MIN_LINUX_PASSWORD_LEN:
        LOG.warn(
            'Length requested is too small, must longer than {}, requesting '
            '{}'.format(MIN_LINUX_PASSWORD_LEN, length))
        return None

    total = length
    left = 3

    vocabulary = [ascii_lowercase, ascii_uppercase, digits, SPECIAL_CHARACTERS]

    password = ''
    while not password:
        raw_password = []
        for chars in vocabulary:
            count = random.randint(1, total - left)
            raw_password += random.sample(chars, min(count, len(chars)))
            left -= 1
            total -= count

        password = ''.join(
            random.sample(raw_password, min(length, len(raw_password))))

        missing_length = length - len(password)
        if missing_length > 0:
            all_chars = ''.join(vocabulary)
            password += ''.join(
                random.choice(all_chars) for _ in range(missing_length))

        if password in exclude_list:
            password = ''

    LOG.debug('generated valid password:{}'.format(password))

    return password


def gen_invalid_password(invalid_type='shorter', previous_passwords=None,
                         minimum_length=7):
    if previous_passwords is None:
        previous_passwords = []

    valid_password = list(gen_linux_password(exclude_list=previous_passwords,
                                             length=minimum_length * 4))

    current_length = len(valid_password)

    if invalid_type == 'shorter':
        invalid_len = random.randint(1, minimum_length - 1)
        invalid_password = random.sample(valid_password, invalid_len)

    elif invalid_type == '1_lowercase':
        invalid_password = ''.join(
            c for c in valid_password if c not in ascii_lowercase)
        missing_length = current_length - len(invalid_password)
        invalid_password += ''.join(
            random.choice(ascii_uppercase) for _ in range(missing_length))

    elif invalid_type == '1_uppercase':
        invalid_password = ''.join(
            c for c in valid_password if c not in ascii_uppercase)
        missing_length = current_length - len(invalid_password)
        invalid_password += ''.join(
            random.choice(ascii_lowercase) for _ in range(missing_length))

    elif invalid_type == '1_digit':
        invalid_password = ''.join(c for c in valid_password if c not in digits)
        missing_length = current_length - len(invalid_password)
        invalid_password += ''.join(
            random.choice(ascii_lowercase) for _ in range(missing_length))

    elif invalid_type == '1_special':
        invalid_password = ''.join(
            c for c in valid_password if c not in SPECIAL_CHARACTERS)
        missing_length = current_length - len(invalid_password)
        invalid_password += ''.join(
            random.choice(ascii_lowercase) for _ in range(missing_length))

    elif invalid_type == 'not_in_dictionary':
        invalid_password = random.choice(
            re.split(r'\W', SIMPLE_WORD_DICTIONARY))

    elif invalid_type == 'diff_more_than_3':
        if not previous_passwords or len(previous_passwords) < 1:
            return None

        last_password = previous_passwords[-1]
        len_last_password = len(last_password)
        count_difference = random.randint(0, 2)
        for index in random.sample(range(len_last_password), count_difference):
            cur_char = last_password[index]
            last_password[index] = random.choice(
                c for c in last_password if c != cur_char)
        invalid_password = ''.join(last_password)

    elif invalid_type == 'not_simple_reverse':
        if not previous_passwords or len(previous_passwords) < 1:
            return None
        invalid_password = ''.join(reversed(previous_passwords[-1]))

    elif invalid_type == 'not_only_case_diff':
        if not previous_passwords or len(previous_passwords) < 1:
            return None
        invalid_password = []
        for ch in valid_password:
            if ch.islower():
                invalid_password.append(ch.upper())
            elif ch.isupper():
                invalid_password.append(ch.lower())
            else:
                invalid_password.append(ch)

        invalid_password = ''.join(invalid_password)

    elif invalid_type == 'not_last_2':
        if not previous_passwords or len(previous_passwords) < 1:
            return None
        invalid_password = random.choice(previous_passwords[-2:])

    elif invalid_type == '5_failed_attempts':
        invalid_password = ''

    else:
        assert False, 'Unknown password rule:{}'.format(invalid_type)

    return ''.join(invalid_password)


def modify_https(enable_https=True, check_first=True, con_ssh=None,
                 auth_info=Tenant.get('admin_platform'),
                 fail_ok=False):
    """
    Modify platform https via 'system modify https_enable=<bool>'

    Args:
        enable_https (bool): True/False to enable https or not
        check_first (bool): if user want to check if the lab is already in
        the state that user try to enable
        con_ssh (SSHClient):
        auth_info (dict):
        fail_ok (bool):

    Returns (tuple):
        (-1, msg)
        (0, msg)
        (1, <std_err>)

    """
    if check_first:
        is_https = keystone_helper.is_https_enabled(source_openrc=False,
                                                    auth_info=auth_info,
                                                    con_ssh=con_ssh)
        if (is_https and enable_https) or (not is_https and not enable_https):
            msg = "Https is already {}. Do nothing.".format(
                'enabled' if enable_https else 'disabled')
            LOG.info(msg)
            return -1, msg

    LOG.info("Modify system to {} https".format(
        'enable' if enable_https else 'disable'))
    res, output = system_helper.modify_system(fail_ok=fail_ok, con_ssh=con_ssh,
                                              auth_info=auth_info,
                                              https_enabled='{}'.format(
                                                  str(enable_https).lower()))
    if res == 1:
        return 1, output

    LOG.info("Wait up to 60s for config out-of-date alarm with best effort.")
    system_helper.wait_for_alarm(alarm_id=EventLogID.CONFIG_OUT_OF_DATE,
                                 entity_id='controller-', strict=False,
                                 con_ssh=con_ssh, timeout=60, fail_ok=True,
                                 auth_info=auth_info)

    LOG.info("Wait up to 600s for config out-of-date alarm to clear.")
    system_helper.wait_for_alarm_gone(EventLogID.CONFIG_OUT_OF_DATE,
                                      con_ssh=con_ssh, timeout=600,
                                      check_interval=20, fail_ok=False,
                                      auth_info=auth_info)

    LOG.info("Wait up to 300s for public endpoints to be updated")
    expt_status = 'enabled' if enable_https else 'disabled'
    end_time = time.time() + 300
    while time.time() < end_time:
        if keystone_helper.is_https_enabled(con_ssh=con_ssh,
                                            source_openrc=False,
                                            auth_info=auth_info) == \
                enable_https:
            break
        time.sleep(10)
    else:
        raise exceptions.KeystoneError(
            "Https is not {} in 'openstack endpoint list'".format(expt_status))

    msg = 'Https is {} successfully'.format(expt_status)
    LOG.info(msg)
    # TODO: install certificate for https. There will be a warning msg if
    #  self-signed certificate is used

    if not ProjVar.get_var('IS_DC') or \
            (auth_info and auth_info.get('region', None) in (
            'RegionOne', 'SystemController')):
        # If DC, use the central region https as system https, since that is
        # the one used for external access
        CliAuth.set_vars(HTTPS=enable_https)

    return 0, msg


def set_ldap_user_password(user_name, new_password, check_if_existing=True,
                           fail_ok=False):
    """
    Set ldap user password use ldapsetpasswd

    Args:
        user_name (str):
            -   name of the LDAP User

        new_password (str):
            -   new password to change to

        check_if_existing (bool):
            -   True:   check if the user already existing first
                False:  change the password without checking the existence of
                    the user

        fail_ok (bool)

    Returns (bool):
            True if successful, False otherwise
    """

    if check_if_existing:
        found, user_info = LdapUserManager().find_ldap_user(user_name=user_name)
        if not found:
            return False

    ssh_client = ControllerClient.get_active_controller()
    rc, output = ssh_client.exec_sudo_cmd(
        'ldapsetpasswd {} {}'.format(user_name, new_password), fail_ok=fail_ok)
    if rc > 1:
        return 1, output

    return rc, output


def fetch_cert_file(cert_file=None, scp_to_local=True, con_ssh=None):
    """
    fetch cert file from build server. scp to TiS.
    Args:
        cert_file (str): valid values: ca-cert, server-with-key
        scp_to_local (bool): Whether to scp cert file to localhost as well.
        con_ssh (SSHClient): active controller ssh client

    Returns (str|None):
        cert file path on localhost if scp_to_local=True, else cert file path
        on TiS system. If no certificate found, return None.

    """
    if not cert_file:
        cert_file = '{}/ca-cert.pem'.format(HostLinuxUser.get_home())

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    if not con_ssh.file_exists(cert_file):
        raise FileNotFoundError(
            '{} not found on active controller'.format(cert_file))

    if scp_to_local:
        cert_name = os.path.basename(cert_file)
        dest_path = os.path.join(ProjVar.get_var('TEMP_DIR'), cert_name)
        common.scp_from_active_controller_to_localhost(source_path=cert_file,
                                                       dest_path=dest_path,
                                                       timeout=120)
        cert_file = dest_path
        LOG.info("Cert file copied to {} on localhost".format(dest_path))

    return cert_file
