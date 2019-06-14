#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from consts.proj_vars import ProjVar

# output of date. such as: Tue Mar  1 18:20:29 UTC 2016
DATE_OUTPUT = r'[0-2]\d:[0-5]\d:[0-5]\d\s[A-Z]{3,}\s\d{4}$'

EXT_IP = '8.8.8.8'

# such as in string '5 packets transmitted, 0 received, 100% packet loss,
# time 4031ms', number 100 will be found
PING_LOSS_RATE = r'\, (\d{1,3})\% packet loss\,'

# vshell ping loss rate pattern. 3 packets transmitted, 0 received, 0 total,
# 100.00%% loss
VSHELL_PING_LOSS_RATE = r'\, (\d{1,3}).\d{1,2}[%]% loss'

# Matches 8-4-4-4-12 hexadecimal digits. Lower case only
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

# Match name and uuid.
# Such as: 'ubuntu_14 (a764c205-eb82-4f18-bda6-6c8434223eb5)'
NAME_UUID = r'(.*) \((' + UUID + r')\)'

# Message to indicate boot from volume from nova show
BOOT_FROM_VOLUME = 'Attempt to boot from volume - no image supplied'

METADATA_SERVER = '169.254.169.254'

# Heat template path
HEAT_PATH = 'heat/hot/simple/'
HEAT_SCENARIO_PATH = 'heat/hot/scenarios/'
HEAT_FLAVORS = ['small_ded', 'small_float']
HEAT_CUSTOM_TEMPLATES = 'custom_heat_templates'

# special NIC patterns
MELLANOX_DEVICE = 'MT27500|MT27710'
MELLANOX4 = 'MT.*ConnectX-4'

PLATFORM_AFFINE_INCOMPLETE = '/etc/platform/.task_affining_incomplete'
PLATFORM_CONF_PATH = '/etc/platform/platform.conf'

SUBCLOUD_PATTERN = 'subcloud'

PLATFORM_NET_TYPES = ('mgmt', 'oam', 'infra', 'pxeboot')

TIMEZONES = [
    "Asia/Hong_Kong",  # UTC+8
    "America/Los_Angeles",  # UTC-8, DST:UTC-7
    "Canada/Eastern",  # UTC-5, DST:UTC-4
    "Canada/Central",  # UTC-6, DST:UTC-5
    # "Europe/London",      # UTC, DST:UTC+1
    "Europe/Berlin",  # UTC+1, DST:UTC+2
    "UTC"
]

STORAGE_AGGREGATE = {
    # 'local_lvm' : 'local_storage_lvm_hosts',
    'local_image': 'local_storage_image_hosts',
    'remote': 'remote_storage_hosts',
}


class NtpPool:
    NTP_POOL_1 = '2.pool.ntp.org,1.pool.ntp.org,0.pool.ntp.org'
    NTP_POOL_2 = '1.pool.ntp.org,2.pool.ntp.org,2.pool.ntp.org'
    NTP_POOL_3 = '3.ca.pool.ntp.org,2.ca.pool.ntp.org,1.ca.pool.ntp.org'
    NTP_POOL_TOO_LONG = '3.ca.pool.ntp.org,2.ca.pool.ntp.org,' \
                        '1.ca.pool.ntp.org,1.com,2.com,3.com'
    NTP_NAME_TOO_LONG = 'garbage_' * 30


class GuestImages:
    TMP_IMG_DIR = '/opt/backups'
    DEFAULT = {
        'image_dir': '{}/images'.format(ProjVar.get_var('USER_FILE_DIR')),
        'image_dir_file_server': '/sandbox/images',
        'guest': 'tis-centos-guest'
    }
    TIS_GUEST_PATTERN = 'cgcs-guest|tis-centos-guest'
    GUESTS_NO_RM = ['ubuntu_14', 'tis-centos-guest', 'cgcs-guest']
    # Image files name and size from TestFileServer
    # <glance_image_name>: <source_file_name>, <root disk size>,
    # <dest_file_name>, <disk_format>, <container_format>
    IMAGE_FILES = {
        'ubuntu_14': (
            'ubuntu-14.04-server-cloudimg-amd64-disk1.img', 3,
            'ubuntu_14.qcow2', 'qcow2', 'bare'),
        'ubuntu_12': (
            'ubuntu-12.04-server-cloudimg-amd64-disk1.img', 8,
            'ubuntu_12.qcow2', 'qcow2', 'bare'),
        'ubuntu_16': (
            'ubuntu-16.04-xenial-server-cloudimg-amd64-disk1.img', 8,
            'ubuntu_16.qcow2', 'qcow2', 'bare'),
        'centos_6': (
            'CentOS-6.8-x86_64-GenericCloud-1608.qcow2', 8,
            'centos_6.qcow2', 'qcow2', 'bare'),
        'centos_7': (
            'CentOS-7-x86_64-GenericCloud.qcow2', 8,
            'centos_7.qcow2', 'qcow2', 'bare'),
        'rhel_6': (
            'rhel-6.5-x86_64.qcow2', 11, 'rhel_6.qcow2', 'qcow2', 'bare'),
        'rhel_7': (
            'rhel-7.2-x86_64.qcow2', 11, 'rhel_7.qcow2', 'qcow2', 'bare'),
        'opensuse_11': (
            'openSUSE-11.3-x86_64.qcow2', 11,
            'opensuse_11.qcow2', 'qcow2', 'bare'),
        'opensuse_12': (
            'openSUSE-12.3-x86_64.qcow2', 21,
            'opensuse_12.qcow2', 'qcow2', 'bare'),
        'opensuse_13': (
            'openSUSE-13.2-OpenStack-Guest.x86_64-0.0.10-Build2.94.qcow2', 16,
            'opensuse_13.qcow2', 'qcow2', 'bare'),
        'win_2012': (
            'win2012r2_cygwin_compressed.qcow2', 13,
            'win2012r2.qcow2', 'qcow2', 'bare'),
        'win_2016': (
            'win2016_cygwin_compressed.qcow2', 29,
            'win2016.qcow2', 'qcow2', 'bare'),
        'ge_edge': (
            'edgeOS.hddirect.qcow2', 5,
            'ge_edge.qcow2', 'qcow2', 'bare'),
        'cgcs-guest': (
            'cgcs-guest.img', 1, 'cgcs-guest.img', 'raw', 'bare'),
        'vxworks': (
            'vxworks-tis.img', 1, 'vxworks.img', 'raw', 'bare'),
        'tis-centos-guest': (
            None, 2, 'tis-centos-guest.img', 'raw', 'bare'),
        'tis-centos-guest-rt': (
            None, 2, 'tis-centos-guest-rt.img', 'raw', 'bare'),
        'tis-centos-guest-qcow2': (
            None, 2, 'tis-centos-guest.qcow2', 'qcow2', 'bare'),
        'centos_gpu': (
            'centos-67-cloud-gpu.img', 8,
            'centos_6_gpu.qcow2', 'qcow2', 'bare'),
        'debian-8-m-agent': (
            'debian-8-m-agent.qcow2', 1.8,
            'debian-8-m-agent.qcow2', 'qcow2', 'bare'),
        'trusty_uefi': (
            'trusty-server-cloudimg-amd64-uefi1.img', 2.2,
            'trusty-uefi.qcow2', 'qcow2', 'bare'),
        'uefi_shell': (
            'uefi_shell.iso', 2, 'uefi_shell.iso', 'raw', 'bare'),
    }


class Networks:
    INFRA_NETWORK_CIDR = "192.168.205.0/24"
    IPV4_IP = r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}'

    __NEUTRON_NET_NAME_PATTERN = {
        'mgmt': r'tenant\d-mgmt-net',
        'data': r'tenant\d-net',
        'internal': 'internal',
        'external': 'external',
    }
    __NEUTRON_NET_IP_PATTERN = {
        'data': r'172.\d{1,3}.\d{1,3}.\d{1,3}',
        'mgmt': r'192.168.\d{3}\.\d{1,3}|192.168.[8|9]\d\.\d{1,3}',
        'internal': r'10.\d{1,3}.\d{1,3}.\d{1,3}',
        'external': r'192.168.\d\.\d{1,3}|192.168.[1-5]\d\.\d{1,3}|10.10.\d{'
                    r'1,3}\.\d{1,3}'
    }

    @classmethod
    def get_nenutron_net_patterns(cls, net_type='mgmt'):
        return cls.__NEUTRON_NET_NAME_PATTERN.get(
            net_type), cls.__NEUTRON_NET_IP_PATTERN.get(net_type)

    @classmethod
    def set_neutron_net_patterns(cls, net_type, net_name_pattern=None,
                                 net_ip_pattern=None):
        if net_type not in cls.__NEUTRON_NET_NAME_PATTERN:
            raise ValueError("Unknown net_type {}. Select from: {}".format(
                net_type, list(cls.__NEUTRON_NET_NAME_PATTERN.keys())))

        if net_name_pattern is not None:
            cls.__NEUTRON_NET_NAME_PATTERN[net_type] = net_name_pattern
        if net_ip_pattern is not None:
            cls.__NEUTRON_NET_IP_PATTERN[net_type] = net_ip_pattern


class SystemType:
    CPE = 'All-in-one'
    STANDARD = 'Standard'


class StorageAggregate:
    LOCAL_LVM = 'local_storage_lvm_hosts'
    LOCAL_IMAGE = 'local_storage_image_hosts'
    REMOTE = 'remote_storage_hosts'


class VMStatus:
    # under http://docs.openstack.org/developer/nova/vmstates.html
    ACTIVE = 'ACTIVE'
    BUILD = 'BUILDING'
    REBUILD = 'REBUILD'
    VERIFY_RESIZE = 'VERIFY_RESIZE'
    RESIZE = 'RESIZED'
    ERROR = 'ERROR'
    SUSPENDED = 'SUSPENDED'
    PAUSED = 'PAUSED'
    NO_STATE = 'NO STATE'
    HARD_REBOOT = 'HARD REBOOT'
    SOFT_REBOOT = 'REBOOT'
    STOPPED = "SHUTOFF"
    MIGRATING = 'MIGRATING'


class ImageStatus:
    QUEUED = 'queued'
    ACTIVE = 'active'
    SAVING = 'saving'


class HostAdminState:
    UNLOCKED = 'unlocked'
    LOCKED = 'locked'


class HostOperState:
    ENABLED = 'enabled'
    DISABLED = 'disabled'


class HostAvailState:
    DEGRADED = 'degraded'
    OFFLINE = 'offline'
    ONLINE = 'online'
    AVAILABLE = 'available'
    FAILED = 'failed'
    POWER_OFF = 'power-off'


class HostTask:
    BOOTING = 'Booting'
    REBOOTING = 'Rebooting'
    POWERING_ON = 'Powering-on'
    POWER_CYCLE = 'Critical Event Power-Cycle'
    POWER_DOWN = 'Critical Event Power-Down'


class Prompt:
    CONTROLLER_0 = r'.*controller\-0[:| ].*\$'
    CONTROLLER_1 = r'.*controller\-1[:| ].*\$'
    CONTROLLER_PROMPT = r'.*controller\-[01][:| ].*\$ '

    VXWORKS_PROMPT = '-> '

    ADMIN_PROMPT = r'\[.*@controller\-[01].*\(keystone_admin\)\]\$'
    TENANT1_PROMPT = r'\[.*@controller\-[01] .*\(keystone_tenant1\)\]\$ '
    TENANT2_PROMPT = r'\[.*@controller\-[01] .*\(keystone_tenant2\)\]\$ '
    TENANT_PROMPT = r'\[.*@controller\-[01] .*\(keystone_{}\)\]\$ '  #
    # general prompt. Need to fill in tenant name
    REMOTE_CLI_PROMPT = r'\(keystone_{}\)\]\$ '  # remote cli prompt

    COMPUTE_PROMPT = r'.*compute\-([0-9]){1,}\:~\$'
    STORAGE_PROMPT = r'.*storage\-([0-9]){1,}\:~\$'
    PASSWORD_PROMPT = r'.*assword\:[ ]?$|assword for .*:[ ]?$'
    LOGIN_PROMPT = "ogin:"
    SUDO_PASSWORD_PROMPT = 'Password: '
    BUILD_SERVER_PROMPT_BASE = r'{}@{}\:~.*'
    TEST_SERVER_PROMPT_BASE = r'\[{}@.*\]\$ '
    # TIS_NODE_PROMPT_BASE = r'{}\:~\$ '
    TIS_NODE_PROMPT_BASE = r'{}[: ]?~.*$'
    ADD_HOST = r'.*\(yes/no\).*'
    ROOT_PROMPT = '.*root@.*'
    Y_N_PROMPT = r'.*\(y/n\)\?.*'
    YES_N_PROMPT = r'.*\[yes/N\]\: ?'
    CONFIRM_PROMPT = '.*confirm: ?'


class NovaCLIOutput:
    VM_ACTION_ACCEPTED = "Request to {} server (.*) has been accepted."
    VM_START_ACCEPTED = "Request to start server (.*) has been accepted."
    VM_STOP_ACCEPTED = "Request to stop server (.*) has been accepted."
    VM_DELETE_REJECTED_NOT_EXIST = "No server with a name or ID of '(.*)' " \
                                   "exists."
    VM_DELETE_ACCEPTED = "Request to delete server (.*) has been accepted."
    VM_BOOT_REJECT_MEM_PAGE_SIZE_FORBIDDEN = "Page size .* forbidden against .*"
    SRV_GRP_DEL_REJ_NOT_EXIST = "Delete for server group (.*) failed"
    SRV_GRP_DEL_SUCC = "Server group (.*) has been successfully deleted."


class FlavorSpec:
    CPU_POLICY = 'hw:cpu_policy'
    VCPU_MODEL = 'hw:cpu_model'
    SHARED_VCPU = 'hw:wrs:shared_vcpu'
    CPU_THREAD_POLICY = 'hw:cpu_thread_policy'
    VCPU_SCHEDULER = 'hw:wrs:vcpu:scheduler'
    MIN_VCPUS = "hw:wrs:min_vcpus"
    STORAGE_BACKING = 'aggregate_instance_extra_specs:stx_storage'
    DISK_READ_BYTES = 'quota:disk_read_bytes_sec'
    DISK_READ_IOPS = 'quota:disk_read_iops_sec'
    DISK_WRITE_BYTES = 'quota:disk_write_bytes_sec'
    DISK_WRITE_IOPS = 'quota:disk_write_iops_sec'
    DISK_TOTAL_BYTES = 'quota:disk_total_bytes_sec'
    DISK_TOTAL_IOPS = 'quota:disk_total_iops_sec'
    NUMA_NODES = 'hw:numa_nodes'
    NUMA_0 = 'hw:numa_node.0'
    NUMA_1 = 'hw:numa_node.1'
    NUMA0_CPUS = 'hw:numa_cpus.0'
    NUMA1_CPUS = 'hw:numa_cpus.1'
    NUMA0_MEM = 'hw:numa_mem.0'
    NUMA1_MEM = 'hw:numa_mem.1'
    VSWITCH_NUMA_AFFINITY = 'hw:wrs:vswitch_numa_affinity'
    MEM_PAGE_SIZE = 'hw:mem_page_size'
    AUTO_RECOVERY = 'sw:wrs:auto_recovery'
    GUEST_HEARTBEAT = 'sw:wrs:guest:heartbeat'
    SRV_GRP_MSG = "sw:wrs:srv_grp_messaging"
    NIC_ISOLATION = "hw:wrs:nic_isolation"
    PCI_NUMA_AFFINITY = "hw:pci_numa_affinity_policy"
    PCI_PASSTHROUGH_ALIAS = "pci_passthrough:alias"
    PCI_IRQ_AFFINITY_MASK = "hw:pci_irq_affinity_mask"
    CPU_REALTIME = 'hw:cpu_realtime'
    CPU_REALTIME_MASK = 'hw:cpu_realtime_mask'
    HPET_TIMER = 'sw:wrs:guest:hpet'
    NESTED_VMX = 'hw:wrs:nested_vmx'
    NUMA0_CACHE_CPUS = 'hw:cache_vcpus.0'
    NUMA1_CACHE_CPUS = 'hw:cache_vcpus.1'
    NUMA0_L3_CACHE = 'hw:cache_l3.0'
    NUMA1_L3_CACHE = 'hw:cache_l3.1'
    LIVE_MIG_TIME_OUT = 'hw:wrs:live_migration_timeout'


class ImageMetadata:
    MEM_PAGE_SIZE = 'hw_mem_page_size'
    AUTO_RECOVERY = 'sw_wrs_auto_recovery'
    VIF_MODEL = 'hw_vif_model'
    CPU_THREAD_POLICY = 'hw_cpu_thread_policy'
    CPU_POLICY = 'hw_cpu_policy'
    CPU_RT_MASK = 'hw_cpu_realtime_mask'
    CPU_RT = 'hw_cpu_realtime'
    CPU_MODEL = 'hw_cpu_model'
    FIRMWARE_TYPE = 'hw_firmware_type'


class VMMetaData:
    EVACUATION_PRIORITY = 'sw:wrs:recovery_priority'


class InstanceTopology:
    NODE = r'node:(\d),'
    PGSIZE = r'pgsize:(\d{1,3}),'
    VCPUS = r'vcpus:(\d{1,2}),'
    PCPUS = r'pcpus:(\d{1,2}),\s'  # find a string separated by ',
    # ' if multiple numa nodes
    CPU_POLICY = 'pol:(.*),'
    SIBLINGS = 'siblings:(.*),'
    THREAD_POLICY = 'thr:(.*)$|thr:(.*),'
    TOPOLOGY = r'\d{1,2}s,\d{1,2}c,\d{1,2}t'


class RouterStatus:
    ACTIVE = 'ACTIVE'
    DOWN = 'DOWN'


class EventLogID:
    PATCH_INSTALL_FAIL = '900.002'
    PATCH_IN_PROGRESS = '900.001'
    CINDER_IO_CONGEST = '800.101'
    STORAGE_LOR = '800.011'
    STORAGE_POOLQUOTA = '800.003'
    STORAGE_ALARM_COND = '800.001'
    HEARTBEAT_CHECK_FAILED = '700.215'
    HEARTBEAT_ENABLED = '700.211'
    REBOOT_VM_COMPLETE = '700.186'
    REBOOT_VM_INPROGRESS = '700.182'
    REBOOT_VM_ISSUED = '700.181'  # soft-reboot or hard-reboot in reason text
    VM_DELETED = '700.114'
    VM_DELETING = '700.110'
    VM_CREATED = '700.108'
    MULTI_NODE_RECOVERY = '700.016'
    HEARTBEAT_DISABLED = '700.015'
    VM_REBOOTING = '700.005'
    VM_FAILED = '700.001'
    IMA = '500.500'
    SERVICE_GROUP_STATE_CHANGE = '401.001'
    LOSS_OF_REDUNDANCY = '400.002'
    CON_DRBD_SYNC = '400.001'
    PROVIDER_NETWORK_FAILURE = '300.005'
    NETWORK_AGENT_NOT_RESPOND = '300.003'
    CONFIG_OUT_OF_DATE = '250.001'
    INFRA_NET_FAIL = '200.009'
    BMC_SENSOR_ACTION = '200.007'
    STORAGE_DEGRADE = '200.006'
    # 200.004	compute-0 experienced a service-affecting failure.
    # Auto-recovery in progress.
    # host=compute-0 	critical 	April 7, 2017, 2:34 p.m.
    HOST_RECOVERY_IN_PROGRESS = '200.004'
    HOST_LOCK = '200.001'
    NTP_ALARM = '100.114'
    INFRA_PORT_FAIL = '100.110'
    FS_THRESHOLD_EXCEEDED = '100.104'
    CPU_USAGE_HIGH = '100.101'
    MNFA_MODE = '200.020'


class NetworkingVmMapping:
    VSWITCH = {
        'vif': 'avp',
        'flavor': 'medium.dpdk',
    }
    AVP = {
        'vif': 'avp',
        'flavor': 'small',
    }
    VIRTIO = {
        'vif': 'avp',
        'flavor': 'small',
    }


class VifMapping:
    VIF_MAP = {'vswitch': 'DPDKAPPS',
               'avp': 'AVPAPPS',
               'virtio': 'VIRTIOAPPS',
               'vhost': 'VHOSTAPPS',
               'sriov': 'SRIOVAPPS',
               'pcipt': 'PCIPTAPPS'
               }


class LocalStorage:
    DIR_PROFILE = 'storage_profiles'
    TYPE_STORAGE_PROFILE = ['storageProfile', 'localstorageProfile']


class VMNetwork:
    NET_IF = r"auto {}\niface {} inet dhcp\n"
    IFCFG_DHCP = """
DEVICE={}
BOOTPROTO=dhcp
ONBOOT=yes
TYPE=Ethernet
USERCTL=yes
PEERDNS=yes
IPV6INIT={}
PERSISTENT_DHCLIENT=1
"""

    IFCFG_STATIC = """
DEVICE={}
BOOTPROTO=static
ONBOOT=yes
TYPE=Ethernet
USERCTL=yes
PEERDNS=yes
IPV6INIT={}
PERSISTENT_DHCLIENT=1
IPADDR={}
"""


class HTTPPort:
    NEUTRON_PORT = 9696
    NEUTRON_VER = "v2.0"
    CEIL_PORT = 8777
    CEIL_VER = "v2"
    GNOCCHI_PORT = 8041
    GNOCCHI_VER = 'v1'
    SYS_PORT = 6385
    SYS_VER = "v1"
    CINDER_PORT = 8776
    CINDER_VER = "v3"  # v1 and v2 are also supported
    GLANCE_PORT = 9292
    GLANCE_VER = "v2"
    HEAT_PORT = 8004
    HEAT_VER = "v1"
    HEAT_CFN_PORT = 8000
    HEAT_CFN_VER = "v1"
    NOVA_PORT = 8774
    NOVA_VER = "v2.1"  # v3 also supported
    NOVA_EC2_PORT = 8773
    NOVA_EC2_VER = "v2"
    PATCHING_PORT = 15491
    PATCHING_VER = "v1"


class QoSSpec:
    READ_BYTES = 'read_bytes_sec'
    WRITE_BYTES = 'write_bytes_sec'
    TOTAL_BYTES = 'total_bytes_sec'
    READ_IOPS = 'read_iops_sec'
    WRITE_IOPS = 'write_iops_sec'
    TOTAL_IOPS = 'total_iops_sec'


class DevClassID:
    QAT_VF = '0b4000'
    GPU = '030000'
    USB = '0c0320|0c0330'


class MaxVmsSupported:
    SX = 10
    XEON_D = 4
    DX = 10
    VBOX = 2


class CpuModel:
    CPU_MODELS = (
        'Skylake-Server', 'Skylake-Client',
        'Broadwell', 'Broadwell-noTSX',
        'Haswell-noTSX-IBRS', 'Haswell',
        'IvyBridge', 'SandyBridge',
        'Westmere', 'Nehalem', 'Penryn', 'Conroe')


class BackendState:
    CONFIGURED = 'configured'
    CONFIGURING = 'configuring'


class BackendTask:
    RECONFIG_CONTROLLER = 'reconfig-controller'
    APPLY_MANIFEST = 'applying-manifests'


class PartitionStatus:
    READY = 'Ready'
    MODIFYING = 'Modifying'
    DELETING = 'Deleting'
    CREATING = 'Creating'
    IN_USE = 'In-Use'


class SysType:
    AIO_DX = 'AIO-DX'
    AIO_SX = 'AIO-SX'
    STORAGE = 'Storage'
    REGULAR = 'Regular'
    MULTI_REGION = 'Multi-Region'
    DISTRIBUTED_CLOUD = 'Distributed_Cloud'


class HeatStackStatus:
    CREATE_FAILED = 'CREATE_FAILED'
    CREATE_COMPLETE = 'CREATE_COMPLETE'
    UPDATE_COMPLETE = 'UPDATE_COMPLETE'
    UPDATE_FAILED = 'UPDATE_FAILED'
    DELETE_FAILED = 'DELETE_FAILED'


class VimEventID:
    LIVE_MIG_BEGIN = 'instance-live-migrate-begin'
    LIVE_MIG_END = 'instance-live-migrated'
    COLD_MIG_BEGIN = 'instance-cold-migrate-begin'
    COLD_MIG_END = 'instance-cold-migrated'
    COLD_MIG_CONFIRM_BEGIN = 'instance-cold-migrate-confirm-begin'
    COLD_MIG_CONFIRMED = 'instance-cold-migrate-confirmed'


class MigStatus:
    COMPLETED = 'completed'
    RUNNING = 'running'
    PREPARING = 'preparing'
    PRE_MIG = 'pre-migrating'
    POST_MIG = 'post-migrating'


class TrafficControl:
    CLASSES = {'1:40': 'default', '1:1': 'root', '1:10': 'hiprio',
               '1:20': 'storage', '1:30': 'migration',
               '1:50': 'drbd'}

    RATE_PATTERN_ROOT = r'class htb 1:1 root rate (\d+)([GMK])bit ceil (\d+)(' \
                        r'[GMK])bit burst \d+b cburst \d+b'
    RATE_PATTERN = r'class htb (1:\d+) parent 1:1 leaf \d+: prio \d+ rate (' \
                   r'\d+)([GMK])bit ceil (\d+)([GMK])bit ' \
                   r'burst \d+b cburst \d+b'

    # no infra
    MGMT_NO_INFRA = {
        'config': 'no infra',
        'root': (1, 1),
        'default': (0.1, 0.2),
        'hiprio': (0.1, 0.2),
        'storage': (0.5, 1),
        'migration': (0.3, 1),
        'drbd': (0.8, 1)}

    # infra must be sep
    MGMT_SEP = {
        'config': 'separate mgmt',
        'root': (1, 1),
        'default': (0.1, 1),
        'hiprio': (0.1, 1)}

    # infra could be sep or over pxe
    MGMT_USES_PXE = {
        'config': 'mgmt consolidated over pxeboot',
        'root': (1, 1),
        'default': (0.1, 0.2),
        'hiprio': (0.1, 0.2)}

    # infra over mgmt
    MGMT_USED_BY_INFRA = {
        'config': 'infra consolidated over mgmt',
        'root': (1, 1),
        'default': (0.1, 0.2),
        'hiprio': (0.1, 0.2),
        'storage': (0.5, 1),
        'migration': (0.3, 1),
        'drbd': (0.8, 1)}

    # infra over mgmt
    INFRA_USES_MGMT = {
        'config': 'infra consolidated over mgmt',
        'root': (0.99, 0.99),
        'default': (0.99 * 0.1, 0.99 * 0.2),
        'hiprio': (0.99 * 0.1, 0.99 * 0.2),
        'storage': (0.99 * 0.5, 0.99 * 1),
        'migration': (0.99 * 0.3, 0.99 * 1),
        'drbd': (0.99 * 0.8, 0.99 * 1)}

    # mgmt could be sep or over pxe
    INFRA_SEP = {
        'config': 'separate infra',
        'root': (1, 1),
        'default': (0.1, 0.2),
        'hiprio': (0.1, 0.2),
        'storage': (0.5, 1),
        'migration': (0.3, 1),
        'drbd': (0.8, 1)}

    # mgmt must be over pxe
    INFRA_USES_PXE = {
        'config': 'infra and mgmt consolidated over pxeboot',
        'root': (1, 1),
        'default': (0.99 * 0.1, 0.99 * 0.2),  # 0.1, 0.2 is the ratio for mgmt
        'hiprio': (0.99 * 0.1, 0.99 * 0.2),  # 0.1, 0.2 is the ratio for mgmt
        'storage': (0.99 * 0.5, 0.99),
        'migration': (0.99 * 0.3, 0.99),
        'drbd': (0.99 * 0.8, 0.99)}


class SubcloudStatus:
    AVAIL_ONLINE = "online"
    AVAIL_OFFLINE = "offline"
    MGMT_MANAGED = "managed"
    MGMT_UNMANAGED = "unmanaged"
    SYNCED = 'in-sync'
    UNSYNCED = 'out-of-sync'


class PodStatus:
    RUNNING = 'Running'
    COMPLETED = 'Completed'
    CRASH = 'CrashLoopBackOff'
    POD_INIT = 'PodInitializing'
    INIT = 'Init:0/1'
    PENDING = 'Pending'


class AppStatus:
    UPLOADING = 'uploading'
    UPLOADED = 'uploaded'
    UPLOAD_FAILED = 'upload-failed'
    APPLIED = 'applied'
    APPLY_FAILED = 'apply-failed'
    REMOVE_FAILED = 'remove-failed'
    DELETE_FAILED = 'delete-failed'


class VSwitchType:
    OVS_DPDK = 'ovs-dpdk'
    AVS = 'avs'
    NONE = 'none'


class Container:
    LOCAL_DOCKER_REG = 'registry.local:9001'
