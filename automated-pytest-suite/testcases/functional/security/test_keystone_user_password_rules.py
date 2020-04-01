#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import random
import re
import time
import copy
from string import ascii_lowercase, ascii_uppercase, digits, ascii_letters

from pytest import mark, skip, fixture

from consts.auth import Tenant
from keywords import keystone_helper, container_helper, kube_helper
from utils import cli
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient


SPECIAL_CHARACTERS = r'!@#$%^&*()<>{}+=_\\\[\]\-?|~`,.;:'
MIN_PASSWORD_LEN = 7
MAX_PASSWORD_LEN = 128

# keystone.conf security_compliance configs
LOCKOUT_DURATION = 300
FAILURE_ATTEMPTS = 5
UNIQUE_LAST_COUNT = 2

# Test user
TEST_USER_NAME = 'stxtestuser'
TEST_PASSWORD = 'Password*Rule1Test'
USED_PASSWORDS = {}
WAIT_BETWEEN_CHANGE = 6

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


def save_used_password(keystone, password):
    if keystone not in USED_PASSWORDS:
        USED_PASSWORDS[keystone] = [password]
    else:
        used_passwords = USED_PASSWORDS[keystone]
        used_passwords.append(password)
        if len(used_passwords) > UNIQUE_LAST_COUNT:
            used_passwords.pop(0)

    LOG.info('{} keystone user {} password saved. \nUsed passwords: {}'.format(
        keystone, TEST_USER_NAME, USED_PASSWORDS[keystone]))


def is_last_used(password, keystone, depth=UNIQUE_LAST_COUNT):
    used_passwords = USED_PASSWORDS.get(keystone, [])
    if used_passwords:
        if len(used_passwords) >= UNIQUE_LAST_COUNT:
            return password in used_passwords[-1 * depth:]
        else:
            return password in used_passwords

    return False


def get_valid_password(keystone):
    total_length = random.randint(MIN_PASSWORD_LEN, MAX_PASSWORD_LEN)
    password = None
    frequently_used_words = re.split(r'\W', SIMPLE_WORD_DICTIONARY.strip())

    attempt = 0
    while attempt < 60:
        attempt += 1
        left_count = total_length
        lower_case_len = random.randint(1, left_count - 3)
        left_count -= lower_case_len

        upper_case_len = random.randint(1, left_count - 2)
        left_count -= upper_case_len

        digit_len = random.randint(1, left_count - 1)
        left_count -= digit_len

        special_char_len = random.randint(1, left_count)

        lower_case = random.sample(ascii_lowercase, min(lower_case_len, len(ascii_lowercase)))
        upper_case = random.sample(ascii_uppercase, min(upper_case_len, len(ascii_uppercase)))
        password_digits = random.sample(digits, min(digit_len, len(digits)))
        special_char = random.sample(SPECIAL_CHARACTERS, min(special_char_len,
                                                             len(SPECIAL_CHARACTERS)))

        actual_len = len(lower_case) + len(upper_case) + len(password_digits) + len(special_char)

        password = random.sample(lower_case + upper_case + password_digits + special_char,
                                 min(actual_len, total_length))
        alphabet = ascii_lowercase + ascii_uppercase + digits + SPECIAL_CHARACTERS

        password = ''.join(password)
        if actual_len != len(password):
            LOG.warn('actual_len:{}, password len:{}, password:{}\n'.format(
                actual_len, len(password), password))

        if len(password) < total_length:
            password += \
                ''.join(random.choice(alphabet) for _ in range(total_length - len(password) + 1))

        list_of_chars = list(password)

        if (list_of_chars[0] == '{') or (list_of_chars[0] == '}') or (list_of_chars[0] == '-'):
            list_of_chars[0] = 'a'

        if (list_of_chars[-1] == '{') or (list_of_chars[-1] == '}'):
            list_of_chars[-1] = 'a'

        for index, char in enumerate(list_of_chars):
            next_char = list_of_chars[index + 1] if index != len(list_of_chars) - 1 else ''

            if char == '{':
                if next_char == '{' or next_char == '}':
                    list_of_chars[index + 1] = 'a'
                    list_of_chars[index - 1] = '{'
                else:
                    list_of_chars[index - 1] = '{'
            if char == '}':
                if next_char != '{':
                    list_of_chars[index - 1] = '}'

        password = ''.join(list_of_chars)

        if not is_last_used(password, keystone=keystone) and password not in \
                frequently_used_words:
            break

    if attempt < 60:
        LOG.debug('Found valid password:\n{}\n'.format(password))
    else:
        LOG.debug('Cannot found valid password, attempted:{}\n'.format(attempt))

    return password


def multiple_attempts_generator():
    LOG.info('Attempt with wrong passwords multiple times')
    invalid_password = ''.join(random.sample(ascii_letters, MIN_PASSWORD_LEN - 1))

    while True:
        count, keystone, is_admin, user_name = yield
        current_password = USED_PASSWORDS[keystone][-1]
        for n in range(int(count)):
            verify_user(user_name, invalid_password, is_admin=is_admin, expect_fail=True,
                        keystone=keystone)
            LOG.info('Command rejected with INVALID password as expected, count: {}'.format(n + 1))
            time.sleep(10)

        time.sleep(20)

        LOG.tc_step('Verify {} keystone user {} is locked out after {} failed '
                    'attempts'.format(keystone, user_name, count))
        verify_user(user_name, current_password, is_admin=is_admin, expect_fail=True,
                    keystone=keystone)

        LOG.tc_step('Wait for {} seconds and verify account is unlocked'.format(
            LOCKOUT_DURATION + WAIT_BETWEEN_CHANGE))

        time.sleep(LOCKOUT_DURATION + WAIT_BETWEEN_CHANGE)
        verify_user(user_name, current_password, is_admin=is_admin, expect_fail=False,
                    keystone=keystone)
        LOG.info('OK, {} keystone user is unlocked after {} seconds'.format(keystone,
                                                                            LOCKOUT_DURATION))

        yield


def special_char_generator():
    while True:
        (args, keystone, _), expecting_pass = yield

        password = list(get_valid_password(keystone=keystone))

        if not expecting_pass:

            special_to_letter = \
                dict(zip(SPECIAL_CHARACTERS, ascii_letters[:len(SPECIAL_CHARACTERS) + 1]))
            password = \
                ''.join(special_to_letter[c] if c in SPECIAL_CHARACTERS else c for c in password)
        else:
            while True:
                password = get_valid_password(keystone=keystone)
                if not is_last_used(password, keystone=keystone):
                    break

        yield password


def case_numerical_generator():
    while True:
        (args, keystone, _), expecting_pass = yield

        password = list(get_valid_password(keystone=keystone))

        if not expecting_pass:
            if args == 'lower':
                password = ''.join(c.upper() if c.isalpha() else c for c in password
                                   if not c.isalpha() or c.islower())
            elif args == 'upper':
                password = ''.join(c.lower() if c.isalpha() else c for c in password
                                   if not c.isalpha() or c.isupper())
            elif args == 'digit':
                digit_to_letter = dict(zip('0123456789', 'abcdefghij'))
                password = ''.join(digit_to_letter[c] if c.isdigit() else c for c in password)
            else:
                skip('Unknown args: case_numerical_generator: user_name={}, args={}, '
                     'expecting_pass={}\n'.format(keystone, args, expecting_pass))
                return

        else:
            while True:
                password = get_valid_password(keystone=keystone)
                if not is_last_used(password, keystone=keystone):
                    break

        yield password


def change_history_generator():
    while True:
        (args, keystone, _), expecting_pass = yield

        used_passwords = USED_PASSWORDS[keystone]
        if not expecting_pass:
            if args == 'not_last_2':
                password = used_passwords[0]

            elif args == '3_diff':
                previous = used_passwords[-1]
                total_to_change = random.randrange(0, 2)
                rand_indice = random.sample(range(len(previous)), total_to_change)
                new_chars = []
                for i in range(len(previous)):
                    if i in rand_indice:
                        while True:
                            new_char = random.choice(ascii_letters)
                            if new_char != previous[i]:
                                new_chars.append(new_char)
                                break
                    else:
                        new_chars.append(previous[i])
                password = ''.join(new_chars)

            elif args == 'reversed':
                password = ''.join(used_passwords[-1::-1])

            else:
                password = ''
                skip('Unknown arg:{} for change_history_generator'.format(args))

        else:
            while True:
                password = get_valid_password(keystone=keystone)
                if password not in used_passwords:
                    break

        yield password


def length_generator():
    while True:
        (args, keystone, _), expecting_pass = yield

        password = ''
        for _ in range(30):
            password = get_valid_password(keystone=keystone)

            if not expecting_pass:
                password = password[:random.randint(1, MIN_PASSWORD_LEN - 1)]
                break

            if not is_last_used(password, keystone=keystone):
                break

        yield password


def verify_user(user_name, password, is_admin=True, expect_fail=False, keystone=None):
    scenario = ' and expect failure' if expect_fail else ''
    LOG.info('Run {} OpenStack command with {} role {}'.format(
        keystone, 'admin' if is_admin else 'member', scenario))

    dict_name = '{}_platform'.format(user_name) if keystone == 'platform' else user_name
    auth_info = Tenant.get(dict_name)
    auth_info = copy.deepcopy(auth_info)
    auth_info['password'] = password
    if is_admin:
        command = 'endpoint list'
        code, output = cli.openstack(command, fail_ok=expect_fail, auth_info=auth_info)
    else:
        command = 'user show {}'.format(user_name)
        code, output = cli.openstack(command, fail_ok=expect_fail, auth_info=auth_info)

    message = 'command:{}\nauth_info:{}\noutput:{}'.format(command, auth_info, output)

    if expect_fail:
        assert 1 == code, "OpenStack command ran successfully while rejection is " \
                          "expected: {}".format(message)


def change_user_password(user_name, password, keystone, by_admin=True, expect_fail=None):
    scenario = 'Change platform keystone user password with rule {} unsatisfied'.format(
        expect_fail) if expect_fail else 'Change platform keyword user password to a valid password'

    if by_admin and expect_fail == 'not_last_used':
        scenario += ', but still allowed when operated by admin user'
        expect_fail = None

    LOG.info(scenario)

    dict_name = '{}_platform'.format(user_name) if keystone == 'platform' else user_name
    user_auth = Tenant.get(dict_name)
    original_password = user_auth['password']

    if by_admin:
        admin_auth = Tenant.get('admin_platform') if keystone == 'platform' else Tenant.get('admin')
        code, output = keystone_helper.set_user(user=user_name, password=password, project='admin',
                                                auth_info=admin_auth, fail_ok=expect_fail)
    else:
        code, output = keystone_helper.set_current_user_password(
            fail_ok=expect_fail, original_password=original_password, new_password=password,
            auth_info=user_auth)

    if code == 0:
        save_used_password(keystone, password=password)

    if expect_fail:
        assert 1 == code, "{} keystone user password change accepted unexpectedly with " \
                          "password rule violated: {}".format(keystone, password)

    LOG.info('{} keystone password change {} as expected'.format(
        keystone, 'rejected' if expect_fail else 'accepted'))

    return code, output


PASSWORD_RULE_INFO = [
    ('minimum_7_chars', (length_generator, '')),
    ('at_least_1_lower_case', (case_numerical_generator, 'lower')),
    ('at_least_1_upper_case', (case_numerical_generator, 'upper')),
    ('at_least_1_digit', (case_numerical_generator, 'digit')),
    ('at_least_1_special_case', (special_char_generator, '')),
    ('not_last_used', (change_history_generator, 'not_last_2')),
]

KEYSTONES = ['platform', 'stx-openstack']


@fixture(scope='module', params=KEYSTONES)
def create_test_user(request):
    keystone = request.param
    if keystone == 'stx-openstack' and not container_helper.is_stx_openstack_deployed():
        skip('stx-openstack is not applied')

    LOG.fixture_step("Creating {} keystone user {} for password rules testing".format(
        keystone, TEST_USER_NAME))
    auth_info = Tenant.get('admin_platform') if keystone == 'platform' else Tenant.get('admin')
    existing_users = keystone_helper.get_users(field='Name', auth_info=auth_info)
    print(existing_users, "exiting userssss")
    if TEST_USER_NAME in existing_users:
        keystone_helper.delete_users(TEST_USER_NAME, auth_info=auth_info)

    keystone_helper.create_user(name=TEST_USER_NAME, password=TEST_PASSWORD,
                                auth_info=auth_info, project='admin')
    existing_users = keystone_helper.get_users(field='Name', auth_info=auth_info)
    print(existing_users, "exiting userssss")
    save_used_password(keystone, TEST_PASSWORD)
    keystone_helper.add_or_remove_role(add_=True, role='member', user=TEST_USER_NAME,
                                       auth_info=auth_info, project='admin')

    def delete():
        LOG.fixture_step("Delete keystone test {}".format(TEST_USER_NAME))
        keystone_helper.delete_users(TEST_USER_NAME, auth_info=auth_info)

    request.addfinalizer(delete)

    return keystone


class TestKeystonePassword:
    @mark.parametrize(('role', 'scenario'), [
        ('admin_role', 'change_by_admin_user'),
        ('admin_role', 'change_by_current_user'),
        ('member_role', 'change_by_current_user'),
        ('member_role', 'change_by_admin_user'),
    ])
    def test_keystone_password_rules(self, create_test_user, role, scenario):
        """
        Test keystone password rules when attempt to change the password
        Args:
            create_test_user:
            role:
            scenario (str): operator for the password change

        Setups:
            - Create a platform/stx-openstack keystone user (class)

        Test Steps:
            - Assign member/admin role to test user
            - Ensure test user can run openstack command
            - Attempt to change the test user password using current user or the default keystone
                admin user
            - Ensure the valid password is accepted while the invalid ones are rejected

        Teardown:
            - Remove test user (class)

        """
        keystone = create_test_user
        user_name = TEST_USER_NAME
        is_admin = True if role == 'admin_role' else False
        assign_role(keystone=keystone, user_name=user_name, role=role, is_admin=is_admin)

        random.seed()
        by_admin = True if 'admin_user' in scenario else False
        for item in PASSWORD_RULE_INFO:
            rule, generator_args = item

            LOG.tc_step('Verify {} keystone password rule {} when {}'.format(
                keystone, rule, scenario))
            password_gen, args = generator_args

            password_producer = password_gen()
            password_producer.send(None)
            send_args = (args, keystone, is_admin)
            valid_pwd = password_producer.send((send_args, True))
            change_user_password(user_name, valid_pwd, by_admin=is_admin, keystone=keystone)
            verify_user(user_name, valid_pwd, is_admin=is_admin, keystone=keystone)

            next(password_producer)
            invalid_pwd = password_producer.send((send_args, False))
            wait = WAIT_BETWEEN_CHANGE + 1
            LOG.info('Wait for {} seconds to test {} violation'.format(wait, rule))
            time.sleep(wait)
            change_user_password(user_name, invalid_pwd, expect_fail=rule,
                                 by_admin=by_admin, keystone=keystone)

            LOG.info('Password rule {} verified passed'.format(rule))

    @fixture(scope='class')
    def configure_keystone_lockout(self, create_test_user):
        keystone = create_test_user
        set_keystone_lockout(keystone, lockout_duration=LOCKOUT_DURATION,
                             failure_attempts=FAILURE_ATTEMPTS)
        return keystone

    @mark.parametrize('role', [
        'admin_role',
        'member_role'
    ])
    def test_keystone_account_lockout(self, configure_keystone_lockout, role):
        """
        Test keystone password rules when attempt to change the password
        Args:
            configure_keystone_lockout:
            role:

        Setups:
            - Create a platform/stx-openstack keystone user (class)
            - Check lockout config exists in keystone.conf (class)
            - Set lockout configs to 5 failed attempts and 300 lockout duration for testing purpose

        Test Steps:
            - Assign member/admin role to test user
            - Attempt to run openstack command using incorrect passwords for 5 times
            - Check test account is locked by running openstack command using correct password
            - Wait for lockout duration
            - Check user is unlocked

        Teardown:
            - Remove test user (class)

        """
        keystone = configure_keystone_lockout
        user_name = TEST_USER_NAME
        is_admin = True if role == 'admin_role' else False
        assign_role(keystone=keystone, user_name=user_name, role=role, is_admin=is_admin)

        random.seed()
        LOG.tc_step('Set {} keystone lockout_duration to 300 and lockout_failure_attempts to 5 for '
                    'testing purpose'.format(keystone))
        set_keystone_lockout(keystone=keystone, lockout_duration=LOCKOUT_DURATION,
                             failure_attempts=5)

        LOG.tc_step('Attempt to run {} keystone command using incorrect password multiple times '
                    'and ensure account is locked out'.format(keystone))
        args = (5, keystone, is_admin, user_name)
        password_producer = multiple_attempts_generator()
        password_producer.send(None)
        password_producer.send(args)


def assign_role(keystone, user_name, role, is_admin):
    is_platform = True if keystone == 'platform' else False

    LOG.tc_step('Assign test user {} with {}'.format(user_name, role))
    admin_auth = Tenant.get('admin_platform') if is_platform else Tenant.get('admin')
    keystone_helper.add_or_remove_role(add_=is_admin, role='admin', user=user_name,
                                       auth_info=admin_auth, project='admin')

    user_dict_name = '{}_platform'.format(user_name) if is_platform else user_name
    password = Tenant.get(user_dict_name)['password']
    LOG.tc_step('Run {} OpenStack command using {}/{} and ensure it works'.format(
        keystone, user_name, password))
    verify_user(user_name, password, is_admin=is_admin, keystone=keystone)


def __set_non_platform_lockout(current_values, expt_values):
    app_name = 'stx-openstack'
    service = 'keystone'
    namespace = 'openstack'
    section = 'conf.keystone.security_compliance'
    fields = ['lockout_duration', 'lockout_failure_attempts']
    kv_pairs = {}
    for i in range(2):
        if current_values[i] != expt_values[i]:
            kv_pairs['{}.{}'.format(section, fields[i])] = expt_values[i]

    if not kv_pairs:
        LOG.info('stx-openstack keystone lockout values already set to: {}'.format(expt_values))
        return

    container_helper.update_helm_override(
        chart=service, namespace=namespace, reset_vals=False,
        kv_pairs=kv_pairs)

    override_info = container_helper.get_helm_override_values(
        chart=service, namespace=namespace, fields='user_overrides')
    LOG.debug('override_info:{}'.format(override_info))

    container_helper.apply_app(
        app_name=app_name, check_first=False, applied_timeout=1800)

    post_values = get_lockout_values(keystone='stx-openstack')
    assert expt_values == post_values, "lockout values did not set to expected after helm " \
                                       "override update"
    LOG.info('stx-openstack keystone lockout values set successfully')


def __set_platform_lockout(current_values, expt_values):
    conf_file = '/etc/keystone/keystone.conf'
    fields = ['lockout_duration', 'lockout_failure_attempts']
    con_ssh = ControllerClient.get_active_controller()
    for i in range(2):
        if current_values[i] == expt_values[i]:
            continue

        field = fields[i]
        con_ssh.exec_sudo_cmd("sed -i 's/^{}.*=.*/{} = {}/g' "
                              "{}".format(field, field, expt_values[i], conf_file), fail_ok=False)

    post_values = get_lockout_values('platform')
    assert expt_values == post_values, "platform keystone lockout values unexpected after sed"

    LOG.info("Restart platform keystone service after changing keystone config")
    con_ssh.exec_sudo_cmd('sm-restart-safe service keystone', fail_ok=False)
    time.sleep(30)


def set_keystone_lockout(keystone, lockout_duration=300, failure_attempts=5):
    current_values = get_lockout_values(keystone=keystone)
    expt_values = [lockout_duration, failure_attempts]
    if current_values == expt_values:
        return

    if keystone == 'platform':
        __set_platform_lockout(current_values, expt_values)
    else:
        __set_non_platform_lockout(current_values, expt_values)


def get_lockout_values(keystone):
    conf_file = '/etc/keystone/keystone.conf'
    fields = ['lockout_duration', 'lockout_failure_attempts']
    section = 'security_compliance'
    config_fields = {section: fields}

    LOG.info('Getting {} keystone account lockout values'.format(keystone))

    if keystone == 'platform':
        con_ssh = ControllerClient.get_active_controller()
        code, out = con_ssh.exec_sudo_cmd('grep -E "^{}|^{}" {}'.format(
            fields[0], fields[1], conf_file))
        assert code == 0, "platform keystone lockout is not configured"
        for field in fields:
            assert field in out, "platform keystone {} is not configured".format(field)

        values_dict = {}
        for line in out.splitlines():
            key, val = line.split(sep='=')
            values_dict[key.strip()] = int(val.strip())
        values = [values_dict[field] for field in fields]

    else:
        configs = kube_helper.get_openstack_configs(
            conf_file=conf_file, configs=config_fields,
            label_app='keystone', label_component='api')

        values = [(item.get(section, fields[0], fallback=None),
                   item.get(section, fields[1], fallback=None))
                  for item in list(configs.values())]

        assert len(set(values)) == 1, 'keystone conf differs in different keystone api pods'
        values = values[0]
        for value in values:
            assert value is not None, "{} keystone account lockout is not " \
                                      "configured".format(keystone)
        values = [int(val.strip()) for val in values]

    LOG.info("Lockout configs in {} keystone.conf: {}".format(keystone, values))
    return values
