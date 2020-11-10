#
# Copyright (c) 2019, 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


CLI_TIMEOUT = 600


class HostTimeout:
    # Host in online state after locked
    ONLINE_AFTER_LOCK = 1200
    # Compute host reaches enabled/available state after system host-unlock
    # returned
    COMPUTE_UNLOCK = 840
    # Host reaches enabled/available state after system host-unlock returned
    CONTROLLER_UNLOCK = 1360
    # Host reaches enabled/available state after sudo reboot -f from host
    REBOOT = 2400
    # Active controller switched and being able to run openstack CLI after
    # system host-swact returned
    SWACT = 600
    # Host in locked state after system host-lock cli returned
    LOCK = 900
    # Task clears in system host-show after host reaches enabled/available state
    TASK_CLEAR = 600
    # Host in offline or failed state via system host-show after sudo reboot
    # -f returned
    FAIL_AFTER_REBOOT = 120
    # Hypervsior in enabled/up state after host in available state and task
    # clears
    HYPERVISOR_UP = 300
    # Web service up in sudo sm-dump after host in available state and task
    # clears
    WEB_SERVICE_UP = 180
    PING_TIMEOUT = 60
    TIMEOUT_BUFFER = 2
    # subfunction go enabled/available after host admin/avail states go
    # enabled/available
    SUBFUNC_READY = 300
    SYSTEM_RESTORE = 3600  # System restore complete
    SYSTEM_BACKUP = 1800  # system backup complete
    BACKUP_COPY_USB = 600
    INSTALL_CLONE = 3600
    INSTALL_CLONE_STATUS = 60
    INSTALL_CONTROLLER = 2400
    INSTALL_LOAD = 3600
    POST_INSTALL_SCRIPTS = 3600
    CONFIG_CONTROLLER_TIMEOUT = 1800
    CEPH_MON_ADD_CONFIG = 300
    NODES_STATUS_READY = 7200


class InstallTimeout:
    # Host reaches enabled/available state after system host-unlock returned
    CONTROLLER_UNLOCK = 9000
    CONFIG_CONTROLLER_TIMEOUT = 1800
    # REBOOT = 2000   # Host reaches enabled/available state after sudo
    # reboot -f from host
    UPGRADE = 7200
    WIPE_DISK_TIMEOUT = 30
    SYSTEM_RESTORE = 3600  # System restore complete
    SYSTEM_BACKUP = 1800  # system backup complete
    BACKUP_COPY_USB = 600
    INSTALL_CLONE = 3600
    INSTALL_CLONE_STATUS = 60
    INSTALL_CONTROLLER = 2400
    INSTALL_LOAD = 3600
    POST_INSTALL_SCRIPTS = 3600


class VMTimeout:
    STATUS_CHANGE = 300
    STATUS_VERIFY_RESIZE = 30
    LIVE_MIGRATE_COMPLETE = 240
    COLD_MIGRATE_CONFIRM = 600
    BOOT_VM = 1800
    DELETE = 180
    VOL_ATTACH = 60
    SSH_LOGIN = 90
    AUTO_RECOVERY = 600
    REBOOT = 180
    PAUSE = 180
    IF_ADD = 30
    REBUILD = 300
    DHCP_IP_ASSIGN = 30
    DHCP_RETRY = 500
    PING_VM = 200


class VolumeTimeout:
    STATUS_CHANGE = 2700  # Windows guest takes a long time
    DELETE = 90


class SysInvTimeout:
    RETENTION_PERIOD_SAVED = 30
    RETENTION_PERIOD_MODIFY = 60
    DNS_SERVERS_SAVED = 30
    DNS_MODIFY = 60
    PARTITION_CREATE = 120
    PARTITION_DELETE = 120
    PARTITION_MODIFY = 120


class CMDTimeout:
    HOST_CPU_MODIFY = 600
    RESOURCE_LIST = 60
    REBOOT_VM = 60
    CPU_PROFILE_APPLY = 30


class ImageTimeout:
    CREATE = 1800
    STATUS_CHANGE = 60
    DELETE = 120


class EventLogTimeout:
    HEARTBEAT_ESTABLISH = 300
    HEALTH_CHECK_FAIL = 60
    VM_REBOOT = 60
    NET_AGENT_NOT_RESPOND_CLEAR = 120


class MTCTimeout:
    KILL_PROCESS_HOST_CHANGE_STATUS = 40
    KILL_PROCESS_HOST_KEEP_STATUS = 20
    KILL_PROCESS_SWACT_NOT_START = 20
    KILL_PROCESS_SWACT_START = 40
    KILL_PROCESS_SWACT_COMPLETE = 40


class CeilTimeout:
    EXPIRE = 300


class OrchestrationPhaseTimeout:
    INITIAL = 20
    BUILD = 60
    ABORT = 7200
    APPLY = 86400


class DCTimeout:
    SYNC = 3600  # 60 minutes
    SUBCLOUD_AUDIT = 600  # 4 minutes + 1
    PATCH_AUDIT = 240  # 3 minutes + 1


class MiscTimeout:
    # timeout for two audits. 'sudo ntpq' got pulled every 10 minutes in
    # /var/log/user.log
    NTPQ_UPDATE = 1260


class K8sTimeout:
    APP_UPLOAD = 300
    APP_APPLY = 600
