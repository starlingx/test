#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import time

from pytest import fixture, skip

from consts.auth import Tenant
from consts.stx import EventLogID, HostAvailState, AppStatus
from consts.reasons import SkipSysType
from keywords import system_helper, host_helper, keystone_helper, \
    security_helper, container_helper, kube_helper
from utils.tis_log import LOG


@fixture(scope='function')
def stx_openstack_applied_required(request):
    app_name = 'stx-openstack'
    if not container_helper.is_stx_openstack_deployed(applied_only=True):
        skip('stx-openstack application is not applied')

    def wait_for_recover():

        post_status = container_helper.get_apps(application=app_name)[0]
        if not post_status == AppStatus.APPLIED:
            LOG.info("Dump info for unhealthy pods")
            kube_helper.dump_pods_info()

            if not post_status.endswith('ed'):
                LOG.fixture_step("Wait for application apply finish")
                container_helper.wait_for_apps_status(apps=app_name,
                                                      status=AppStatus.APPLIED,
                                                      timeout=3600,
                                                      check_interval=15,
                                                      fail_ok=False)

    request.addfinalizer(wait_for_recover)


@fixture(scope='module')
def stx_openstack_required():
    if not container_helper.is_stx_openstack_deployed():
        skip('stx-openstack application is not deployed')


@fixture(scope='session')
def skip_for_one_proc():
    hypervisor = host_helper.get_up_hypervisors()
    if not hypervisor:
        skip("No up hypervisor on system.")

    if len(host_helper.get_host_procs(hostname=hypervisor[0])) < 2:
        skip(
            'At least two processor per compute host is required for this '
            'test.')


@fixture(scope='session')
def no_simplex():
    LOG.fixture_step("(Session) Skip if Simplex")
    if system_helper.is_aio_simplex():
        skip(SkipSysType.SIMPLEX_SYSTEM)


@fixture(scope='session')
def simplex_only():
    LOG.fixture_step("(Session) Skip if not Simplex")
    if not system_helper.is_aio_simplex():
        skip(SkipSysType.SIMPLEX_ONLY)


@fixture(scope='session')
def check_numa_num():
    hypervisor = host_helper.get_up_hypervisors()
    if not hypervisor:
        skip("No up hypervisor on system.")

    return len(host_helper.get_host_procs(hostname=hypervisor[0]))


@fixture(scope='session')
def wait_for_con_drbd_sync_complete():
    if len(system_helper.get_controllers()) < 2:
        LOG.info(
            "Less than two controllers on system. Do not wait for drbd sync")
        return False

    host = 'controller-1'
    LOG.fixture_step("Waiting for controller-1 drbd sync alarm gone if present")
    end_time = time.time() + 1200
    while time.time() < end_time:
        drbd_alarms = system_helper.get_alarms(
            alarm_id=EventLogID.CON_DRBD_SYNC, reason_text='drbd-',
            entity_id=host, strict=False)

        if not drbd_alarms:
            LOG.info("{} drbd sync alarm is cleared".format(host))
            break
        time.sleep(10)

    else:
        assert False, "drbd sync alarm {} is not cleared within timeout".format(
            EventLogID.CON_DRBD_SYNC)

    LOG.fixture_step(
        "Wait for {} becomes available in system host-list".format(host))
    system_helper.wait_for_host_values(host,
                                       availability=HostAvailState.AVAILABLE,
                                       timeout=120, fail_ok=False,
                                       check_interval=10)

    LOG.fixture_step(
        "Wait for {} drbd-cinder in sm-dump to reach desired state".format(
            host))
    host_helper.wait_for_sm_dump_desired_states(host, 'drbd-', strict=False,
                                                timeout=30, fail_ok=False)
    return True


@fixture(scope='session')
def change_admin_password_session(request, wait_for_con_drbd_sync_complete):
    more_than_one_controllers = wait_for_con_drbd_sync_complete
    prev_pswd = Tenant.get('admin')['password']
    post_pswd = '!{}9'.format(prev_pswd)

    LOG.fixture_step(
        '(Session) Changing admin password to {}'.format(post_pswd))
    keystone_helper.set_user('admin', password=post_pswd)

    def _lock_unlock_controllers():
        LOG.fixture_step("Sleep for 300 seconds after admin password change")
        time.sleep(300)
        if more_than_one_controllers:
            active, standby = system_helper.get_active_standby_controllers()
            if standby:
                LOG.fixture_step(
                    "(Session) Locking unlocking controllers to complete "
                    "action")
                host_helper.lock_host(standby)
                host_helper.unlock_host(standby)

                host_helper.lock_host(active, swact=True)
                host_helper.unlock_host(active)
            else:
                LOG.warning(
                    "Standby controller unavailable. Skip lock unlock "
                    "controllers post admin password change.")
        elif system_helper.is_aio_simplex():
            LOG.fixture_step(
                "(Session) Simplex lab - lock/unlock controller to complete "
                "action")
            host_helper.lock_host('controller-0', swact=False)
            host_helper.unlock_host('controller-0')

    def revert_pswd():
        LOG.fixture_step(
            "(Session) Reverting admin password to {}".format(prev_pswd))
        keystone_helper.set_user('admin', password=prev_pswd)
        _lock_unlock_controllers()

        LOG.fixture_step(
            "(Session) Check admin password is reverted to {} in "
            "keyring".format(prev_pswd))
        assert prev_pswd == security_helper.get_admin_password_in_keyring()

    request.addfinalizer(revert_pswd)

    _lock_unlock_controllers()

    LOG.fixture_step(
        "(Session) Check admin password is changed to {} in keyring".format(
            post_pswd))
    assert post_pswd == security_helper.get_admin_password_in_keyring()

    return post_pswd
