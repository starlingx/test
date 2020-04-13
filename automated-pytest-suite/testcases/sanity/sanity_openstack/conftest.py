from pytest import fixture

from keywords import network_helper

NETWORK_NAME = "network-1"
SUBNET_NAME = "subnet"
SUBNET_RANGE = "192.168.0.0/24"
IP_VERSION = 4

@fixture(scope="module")
def create_network_sanity():
    """
    Create network and subnetwork used in sanity_openstack tests
    """
    net_id = network_helper.create_network(name=NETWORK_NAME, cleanup="module")[1]
    subnet_id = network_helper.create_subnet(name=SUBNET_NAME, network=NETWORK_NAME,
                                             subnet_range=SUBNET_RANGE, dhcp=True,
                                             ip_version=IP_VERSION, cleanup="module")[1]
    return net_id, subnet_id
