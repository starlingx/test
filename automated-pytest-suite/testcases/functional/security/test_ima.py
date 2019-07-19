#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, fixture, skip

from consts.auth import HostLinuxUser
from consts.stx import EventLogID
from keywords import system_helper, common
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG

files_to_delete = []


@fixture(scope='module', autouse=True)
def ima_precheck():
    """
    This tests if the system is enabled with IMA.  If not, we
    should skip IMA-related tests.
    """

    LOG.info("Checking if IMA is enabled")
    con_ssh = ControllerClient.get_active_controller()

    exitcode, output = con_ssh.exec_cmd("cat /proc/cmdline")
    if "extended" not in output:
        skip("IMA must be enabled in order to run this test")
    else:
        LOG.info("IMA is enabled")


@fixture(autouse=True)
def delete_files(request):
    global files_to_delete
    files_to_delete = []

    def teardown():
        """
        Delete any created files on teardown.
        """
        for filename in files_to_delete:
            delete_file(filename)

    request.addfinalizer(teardown)


def checksum_compare(source_file, dest_file):
    """
    This does a checksum comparison of two files.  It returns True if the
    checksum matches, and False if it doesn't.
    """

    con_ssh = ControllerClient.get_active_controller()

    LOG.info("Compare checksums on source file and destination file")
    cmd = "getfattr -m . -d {}"

    exitcode, source_sha = con_ssh.exec_cmd(cmd.format(source_file))
    LOG.info("Raw source file checksum is: {}".format(source_sha))
    source_sha2 = source_sha.split("\n")
    print("This is source_sha2: {}".format(source_sha2))
    assert source_sha2 != [''], "No signature on source file"

    if source_file.startswith("/"):
        source_sha = source_sha2[2] + " " + source_sha2[3]
    else:
        source_sha = source_sha2[1] + " " + source_sha2[2]

    LOG.info("Extracted source file checksum: {}".format(source_sha))

    exitcode, dest_sha = con_ssh.exec_cmd(cmd.format(dest_file))
    LOG.info("Raw symlink checksum is: {}".format(dest_sha))
    dest_sha2 = dest_sha.split("\n")

    if dest_file.startswith("/"):
        dest_sha = dest_sha2[2] + " " + dest_sha2[3]
    else:
        dest_sha = dest_sha2[1] + " " + dest_sha2[2]

    LOG.info("Extracted destination file checksum: {}".format(dest_sha))

    if source_sha == dest_sha:
        return True
    else:
        return False


def create_symlink(source_file, dest_file, sudo=True):
    """
    This creates a symlink given a source filename and a destination filename.
    """
    LOG.info("Creating symlink to {} called {}".format(source_file, dest_file))
    cmd = "ln -sf {} {}".format(source_file, dest_file)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def delete_file(filename, sudo=True):
    """
    This deletes a file.
    """
    LOG.info("Deleting file {}".format(filename))
    cmd = "rm {}".format(filename)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def chmod_file(filename, permissions, sudo=True):
    """
    This modifies permissions of a file
    """
    LOG.info("Changing file permissions for {}".format(filename))
    cmd = "chmod {} {}".format(permissions, filename)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def chgrp_file(filename, group, sudo=True):
    """
    This modifies the group ownership of a file
    """
    LOG.info("Changing file permissions for {}".format(filename))
    cmd = "chgrp {} {}".format(group, filename)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def chown_file(filename, file_owner, sudo=True):
    """
    This modifies the user that owns the file
    """
    LOG.info("Changing the user that owns {}".format(filename))
    cmd = "chown {} {}".format(file_owner, filename)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def copy_file(source_file, dest_file, sudo=True, preserve=True, cleanup=None):
    """
    This creates a copy of a file

    Args:
        source_file:
        dest_file:
        sudo (bool): whether to copy with sudo
        cleanup (None|str): source or dest. Add source or dest file to files to
            delete list
        preserve (bool): whether to preserve attributes of source file

    Returns:

    """
    LOG.info("Copy file {} preserve attributes".format('and' if preserve
                                                       else 'without'))
    preserve_str = '--preserve=all ' if preserve else ''
    cmd = "cp {} {}{}".format(source_file, preserve_str, dest_file)
    _exec_cmd(cmd, sudo=sudo, fail_ok=False)

    if cleanup:
        file_path = source_file if cleanup == 'source' else dest_file
        files_to_delete.append(file_path)


def move_file(source_file, dest_file, sudo=True):
    """
    This moves a file from source to destination
    """
    LOG.info("Copy file and preserve attributes")
    cmd = "mv {} {}".format(source_file, dest_file)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)


def create_and_execute(file_path, sudo=True):
    LOG.tc_step("Create a new {} file and execute it".format('root' if sudo
                                                             else 'non-root'))
    cmd = "touch {}".format(file_path)
    _exec_cmd(cmd=cmd, sudo=sudo, fail_ok=False)
    files_to_delete.append(file_path)

    LOG.info("Set file to be executable")
    chmod_file(file_path, "755", sudo=sudo)

    LOG.info("Append to copy of monitored file")
    cmd = 'echo "ls" | {}tee -a {}'.format('sudo -S ' if sudo else '',
                                           file_path)
    _exec_cmd(cmd=cmd, sudo=False, fail_ok=False)

    LOG.info("Execute created file")
    _exec_cmd(file_path, sudo=sudo, fail_ok=False)


@mark.priorities('nightly', 'sx_nightly')
@mark.parametrize(('operation', 'file_path'), [
    ('create_symlink', '/usr/sbin/ntpq'),
    ('copy_and_execute', '/usr/sbin/ntpq'),
    ('change_file_attributes', '/usr/sbin/ntpq'),
    ('create_and_execute', 'new_nonroot_file')
])
def test_ima_no_event(operation, file_path):
    """
    This test validates following scenarios will not generate IMA event:
        - create symlink of a monitored file
        - copy a root file with the proper IMA signature, the nexcute it
        - make file attribute changes, include: chgrp, chown, chmod
        - create and execute a files as sysadmin

    Test Steps:
        - Perform specified operation on given file
        - Confirm IMA violation event is not triggered

    Teardown:
        - Delete created test file

    Maps to TC_17684/TC_17644/TC_17640/TC_17902 from US105523
    This test also covers TC_17665/T_16397 from US105523 (FM Event Log Updates)

    """


    global files_to_delete
    start_time = common.get_date_in_format()
    source_file = file_path
    con_ssh = ControllerClient.get_active_controller()

    LOG.tc_step("{} for {}".format(operation, source_file))
    if operation == 'create_symlink':
        dest_file = "my_symlink"
        create_symlink(source_file, dest_file)
        files_to_delete.append(dest_file)

        checksum_match = checksum_compare(source_file, dest_file)
        assert checksum_match, "SHA256 checksum should match source file and " \
                               "the symlink but didn't"

    elif operation == 'copy_and_execute':
        dest_file = "/usr/sbin/TEMP"
        copy_file(source_file, dest_file)
        files_to_delete.append(dest_file)

        LOG.info("Execute the copied file")
        con_ssh.exec_sudo_cmd("{} -p".format(dest_file))

    elif operation == 'change_file_attributes':
        if HostLinuxUser.get_home() != 'sysadmin':
            skip('sysadmin user is required to run this test')
        dest_file = "/usr/sbin/TEMP"
        copy_file(source_file, dest_file)
        files_to_delete.append(dest_file)

        LOG.info("Change permission of copy")
        chmod_file(dest_file, "777")
        LOG.info("Changing group ownership of file")
        chgrp_file(dest_file, "sys_protected")
        LOG.info("Changing file ownership")
        chown_file(dest_file, "sysadmin:sys_protected")

    elif operation == 'create_and_execute':
        dest_file = "{}/TEMP".format(HostLinuxUser.get_home())
        create_and_execute(file_path=dest_file, sudo=False)

    LOG.tc_step("Ensure no IMA events are raised")
    events_found = system_helper.wait_for_events(start=start_time,
                                                 timeout=60, num=10,
                                                 event_log_id=EventLogID.IMA,
                                                 fail_ok=True, strict=False)

    assert not events_found, "Unexpected IMA events found"


def _exec_cmd(cmd, con_ssh=None, sudo=False, fail_ok=True):
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    if sudo:
        return con_ssh.exec_sudo_cmd(cmd, fail_ok=fail_ok)
    else:
        return con_ssh.exec_cmd(cmd, fail_ok=fail_ok)


@mark.priorities('nightly', 'sx_nightly')
@mark.parametrize(('operation', 'file_path'), [
    ('edit_and_execute', '/usr/sbin/ntpq'),
    ('append_and_execute', '/usr/sbin/logrotate'),
    ('replace_library', '/lib64/libcrypt.so.1'),
    ('create_and_execute', 'new_root_file')
])
def test_ima_event_generation(operation, file_path):
    """
    Following IMA violation scenarios are covered:
        - append/edit data to/of a monitored file, result in changing of the
            hash
        - dynamic library changes
        - create and execute a files as sysadmin

    Test Steps:
    - Perform specified file operations
    - Check IMA violation event is logged

    """
    global files_to_delete

    con_ssh = ControllerClient.get_active_controller()
    start_time = common.get_date_in_format()

    source_file = file_path
    backup_file = None

    if operation in ('edit_and_execute', 'append_and_execute'):
        dest_file = "/usr/sbin/TEMP"
        copy_file(source_file, dest_file, cleanup='dest')

        if operation == 'edit_and_execute':
            LOG.tc_step("Open copy of monitored file and save")
            cmd = "vim {} '+:wq!'".format(dest_file)
            con_ssh.exec_sudo_cmd(cmd, fail_ok=False)
            execute_cmd = "{} -p".format(dest_file)
        else:
            LOG.tc_step("Append to copy of monitored file")
            cmd = 'echo "output" | sudo -S tee -a /usr/sbin/TEMP'.format(
                HostLinuxUser.get_password())
            con_ssh.exec_cmd(cmd, fail_ok=False)
            LOG.tc_step("Execute modified file")
            con_ssh.exec_sudo_cmd(dest_file)
            execute_cmd = "{}".format(dest_file)

        LOG.tc_step("Execute modified file")
        con_ssh.exec_sudo_cmd(execute_cmd)

    elif operation == 'replace_library':
        backup_file = "/root/{}".format(source_file.split('/')[-1])
        dest_file_nocsum = "/root/TEMP"

        LOG.info("Backup source file {} to {}".format(source_file, backup_file))
        copy_file(source_file, backup_file)
        LOG.info("Copy the library without the checksum")
        copy_file(source_file, dest_file_nocsum, preserve=False)
        LOG.info("Replace the library with the unsigned one")
        move_file(dest_file_nocsum, source_file)

    elif operation == 'create_and_execute':
        dest_file = "{}/TEMP".format(HostLinuxUser.get_home())
        create_and_execute(file_path=dest_file, sudo=True)

    LOG.tc_step("Check for IMA event")
    ima_events = system_helper.wait_for_events(start=start_time,
                                               timeout=60, num=10,
                                               event_log_id=EventLogID.IMA,
                                               state='log', severity='major',
                                               fail_ok=True, strict=False)

    if backup_file:
        LOG.info("Restore backup file {} to {}".format(backup_file,
                                                       source_file))
        move_file(backup_file, source_file)

    assert ima_events, "IMA event is not generated after {} on " \
                       "{}".format(operation, file_path)


# CHECK TEST PROCEDURE - FAILS in the middle


@mark.priorities('nightly', 'sx_nightly')
def test_ima_keyring_protection():
    """
    This test validates that the IMA keyring is safe from user space attacks.

    Test Steps:
    - Attempt to add new keys to the keyring
    - Extract key ID and save
    - Attempt to change the key timeout
    - Attempt to change the group and ownership of the key
    - Attempt to delete the key

    This test maps to TC_17667/T_16387 from US105523 (IMA keyring is safe from
    user space attacks)

    """

    con_ssh = ControllerClient.get_active_controller()

    LOG.info("Extract ima key ID")
    exitcode, msg = con_ssh.exec_sudo_cmd("cat /proc/keys | grep _ima")
    raw_key_id = msg.split(" ", maxsplit=1)[0]
    key_id = "0x{}".format(raw_key_id)
    LOG.info("Extracted key is: {}".format(key_id))

    LOG.info("Attempting to add new keys to keyring")
    exitcode, msg = con_ssh.exec_sudo_cmd("keyctl add keyring TEST stuff "
                                          "{}".format(key_id))
    assert exitcode != 0, \
        "Key addition should have failed but instead succeeded"

    LOG.info("Attempt to change the timeout on a key")
    exitcode, msg = con_ssh.exec_sudo_cmd("keyctl timeout {} "
                                          "3600".format(key_id))
    assert exitcode != 0, \
        "Key timeout modification should be rejected but instead succeeded"

    LOG.info("Attempt to change the group of a key")
    exitcode, msg = con_ssh.exec_sudo_cmd("keyctl chgrp {} 0".format(key_id))
    assert exitcode != 0, \
        "Key group modification should be rejected but instead succeeded"

    LOG.info("Attempt to change the ownership of a key")
    exitcode, msg = con_ssh.exec_sudo_cmd("keyctl chown {} 1875".format(key_id))
    assert exitcode != 0, \
        "Key ownership modification should be rejected but instead succeeded"

    LOG.info("Attempt to delete a key")
    exitcode, msg = con_ssh.exec_sudo_cmd("keyctl clear {}".format(key_id))
    assert exitcode != 0, \
        "Key ownership deletion should be rejected but instead succeeded"
