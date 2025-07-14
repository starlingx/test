from enum import Enum
import json

class OpenstackStackHeatDefaultEnum(Enum):
    KEEP_JSON = ["extra_specs"]

    PROJECT = json.dumps({
        "name": "ace_test_1",
        "description": "Ace 1 Project",
        "quota": {
            "network": 8,
            "subnet": 18,
            "port": 83,
            "floatingip": 10,
            "instances": 10,
            "cores": 30,
            "volumes": 12,
            "snapshots": 12
        }
    })
    USER = json.dumps({
        "name": "ace_user_1",
        "password": "password",
        "email": "ace_user_1@noreply.com",
        "default_project": "ace_test_1"
    })
    ROLE_ASSIGNMENT = json.dumps({
        "name": "ace_one_admin_ace_test_1",
        "role": "admin",
        "project": "ace_test_1",
        "user": "ace_one"
    })
    FLAVOR = json.dumps({
        "name": "ace_small",
        "ram": 1024,
        "disk": 2,
        "vcpus": 1,
        "extra_specs": {
            "hw:mem_page_size": "large"
        }
    })
    WEBIMAGE = json.dumps({
        "name": "ace_cirros",
        "container_format": "bare",
        "disk_format": "raw",
        "location": "http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img",
        "min_disk": 0,
        "min_ram": 0,
        "visibility": "public"
    })
    QOS = json.dumps({
        "name": "external-qos",
        "description": "External Network Policy",
        "project_name": "",
        "max_kbps": "10000",
        "max_burst_kbps": "1000",
        "dscp_mark": "16"
    })
    NETWORK_SEGMENT = json.dumps({
        "name": "ace0-ext0-r0-0",
        "network_type": "vlan",
        "physical_network": "group0",
        "minimum_range": "10",
        "maximum_range": "10",
        "shared": "true",
        "private": "false",
        "project_name": ""
    })
    NETWORK = json.dumps({
        "name": "external-net0",
        "subnet_name": "external-subnet0",
        "project_name": "admin",
        "qos_policy_name": "external-qos",
        "provider_network_type": "vlan",
        "provider_physical_network": "group0-ext0",
        "shared": "true",
        "external": "true",
        "gateway_ip": "10.10.85.1",
        "enable_dhcp": "false",
        "subnet_range": "10.10.85.0/24",
        "ip_version": "4",
        "allocation_pool_start": "",
        "allocation_pool_end": ""
    })
