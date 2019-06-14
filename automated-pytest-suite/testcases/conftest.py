import pytest

import setups
from consts.auth import CliAuth, Tenant
from consts.proj_vars import ProjVar
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient

natbox_ssh = None
initialized = False


@pytest.fixture(scope='session', autouse=True)
def setup_test_session(global_setup):
    """
    Setup primary tenant and Nax Box ssh before the first test gets executed.
    STX ssh was already set up at collecting phase.
    """
    LOG.fixture_step("(session) Setting up test session...")
    setups.setup_primary_tenant(ProjVar.get_var('PRIMARY_TENANT'))

    global con_ssh
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    # set build id to be used to upload/write test results
    setups.set_build_info(con_ssh)

    # Ensure tis and natbox (if applicable) ssh are connected
    con_ssh.connect(retry=True, retry_interval=3, retry_timeout=300)

    # set up natbox connection and copy keyfile
    natbox_dict = ProjVar.get_var('NATBOX')
    global natbox_ssh
    natbox_ssh = setups.setup_natbox_ssh(natbox_dict, con_ssh=con_ssh)

    # set global var for sys_type
    setups.set_sys_type(con_ssh=con_ssh)

    # rsync files between controllers
    setups.copy_test_files()


def pytest_collectstart():
    """
    Set up the ssh session at collectstart. Because skipif condition is
    evaluated at the collecting test cases phase.
    """
    global initialized
    if not initialized:
        global con_ssh
        con_ssh = setups.setup_tis_ssh(ProjVar.get_var("LAB"))
        ProjVar.set_var(con_ssh=con_ssh)
        CliAuth.set_vars(**setups.get_auth_via_openrc(con_ssh))
        if setups.is_https(con_ssh):
            CliAuth.set_vars(HTTPS=True)

        auth_url = CliAuth.get_var('OS_AUTH_URL')
        Tenant.set_platform_url(auth_url)
        setups.set_region(region=None)
        if ProjVar.get_var('IS_DC'):
            Tenant.set_platform_url(url=auth_url, central_region=True)
        initialized = True


def pytest_runtest_teardown():
    for con_ssh_ in ControllerClient.get_active_controllers(
            current_thread_only=True):
        con_ssh_.flush()
        con_ssh_.connect(retry=True, retry_interval=3, retry_timeout=300)
    if natbox_ssh:
        natbox_ssh.flush()
        natbox_ssh.connect(retry=False)
