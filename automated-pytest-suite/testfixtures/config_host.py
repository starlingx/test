from pytest import fixture, mark

from utils.tis_log import LOG
from keywords import host_helper
from testfixtures.recover_hosts import HostsToRecover


@mark.tryfirst
@fixture(scope='module')
def config_host_module(request):
    """
    Module level fixture to configure a host.

    Setup:
        - Lock a host
        - Configure host
        - Unlock host

    Teardown (if revert_func is given):
        - Lock host
        - Run revert_func
        - Unlock host

    Args:
        request: pytest param. caller of this func.

    Returns (function): config_host_func.
        Test or another fixture can execute it to pass the hostname,
        modify_func, and revert_func

    Examples:
        see 'add_shared_cpu' fixture in nova/test_shared_cpu.py for usage.

    """
    return __config_host_base(scope='module', request=request)


@mark.tryfirst
@fixture(scope='class')
def config_host_class(request):
    """
    Class level fixture to configure a host.

    Setup:
        - Lock a host
        - Configure host
        - Unlock host

    Teardown (if revert_func is given):
        - Lock host
        - Run revert_func
        - Unlock host

    Args:
        request: pytest param. caller of this func.

    Returns (function): config_host_func.
        Test or another fixture can execute it to pass the hostname,
        modify_func, and revert_func

    Examples:
        see 'add_shared_cpu' fixture in nova/test_shared_cpu.py for usage.

    """
    return __config_host_base(scope='class', request=request)


def __config_host_base(scope, request):

    def config_host_func(host, modify_func, revert_func=None, *args, **kwargs):

        HostsToRecover.add(host, scope=scope)
        LOG.fixture_step("({}) Lock host: {}".format(scope, host))
        host_helper.lock_host(host=host, swact=True)

        # add teardown before running modify (as long as host is locked
        # successfully) in case modify or unlock fails.
        if revert_func is not None:
            def revert_host():
                LOG.fixture_step("({}) Lock host: {}".format(scope, host))
                host_helper.lock_host(host=host, swact=True)
                try:
                    LOG.fixture_step("({}) Execute revert function: {}".format(
                        scope, revert_func))
                    revert_func(host)
                finally:
                    LOG.fixture_step("({}) Unlock host: {}".format(scope, host))
                    # Put it in finally block in case revert_func fails -
                    # host will still be unlocked for other tests.
                    host_helper.unlock_host(host=host)

            request.addfinalizer(revert_host)

        LOG.fixture_step("({}) Execute modify function: {}".format(
            scope, modify_func))
        modify_func(host, *args, **kwargs)

        LOG.fixture_step("({}) Unlock host: {}".format(scope, host))
        host_helper.unlock_host(host=host)

    return config_host_func
