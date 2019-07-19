#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


###############################################################
# Intended for check functions for test result verifications
# assert is used to fail the check
# LOG.tc_step is used log the info
# Should be called by test function directly
###############################################################
import re
import time
import copy

from utils.tis_log import LOG
from utils.rest import Rest
from consts.auth import Tenant
from consts.stx import GuestImages, EventLogID
from keywords import host_helper, system_helper, vm_helper, common, \
    glance_helper, storage_helper

SEP = '\n------------------------------------ '


def check_topology_of_vm(vm_id, vcpus, prev_total_cpus=None, numa_num=None,
                         vm_host=None, cpu_pol=None,
                         cpu_thr_pol=None, expt_increase=None, min_vcpus=None,
                         current_vcpus=None,
                         prev_siblings=None, shared_vcpu=None, con_ssh=None,
                         guest=None):
    """
    Check vm has the correct topology based on the number of vcpus,
    cpu policy, cpu threads policy, number of numa nodes

    Check is done via vm-topology, nova host-describe, virsh vcpupin (on vm
    host), nova-compute.log (on vm host),
    /sys/devices/system/cpu/<cpu#>/topology/thread_siblings_list (on vm)

    Args:
        vm_id (str):
        vcpus (int): number of vcpus specified in flavor
        prev_total_cpus (float): such as 37.0000,  37.0625
        numa_num (int): number of numa nodes vm vcpus are on. Default is 1 if
        unset in flavor.
        vm_host (str):
        cpu_pol (str): dedicated or shared
        cpu_thr_pol (str): isolate, require, or prefer
        expt_increase (int): expected total vcpu increase on vm host compared
        to prev_total_cpus
        min_vcpus (None|int): min vcpu flavor spec. vcpu scaling specific
        current_vcpus (None|int): current number of vcpus. vcpu scaling specific
        prev_siblings (list): list of siblings total. Usually used when
        checking vm topology after live migration
        con_ssh (SSHClient)
        shared_vcpu (int): which vcpu is shared
        guest (str|None): guest os. e.g., ubuntu_14. Default guest is assumed
        when None.

    """
    LOG.info(
        "------ Check topology of vm {} on controller, hypervisor and "
        "vm".format(
            vm_id))
    cpu_pol = cpu_pol if cpu_pol else 'shared'

    if vm_host is None:
        vm_host = vm_helper.get_vm_host(vm_id, con_ssh=con_ssh)

    log_cores_siblings = host_helper.get_logcore_siblings(host=vm_host,
                                                          con_ssh=con_ssh)

    if prev_total_cpus is not None:
        if expt_increase is None:
            expt_increase = vcpus

        LOG.info(
            "{}Check total vcpus for vm host is increased by {} via "
            "'openstack hypervisor show'".format(
                SEP, expt_increase))
        expt_used_vcpus = prev_total_cpus + expt_increase
        end_time = time.time() + 70
        while time.time() < end_time:
            post_hosts_cpus = host_helper.get_vcpus_for_computes(
                hosts=vm_host, field='vcpus_used')
            if expt_used_vcpus == post_hosts_cpus[vm_host]:
                break
            time.sleep(10)
        else:
            post_hosts_cpus = host_helper.get_vcpus_for_computes(
                hosts=vm_host, field='used_now')
            assert expt_used_vcpus == post_hosts_cpus[
                vm_host], "Used vcpus on host {} is not as expected. " \
                          "Expected: {}; Actual: {}".format(vm_host,
                                                            expt_used_vcpus,
                                                            post_hosts_cpus[
                                                                vm_host])

    LOG.info(
        "{}Check vm vcpus, pcpus on vm host via nova-compute.log and virsh "
        "vcpupin".format(SEP))
    # Note: floating vm pcpus will not be checked via virsh vcpupin
    vm_host_cpus, vm_siblings = _check_vm_topology_on_host(
        vm_id, vcpus=vcpus, vm_host=vm_host, cpu_pol=cpu_pol,
        cpu_thr_pol=cpu_thr_pol,
        host_log_core_siblings=log_cores_siblings,
        shared_vcpu=shared_vcpu)

    LOG.info(
        "{}Check vm vcpus, siblings on vm via "
        "/sys/devices/system/cpu/<cpu>/topology/thread_siblings_list".
        format(SEP))
    check_sibling = True if shared_vcpu is None else False
    _check_vm_topology_on_vm(vm_id, vcpus=vcpus, siblings_total=vm_siblings,
                             current_vcpus=current_vcpus,
                             prev_siblings=prev_siblings, guest=guest,
                             check_sibling=check_sibling)

    return vm_host_cpus, vm_siblings


def _check_vm_topology_on_host(vm_id, vcpus, vm_host, cpu_pol, cpu_thr_pol,
                               host_log_core_siblings=None, shared_vcpu=None,
                               shared_host_cpus=None):
    """

    Args:
        vm_id (str):
        vcpus (int):
        vm_host (str):
        cpu_pol (str):
        cpu_thr_pol (str):
        host_log_core_siblings (list|None):
        shared_vcpu (int|None):
        shared_host_cpus (None|list)

    Returns: None

    """
    if not host_log_core_siblings:
        host_log_core_siblings = host_helper.get_logcore_siblings(host=vm_host)

    if shared_vcpu and not shared_host_cpus:
        shared_cpus_ = host_helper.get_host_cpu_cores_for_function(
            func='Shared', hostname=vm_host, thread=None)
        shared_host_cpus = []
        for proc, shared_cores in shared_cpus_.items():
            shared_host_cpus += shared_cores

    LOG.info(
        '======= Check vm topology from vm_host via: virsh vcpupin, taskset')
    instance_name = vm_helper.get_vm_instance_name(vm_id)

    with host_helper.ssh_to_host(vm_host) as host_ssh:
        vcpu_cpu_map = vm_helper.get_vcpu_cpu_map(host_ssh=host_ssh)
        used_host_cpus = []
        vm_host_cpus = []
        vcpus_list = list(range(vcpus))
        for instance_name_, instance_map in vcpu_cpu_map.items():
            used_host_cpus += list(instance_map.values())
            if instance_name_ == instance_name:
                for vcpu in vcpus_list:
                    vm_host_cpus.append(instance_map[vcpu])
        used_host_cpus = list(set(used_host_cpus))
        vm_siblings = None
        # Check vm sibling pairs
        if 'ded' in cpu_pol and cpu_thr_pol in ('isolate', 'require'):
            if len(host_log_core_siblings[0]) == 1:
                assert cpu_thr_pol != 'require', \
                    "cpu_thread_policy 'require' must be used on a HT host"
                vm_siblings = [[vcpu_] for vcpu_ in vcpus_list]
            else:
                vm_siblings = []
                for vcpu_index in vcpus_list:
                    vm_host_cpu = vm_host_cpus[vcpu_index]
                    for host_sibling in host_log_core_siblings:
                        if vm_host_cpu in host_sibling:
                            other_cpu = host_sibling[0] if \
                                vm_host_cpu == host_sibling[1] else \
                                host_sibling[1]
                            if cpu_thr_pol == 'require':
                                assert other_cpu in vm_host_cpus, \
                                    "'require' vm uses only 1 of the sibling " \
                                    "cores"
                                vm_siblings.append(sorted([vcpu_index,
                                                           vm_host_cpus.index(
                                                               other_cpu)]))
                            else:
                                assert other_cpu not in used_host_cpus, \
                                    "sibling core was not reserved for " \
                                    "'isolate' vm"
                                vm_siblings.append([vcpu_index])

        LOG.info("{}Check vcpus for vm via sudo virsh vcpupin".format(SEP))
        vcpu_pins = host_helper.get_vcpu_pins_for_instance_via_virsh(
            host_ssh=host_ssh,
            instance_name=instance_name)
        assert vcpus == len(vcpu_pins), \
            'Actual vm cpus number - {} is not as expected - {} in sudo ' \
            'virsh vcpupin'.format(len(vcpu_pins), vcpus)

        virsh_cpus_sets = []
        for vcpu_pin in vcpu_pins:
            vcpu = int(vcpu_pin['vcpu'])
            cpu_set = common.parse_cpus_list(vcpu_pin['cpuset'])
            virsh_cpus_sets += cpu_set
            if shared_vcpu is not None and vcpu == shared_vcpu:
                assert len(cpu_set) == 1, \
                    "shared vcpu is pinned to more than 1 host cpu"
                assert cpu_set[0] in shared_host_cpus, \
                    "shared vcpu is not pinned to shared host cpu"

        if 'ded' in cpu_pol:
            assert set(vm_host_cpus) == set(
                virsh_cpus_sets), "pinned cpus in virsh cpupin is not the " \
                                  "same as ps"
        else:
            assert set(vm_host_cpus) < set(
                virsh_cpus_sets), "floating vm should be affined to all " \
                                  "available host cpus"

        LOG.info("{}Get cpu affinity list for vm via taskset -pc".format(SEP))
        ps_affined_cpus = \
            vm_helper.get_affined_cpus_for_vm(vm_id,
                                              host_ssh=host_ssh,
                                              vm_host=vm_host,
                                              instance_name=instance_name)
        assert set(ps_affined_cpus) == set(
            virsh_cpus_sets), "Actual affined cpu in taskset is different " \
                              "than virsh"
        return vm_host_cpus, vm_siblings


def _check_vm_topology_on_vm(vm_id, vcpus, siblings_total, current_vcpus=None,
                             prev_siblings=None, guest=None,
                             check_sibling=True):
    siblings_total_ = None
    if siblings_total:
        siblings_total_ = copy.deepcopy(siblings_total)
    # Check from vm in /proc/cpuinfo and
    # /sys/devices/.../cpu#/topology/thread_siblings_list
    if not guest:
        guest = ''
    if not current_vcpus:
        current_vcpus = int(vcpus)

    LOG.info(
        '=== Check vm topology from within the vm via: /sys/devices/system/cpu')
    actual_sibs = []
    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    with vm_helper.ssh_to_vm_from_natbox(vm_id) as vm_ssh:

        win_expt_cores_per_sib = win_log_count_per_sibling = None
        if 'win' in guest:
            LOG.info(
                "{}Check windows guest cores via wmic cpu get cmds".format(SEP))
            offline_cores_count = 0
            log_cores_count, win_log_count_per_sibling = \
                get_procs_and_siblings_on_windows(vm_ssh)
            online_cores_count = present_cores_count = log_cores_count
        else:
            LOG.info(
                "{}Check vm present|online|offline cores from inside vm via "
                "/sys/devices/system/cpu/".format(SEP))
            present_cores, online_cores, offline_cores = \
                vm_helper.get_proc_nums_from_vm(vm_ssh)
            present_cores_count = len(present_cores)
            online_cores_count = len(online_cores)
            offline_cores_count = len(offline_cores)

        assert vcpus == present_cores_count, \
            "Number of vcpus: {}, present cores: {}".format(
                vcpus, present_cores_count)
        assert current_vcpus == online_cores_count, \
            "Current vcpus for vm: {}, online cores: {}".format(
                current_vcpus, online_cores_count)

        expt_total_cores = online_cores_count + offline_cores_count
        assert expt_total_cores in [present_cores_count, 512], \
            "Number of present cores: {}. online+offline cores: {}".format(
                vcpus, expt_total_cores)

        if check_sibling and siblings_total_ and online_cores_count == \
                present_cores_count:
            expt_sibs_list = [[vcpu] for vcpu in
                              range(present_cores_count)] if not \
                siblings_total_ \
                else siblings_total_

            expt_sibs_list = [sorted(expt_sibs_list)]
            if prev_siblings:
                # siblings_total may get modified here
                expt_sibs_list.append(sorted(prev_siblings))

            if 'win' in guest:
                LOG.info("{}Check windows guest siblings via wmic cpu get "
                         "cmds".format(SEP))
                expt_cores_list = []
                for sib_list in expt_sibs_list:
                    win_expt_cores_per_sib = [len(vcpus) for vcpus in sib_list]
                    expt_cores_list.append(win_expt_cores_per_sib)
                assert win_log_count_per_sibling in expt_cores_list, \
                    "Expected log cores count per sibling: {}, actual: {}".\
                    format(win_expt_cores_per_sib, win_log_count_per_sibling)

            else:
                LOG.info(
                    "{}Check vm /sys/devices/system/cpu/["
                    "cpu#]/topology/thread_siblings_list".format(
                        SEP))
                for cpu in ['cpu{}'.format(i) for i in
                            range(online_cores_count)]:
                    actual_sibs_for_cpu = \
                        vm_ssh.exec_cmd(
                            'cat /sys/devices/system/cpu/{}/topology/thread_'
                            'siblings_list'.format(cpu), fail_ok=False)[1]

                    sib_for_cpu = common.parse_cpus_list(actual_sibs_for_cpu)
                    if sib_for_cpu not in actual_sibs:
                        actual_sibs.append(sib_for_cpu)

                assert sorted(
                    actual_sibs) in expt_sibs_list, "Expt sib lists: {}, " \
                                                    "actual sib list: {}". \
                    format(expt_sibs_list, sorted(actual_sibs))


def get_procs_and_siblings_on_windows(vm_ssh):
    cmd = 'wmic cpu get {}'

    procs = []
    for param in ['NumberOfCores', 'NumberOfLogicalProcessors']:
        output = vm_ssh.exec_cmd(cmd.format(param), fail_ok=False)[1].strip()
        num_per_proc = [int(line.strip()) for line in output.splitlines() if
                        line.strip()
                        and not re.search('{}|x'.format(param), line)]
        procs.append(num_per_proc)
    procs = zip(procs[0], procs[1])
    log_procs_per_phy = [nums[0] * nums[1] for nums in procs]
    total_log_procs = sum(log_procs_per_phy)

    LOG.info(
        "Windows guest total logical cores: {}, logical_cores_per_phy_core: {}".
        format(total_log_procs, log_procs_per_phy))
    return total_log_procs, log_procs_per_phy


def check_vm_vswitch_affinity(vm_id, on_vswitch_nodes=True):
    vm_host, vm_numa_nodes = vm_helper.get_vm_host_and_numa_nodes(vm_id)
    vswitch_cores_dict = host_helper.get_host_cpu_cores_for_function(
        vm_host, func='vSwitch')
    vswitch_procs = [proc for proc in vswitch_cores_dict if
                     vswitch_cores_dict[proc]]
    if not vswitch_procs:
        return

    if on_vswitch_nodes:
        assert set(vm_numa_nodes) <= set(
            vswitch_procs), "VM {} is on numa nodes {} instead of vswitch " \
                            "numa nodes {}".format(
            vm_id, vm_numa_nodes, vswitch_procs)
    else:
        assert not (set(vm_numa_nodes) & set(
            vswitch_procs)), "VM {} is on vswitch numa node(s). VM numa " \
                             "nodes: {}, vSwitch numa nodes: {}".format(
            vm_id, vm_numa_nodes, vswitch_procs)


def check_fs_sufficient(guest_os, boot_source='volume'):
    """
    Check if volume pool, image storage, and/or image conversion space is
    sufficient to launch vm
    Args:
        guest_os (str): e.g., tis-centos-guest, win_2016
        boot_source (str): volume or image

    Returns (str): image id

    """
    LOG.info("Check if storage fs is sufficient to launch boot-from-{} vm "
             "with {}".format(boot_source, guest_os))
    check_disk = True if 'win' in guest_os else False
    cleanup = None if re.search(
        'ubuntu_14|{}'.format(GuestImages.TIS_GUEST_PATTERN),
        guest_os) else 'function'
    img_id = glance_helper.get_guest_image(guest_os, check_disk=check_disk,
                                           cleanup=cleanup)
    return img_id


def check_vm_files(vm_id, storage_backing, ephemeral, swap, vm_type, file_paths,
                   content, root=None, vm_action=None,
                   prev_host=None, post_host=None, disks=None, post_disks=None,
                   guest_os=None,
                   check_volume_root=False):
    """
    Check the files on vm after specified action. This is to check the disks
    in the basic nova matrix table.
    Args:
        vm_id (str):
        storage_backing (str): local_image, local_lvm, or remote
        root (int): root disk size in flavor. e.g., 2, 5
        ephemeral (int): e.g., 0, 1
        swap (int): e.g., 0, 512
        vm_type (str): image, volume, image_with_vol, vol_with_vol
        file_paths (list): list of file paths to check
        content (str): content of the files (assume all files have the same
        content)
        vm_action (str|None): live_migrate, cold_migrate, resize, evacuate,
            None (expect no data loss)
        prev_host (None|str): vm host prior to vm_action. This is used to
        check if vm host has changed when needed.
        post_host (None|str): vm host after vm_action.
        disks (dict): disks that are returned from
        vm_helper.get_vm_devices_via_virsh()
        post_disks (dict): only used in resize case
        guest_os (str|None): default guest assumed for None. e,g., ubuntu_16
        check_volume_root (bool): whether to check root disk size even if vm
        is booted from image

    Returns:

    """
    final_disks = post_disks if post_disks else disks
    final_paths = list(file_paths)
    if not disks:
        disks = vm_helper.get_vm_devices_via_virsh(vm_id=vm_id)

    eph_disk = disks.get('eph', {})
    if not eph_disk:
        if post_disks:
            eph_disk = post_disks.get('eph', {})
    swap_disk = disks.get('swap', {})
    if not swap_disk:
        if post_disks:
            swap_disk = post_disks.get('swap', {})

    disk_check = 'no_loss'
    if vm_action in [None, 'live_migrate']:
        disk_check = 'no_loss'
    elif vm_type == 'volume':
        # boot-from-vol, non-live migrate actions
        disk_check = 'no_loss'
        if storage_backing == 'local_lvm' and (eph_disk or swap_disk):
            disk_check = 'eph_swap_loss'
        elif storage_backing == 'local_image' and vm_action == 'evacuate' and (
                eph_disk or swap_disk):
            disk_check = 'eph_swap_loss'
    elif storage_backing == 'local_image':
        # local_image, boot-from-image, non-live migrate actions
        disk_check = 'no_loss'
        if vm_action == 'evacuate':
            disk_check = 'local_loss'
    elif storage_backing == 'local_lvm':
        # local_lvm, boot-from-image, non-live migrate actions
        disk_check = 'local_loss'
        if vm_action == 'resize':
            post_host = post_host if post_host else vm_helper.get_vm_host(vm_id)
            if post_host == prev_host:
                disk_check = 'eph_swap_loss'

    LOG.info("disk check type: {}".format(disk_check))
    loss_paths = []
    if disk_check == 'no_loss':
        no_loss_paths = final_paths
    else:
        # If there's any loss, we must not have remote storage. And any
        # ephemeral/swap disks will be local.
        disks_to_check = disks.get('eph', {})
        # skip swap type checking for data loss since it's not a regular
        # filesystem
        # swap_disks = disks.get('swap', {})
        # disks_to_check.update(swap_disks)

        for path_ in final_paths:
            # For tis-centos-guest, ephemeral disk is mounted to /mnt after
            # vm launch.
            if str(path_).rsplit('/', 1)[0] == '/mnt':
                loss_paths.append(path_)
                break

        for disk in disks_to_check:
            for path in final_paths:
                if disk in path:
                    # We mount disk vdb to /mnt/vdb, so this is looking for
                    # vdb in the mount path
                    loss_paths.append(path)
                    break

        if disk_check == 'local_loss':
            # if vm booted from image, then the root disk is also local disk
            root_img = disks.get('root_img', {})
            if root_img:
                LOG.info(
                    "Auto mount vm disks again since root disk was local with "
                    "data loss expected")
                vm_helper.auto_mount_vm_disks(vm_id=vm_id, disks=final_disks)
                file_name = final_paths[0].rsplit('/')[-1]
                root_path = '/{}'.format(file_name)
                loss_paths.append(root_path)
                assert root_path in final_paths, \
                    "root_path:{}, file_paths:{}".format(root_path, final_paths)

        no_loss_paths = list(set(final_paths) - set(loss_paths))

    LOG.info("loss_paths: {}, no_loss_paths: {}, total_file_pahts: {}".format(
        loss_paths, no_loss_paths, final_paths))
    res_files = {}
    with vm_helper.ssh_to_vm_from_natbox(vm_id=vm_id,
                                         vm_image_name=guest_os) as vm_ssh:
        vm_ssh.exec_sudo_cmd('cat /etc/fstab')
        vm_ssh.exec_sudo_cmd("mount | grep --color=never '/dev'")

        for file_path in loss_paths:
            vm_ssh.exec_sudo_cmd('touch {}2'.format(file_path), fail_ok=False)
            vm_ssh.exec_sudo_cmd('echo "{}" >> {}2'.format(content, file_path),
                                 fail_ok=False)

        for file_path in no_loss_paths:
            output = vm_ssh.exec_sudo_cmd('cat {}'.format(file_path),
                                          fail_ok=False)[1]
            res = '' if content in output else 'content mismatch'
            res_files[file_path] = res

        for file, error in res_files.items():
            assert not error, "Check {} failed: {}".format(file, error)

        swap_disk = final_disks.get('swap', {})
        if swap_disk:
            disk_name = list(swap_disk.keys())[0]
            partition = '/dev/{}'.format(disk_name)
            if disk_check != 'local_loss' and not disks.get('swap', {}):
                mount_on, fs_type = storage_helper.mount_partition(
                    ssh_client=vm_ssh, disk=disk_name,
                    partition=partition, fs_type='swap')
                storage_helper.auto_mount_fs(ssh_client=vm_ssh, fs=partition,
                                             mount_on=mount_on, fs_type=fs_type)

            LOG.info("Check swap disk is on")
            swap_output = vm_ssh.exec_sudo_cmd(
                'cat /proc/swaps | grep --color=never {}'.format(partition))[1]
            assert swap_output, "Expect swapon for {}. Actual output: {}". \
                format(partition, vm_ssh.exec_sudo_cmd('cat /proc/swaps')[1])

            LOG.info("Check swap disk size")
            _check_disk_size(vm_ssh, disk_name=disk_name, expt_size=swap)

        eph_disk = final_disks.get('eph', {})
        if eph_disk:
            LOG.info("Check ephemeral disk size")
            eph_name = list(eph_disk.keys())[0]
            _check_disk_size(vm_ssh, eph_name, expt_size=ephemeral * 1024)

        if root:
            image_root = final_disks.get('root_img', {})
            root_name = ''
            if image_root:
                root_name = list(image_root.keys())[0]
            elif check_volume_root:
                root_name = list(final_disks.get('root_vol').keys())[0]

            if root_name:
                LOG.info("Check root disk size")
                _check_disk_size(vm_ssh, disk_name=root_name,
                                 expt_size=root * 1024)


def _check_disk_size(vm_ssh, disk_name, expt_size):
    partition = vm_ssh.exec_sudo_cmd(
        'cat /proc/partitions | grep --color=never "{}$"'.format(disk_name))[1]
    actual_size = int(
        int(partition.split()[-2].strip()) / 1024) if partition else 0
    expt_size = int(expt_size)
    assert actual_size == expt_size, "Expected disk size: {}M. Actual: {}M".\
        format(expt_size, actual_size)


def check_alarms(before_alarms, timeout=300,
                 auth_info=Tenant.get('admin_platform'), con_ssh=None,
                 fail_ok=False):
    after_alarms = system_helper.get_alarms(auth_info=auth_info,
                                            con_ssh=con_ssh)
    new_alarms = []
    check_interval = 5
    for item in after_alarms:
        if item not in before_alarms:
            alarm_id, entity_id = item.split('::::')
            if alarm_id == EventLogID.CPU_USAGE_HIGH:
                check_interval = 45
            elif alarm_id == EventLogID.NTP_ALARM:
                # NTP alarm handling
                LOG.info("NTP alarm found, checking ntpq stats")
                host = entity_id.split('host=')[1].split('.ntp')[0]
                system_helper.wait_for_ntp_sync(host=host, fail_ok=False,
                                                auth_info=auth_info,
                                                con_ssh=con_ssh)
                continue

            new_alarms.append((alarm_id, entity_id))

    res = True
    remaining_alarms = None
    if new_alarms:
        LOG.info("New alarms detected. Waiting for new alarms to clear.")
        res, remaining_alarms = \
            system_helper.wait_for_alarms_gone(new_alarms,
                                               fail_ok=True,
                                               timeout=timeout,
                                               check_interval=check_interval,
                                               auth_info=auth_info,
                                               con_ssh=con_ssh)

    if not res:
        msg = "New alarm(s) found and did not clear within {} seconds. " \
              "Alarm IDs and Entity IDs: {}".format(timeout, remaining_alarms)
        LOG.warning(msg)
        if not fail_ok:
            assert res, msg

    return res, remaining_alarms


def check_rest_api():
    LOG.info("Check sysinv REST API")
    sysinv_rest = Rest('sysinv', platform=True)
    resource = '/controller_fs'
    status_code, text = sysinv_rest.get(resource=resource, auth=True)
    message = "Retrieved: status_code: {} message: {}"
    LOG.debug(message.format(status_code, text))

    LOG.info("Check status_code of 200 is received")
    message = "Expected status_code of 200 - received {} and message {}"
    assert status_code == 200, message.format(status_code, text)
