from pytest import mark
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords

@mark.p0
@mark.lab_is_simplex
def test_get_hosts():
    """
    Test to validate get hosts rest call
    Test Steps:
        - call gets hosts
        - validate that only one host is found for simplex
        - validate name of the host is controller-0
    """

    system_show_output = GetHostsKeywords().get_hosts()

    hosts = system_show_output.get_all_system_host_show_objects()
    assert len(hosts) == 1
    host = system_show_output.get_system_host_show_object()
    assert host.get_hostname() == 'controller-0'

@mark.p0
@mark.lab_is_simplex
def test_get_host():
    """
    Test to validate get host rest call
    Test Steps:
        - call get hosts to get host id
        - validate the name of the host
    """

    # get the id of the host
    host_id = GetHostsKeywords().get_hosts().get_host_id()
    system_show_output = GetHostsKeywords().get_host(host_id)
    host = system_show_output.get_system_host_show_object()
    assert host.get_hostname() == 'controller-0'
