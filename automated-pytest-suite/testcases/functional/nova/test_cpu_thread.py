#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, fixture, skip, param

from utils.tis_log import LOG

from consts.reasons import SkipHypervisor, SkipHyperthreading
from consts.stx import FlavorSpec, ImageMetadata
# Do not remove used imports below as they are used in eval()
from consts.cli_errs import CPUThreadErr

from keywords import nova_helper, vm_helper, host_helper, glance_helper, \
    check_helper
from testfixtures.fixture_resources import ResourceCleanup
from testfixtures.recover_hosts import HostsToRecover


def id_gen(val):
    if isinstance(val, list):
        return '-'.join(val)


@fixture(scope='module')
def ht_and_nonht_hosts():
    LOG.fixture_step(
        "(Module) Get hyper-threading enabled and disabled hypervisors")
    nova_hosts = host_helper.get_up_hypervisors()
    ht_hosts = []
    non_ht_hosts = []
    for host in nova_hosts:
        if host_helper.is_host_hyperthreaded(host):
            ht_hosts.append(host)
        else:
            non_ht_hosts.append(host)

    LOG.info(
        '-- Hyper-threading enabled hosts: {}; Hyper-threading disabled '
        'hosts: {}'.format(
            ht_hosts, non_ht_hosts))
    return ht_hosts, non_ht_hosts


class TestHTEnabled:

    @fixture(scope='class', autouse=True)
    def ht_hosts_(self, ht_and_nonht_hosts):
        ht_hosts, non_ht_hosts = ht_and_nonht_hosts

        if not ht_hosts:
            skip("No up hypervisor found with Hyper-threading enabled.")

        return ht_hosts, non_ht_hosts

    def test_isolate_vm_on_ht_host(self, ht_hosts_, add_admin_role_func):
        """
        Test isolate vms take the host log_core sibling pair for each vcpu
        when HT is enabled.
        Args:
            ht_hosts_:
            add_admin_role_func:

        Pre-conditions: At least on hypervisor has HT enabled

        Test Steps:
            - Launch VM with isolate thread policy and 4 vcpus, until all
            Application cores on thread-0 are taken
            - Attempt to launch another vm on same host, and ensure it fails

        """
        ht_hosts, non_ht_hosts = ht_hosts_
        vcpu_count = 4
        cpu_thread_policy = 'isolate'
        LOG.tc_step("Create flavor with {} vcpus and {} thread policy".format(
            vcpu_count, cpu_thread_policy))
        flavor_id = nova_helper.create_flavor(
            name='cpu_thread_{}'.format(cpu_thread_policy), vcpus=vcpu_count,
            cleanup='function')[1]
        specs = {FlavorSpec.CPU_POLICY: 'dedicated',
                 FlavorSpec.CPU_THREAD_POLICY: cpu_thread_policy}
        nova_helper.set_flavor(flavor_id, **specs)

        LOG.tc_step(
            "Get used vcpus for vm host before booting vm, and ensure "
            "sufficient instance and core quotas")
        host = ht_hosts[0]
        vms = vm_helper.get_vms_on_host(hostname=host)
        vm_helper.delete_vms(vms=vms)
        log_core_counts = host_helper.get_logcores_counts(
            host, thread='0', functions='Applications')
        max_vm_count = int(log_core_counts[0] / vcpu_count) + int(
            log_core_counts[1] / vcpu_count)
        vm_helper.ensure_vms_quotas(vms_num=max_vm_count + 10,
                                    cores_num=4 * (max_vm_count + 2) + 10)

        LOG.tc_step(
            "Boot {} isolate 4vcpu vms on a HT enabled host, and check "
            "topology of vm on host and vms".
            format(max_vm_count))
        for i in range(max_vm_count):
            name = '4vcpu_isolate-{}'.format(i)
            LOG.info(
                "Launch VM {} on {} and check it's topology".format(name, host))
            prev_cpus = host_helper.get_vcpus_for_computes(
                hosts=[host], field='used_now')[host]
            vm_id = vm_helper.boot_vm(name=name, flavor=flavor_id, vm_host=host,
                                      cleanup='function')[1]

            check_helper.check_topology_of_vm(vm_id, vcpus=vcpu_count,
                                              prev_total_cpus=prev_cpus,
                                              cpu_pol='dedicated',
                                              cpu_thr_pol=cpu_thread_policy,
                                              vm_host=host)

        LOG.tc_step(
            "Attempt to boot another vm on {}, and ensure it fails due to no "
            "free sibling pairs".format(host))
        code = vm_helper.boot_vm(name='cpu_thread_{}'.format(cpu_thread_policy),
                                 flavor=flavor_id, vm_host=host,
                                 fail_ok=True, cleanup='function')[0]
        assert code > 0, "VM is still scheduled even though all sibling " \
                         "pairs should have been occupied"

    @mark.parametrize(('vcpus', 'cpu_thread_policy', 'min_vcpus'), [
        param(4, 'require', None),
        param(3, 'require', None),
        param(3, 'prefer', None),
    ])
    def test_boot_vm_cpu_thread_positive(self, vcpus, cpu_thread_policy,
                                         min_vcpus, ht_hosts_):
        """
        Test boot vm with specific cpu thread policy requirement

        Args:
            vcpus (int): number of vpus to set when creating flavor
            cpu_thread_policy (str): cpu thread policy to set in flavor
            min_vcpus (int): min_vcpus extra spec to set
            ht_hosts_ (tuple): (ht_hosts, non-ht_hosts)

        Skip condition:
            - no host is hyperthreading enabled on system

        Setups:
            - Find out HT hosts and non-HT_hosts on system   (module)

        Test Steps:
            - Create a flavor with given number of vcpus
            - Set cpu policy to dedicated and extra specs as per test params
            - Get the host vcpu usage before booting vm
            - Boot a vm with above flavor
            - Ensure vm is booted on HT host for 'require' vm
            - Check vm-topology, host side vcpu usage, topology from within
            the guest to ensure vm is properly booted

        Teardown:
            - Delete created vm, volume, flavor

        """
        ht_hosts, non_ht_hosts = ht_hosts_
        LOG.tc_step("Create flavor with {} vcpus".format(vcpus))
        flavor_id = nova_helper.create_flavor(
            name='cpu_thread_{}'.format(cpu_thread_policy), vcpus=vcpus)[1]
        ResourceCleanup.add('flavor', flavor_id)

        specs = {FlavorSpec.CPU_POLICY: 'dedicated'}
        if cpu_thread_policy is not None:
            specs[FlavorSpec.CPU_THREAD_POLICY] = cpu_thread_policy

        if min_vcpus is not None:
            specs[FlavorSpec.MIN_VCPUS] = min_vcpus

        LOG.tc_step("Set following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor_id, **specs)

        LOG.tc_step("Get used cpus for all hosts before booting vm")
        hosts_to_check = ht_hosts if cpu_thread_policy == 'require' else \
            ht_hosts + non_ht_hosts
        pre_hosts_cpus = host_helper.get_vcpus_for_computes(
            hosts=hosts_to_check, field='used_now')

        LOG.tc_step(
            "Boot a vm with above flavor and ensure it's booted on a HT "
            "enabled host.")
        vm_id = vm_helper.boot_vm(
            name='cpu_thread_{}'.format(cpu_thread_policy),
            flavor=flavor_id,
            cleanup='function')[1]

        vm_host = vm_helper.get_vm_host(vm_id)
        if cpu_thread_policy == 'require':
            assert vm_host in ht_hosts, "VM host {} is not hyper-threading " \
                                        "enabled.".format(vm_host)

        LOG.tc_step("Check topology of the {}vcpu {} vm on hypervisor and "
                    "on vm".format(vcpus, cpu_thread_policy))
        prev_cpus = pre_hosts_cpus[vm_host]
        check_helper.check_topology_of_vm(vm_id, vcpus=vcpus,
                                          prev_total_cpus=prev_cpus,
                                          cpu_pol='dedicated',
                                          cpu_thr_pol=cpu_thread_policy,
                                          min_vcpus=min_vcpus, vm_host=vm_host)

    @mark.parametrize(('vcpus', 'cpu_pol', 'cpu_thr_pol', 'flv_or_img',
                       'vs_numa_affinity', 'boot_source', 'nova_actions'), [
        param(2, 'dedicated', 'isolate', 'image', None, 'volume',
              'live_migrate', marks=mark.priorities('domain_sanity',
                                                    'nightly')),
        param(3, 'dedicated', 'require', 'image', None, 'volume',
              'live_migrate', marks=mark.domain_sanity),
        param(3, 'dedicated', 'prefer', 'flavor', None, 'volume',
              'live_migrate', marks=mark.p2),
        param(3, 'dedicated', 'require', 'flavor', None, 'volume',
              'live_migrate', marks=mark.p2),
        param(3, 'dedicated', 'isolate', 'flavor', None, 'volume',
              'cold_migrate', marks=mark.domain_sanity),
        param(2, 'dedicated', 'require', 'image', None, 'image',
              'cold_migrate',  marks=mark.domain_sanity),
        param(2, 'dedicated', 'require', 'flavor', None, 'volume',
              'cold_mig_revert', marks=mark.p2),
        param(5, 'dedicated', 'prefer', 'image', None, 'volume',
              'cold_mig_revert'),
        param(4, 'dedicated', 'isolate', 'image', None, 'volume',
              ['suspend', 'resume', 'rebuild'], marks=mark.p2),
        param(6, 'dedicated', 'require', 'image', None, 'image',
              ['suspend', 'resume', 'rebuild'], marks=mark.p2),
    ], ids=id_gen)
    def test_cpu_thread_vm_topology_nova_actions(self, vcpus, cpu_pol,
                                                 cpu_thr_pol, flv_or_img,
                                                 vs_numa_affinity,
                                                 boot_source, nova_actions,
                                                 ht_hosts_):
        ht_hosts, non_ht_hosts = ht_hosts_
        if 'mig' in nova_actions:
            if len(ht_hosts) + len(non_ht_hosts) < 2:
                skip(SkipHypervisor.LESS_THAN_TWO_HYPERVISORS)
            if cpu_thr_pol in ['require', 'isolate'] and len(ht_hosts) < 2:
                skip(SkipHyperthreading.LESS_THAN_TWO_HT_HOSTS)

        name_str = 'cpu_thr_{}_in_img'.format(cpu_pol)

        LOG.tc_step("Create flavor with {} vcpus".format(vcpus))
        flavor_id = nova_helper.create_flavor(name='vcpus{}'.format(vcpus),
                                              vcpus=vcpus)[1]
        ResourceCleanup.add('flavor', flavor_id)

        specs = {}
        if vs_numa_affinity:
            specs[FlavorSpec.VSWITCH_NUMA_AFFINITY] = vs_numa_affinity

        if flv_or_img == 'flavor':
            specs[FlavorSpec.CPU_POLICY] = cpu_pol
            specs[FlavorSpec.CPU_THREAD_POLICY] = cpu_thr_pol

        if specs:
            LOG.tc_step("Set following extra specs: {}".format(specs))
            nova_helper.set_flavor(flavor_id, **specs)

        image_id = None
        if flv_or_img == 'image':
            image_meta = {ImageMetadata.CPU_POLICY: cpu_pol,
                          ImageMetadata.CPU_THREAD_POLICY: cpu_thr_pol}
            LOG.tc_step(
                "Create image with following metadata: {}".format(image_meta))
            image_id = glance_helper.create_image(name=name_str,
                                                  cleanup='function',
                                                  **image_meta)[1]

        LOG.tc_step("Get used cpus for all hosts before booting vm")
        hosts_to_check = ht_hosts if cpu_thr_pol == 'require' else \
            ht_hosts + non_ht_hosts
        pre_hosts_cpus = host_helper.get_vcpus_for_computes(
            hosts=hosts_to_check, field='used_now')

        LOG.tc_step("Boot a vm from {} with above flavor".format(boot_source))
        vm_id = vm_helper.boot_vm(name=name_str, flavor=flavor_id,
                                  source=boot_source, image_id=image_id,
                                  cleanup='function')[1]

        vm_host = vm_helper.get_vm_host(vm_id)

        if cpu_thr_pol == 'require':
            LOG.tc_step("Check vm is booted on a HT host")
            assert vm_host in ht_hosts, "VM host {} is not hyper-threading " \
                                        "enabled.".format(vm_host)

        prev_cpus = pre_hosts_cpus[vm_host]
        prev_siblings = check_helper.check_topology_of_vm(
            vm_id, vcpus=vcpus, prev_total_cpus=prev_cpus, cpu_pol=cpu_pol,
            cpu_thr_pol=cpu_thr_pol, vm_host=vm_host)[1]

        LOG.tc_step("Perform following nova action(s) on vm {}: "
                    "{}".format(vm_id, nova_actions))
        if isinstance(nova_actions, str):
            nova_actions = [nova_actions]

        check_prev_siblings = False
        for action in nova_actions:
            kwargs = {}
            if action == 'rebuild':
                kwargs['image_id'] = image_id
            elif action == 'live_migrate':
                check_prev_siblings = True
            vm_helper.perform_action_on_vm(vm_id, action=action, **kwargs)

        post_vm_host = vm_helper.get_vm_host(vm_id)
        pre_action_cpus = pre_hosts_cpus[post_vm_host]

        if cpu_thr_pol == 'require':
            LOG.tc_step("Check vm is still on HT host")
            assert post_vm_host in ht_hosts, "VM host {} is not " \
                                             "hyper-threading " \
                                             "enabled.".format(vm_host)

        LOG.tc_step(
            "Check VM topology is still correct after {}".format(nova_actions))
        if cpu_pol != 'dedicated' or not check_prev_siblings:
            # Allow prev_siblings in live migration case
            prev_siblings = None
        check_helper.check_topology_of_vm(vm_id, vcpus=vcpus,
                                          prev_total_cpus=pre_action_cpus,
                                          cpu_pol=cpu_pol,
                                          cpu_thr_pol=cpu_thr_pol,
                                          vm_host=post_vm_host,
                                          prev_siblings=prev_siblings)

    @fixture(scope='class')
    def _add_hosts_to_stxauto(self, request, ht_hosts_, add_stxauto_zone):
        ht_hosts, non_ht_hosts = ht_hosts_

        if not non_ht_hosts:
            skip("No non-HT host available")

        LOG.fixture_step("Add one HT host and nonHT hosts to stxauto zone")

        if len(ht_hosts) > 1:
            ht_hosts = [ht_hosts[0]]

        host_in_stxauto = ht_hosts + non_ht_hosts

        def _revert():
            nova_helper.remove_hosts_from_aggregate(aggregate='stxauto',
                                                    hosts=host_in_stxauto)

        request.addfinalizer(_revert)

        nova_helper.add_hosts_to_aggregate('stxauto', ht_hosts + non_ht_hosts)

        LOG.info(
            "stxauto zone: HT: {}; non-HT: {}".format(ht_hosts, non_ht_hosts))
        return ht_hosts, non_ht_hosts


class TestHTDisabled:

    @fixture(scope='class', autouse=True)
    def ensure_nonht(self, ht_and_nonht_hosts):
        ht_hosts, non_ht_hosts = ht_and_nonht_hosts
        if not non_ht_hosts:
            skip("No host with HT disabled")

        if ht_hosts:
            LOG.fixture_step(
                "Locking HT hosts to ensure only non-HT hypervisors available")
            HostsToRecover.add(ht_hosts, scope='class')
            for host_ in ht_hosts:
                host_helper.lock_host(host_, swact=True)

    @mark.parametrize(('vcpus', 'cpu_thread_policy', 'min_vcpus', 'expt_err'), [
        param(2, 'require', None, 'CPUThreadErr.HT_HOST_UNAVAIL'),
        param(3, 'require', None, 'CPUThreadErr.HT_HOST_UNAVAIL'),
        param(3, 'isolate', None, None),
        param(2, 'prefer', None, None),
    ])
    def test_boot_vm_cpu_thread_ht_disabled(self, vcpus, cpu_thread_policy,
                                            min_vcpus, expt_err):
        """
        Test boot vm with specified cpu thread policy when no HT host is
        available on system

        Args:
            vcpus (int): number of vcpus to set in flavor
            cpu_thread_policy (str): cpu thread policy in flavor extra spec
            min_vcpus (int): min_vpus in flavor extra spec
            expt_err (str|None): expected error message in nova show if any

        Skip condition:
            - All hosts are hyperthreading enabled on system

        Setups:
            - Find out HT hosts and non-HT_hosts on system   (module)
            - Enusre no HT hosts on system

        Test Steps:
            - Create a flavor with given number of vcpus
            - Set flavor extra specs as per test params
            - Get the host vcpu usage before booting vm
            - Attempt to boot a vm with above flavor
                - if expt_err is None:
                    - Ensure vm is booted on non-HT host for 'isolate'/'prefer'
                        vm
                    - Check vm-topology, host side vcpu usage, topology from
                        within the guest to ensure vm is properly booted
                - else, ensure expected error message is included in nova
                    show for 'require' vm

        Teardown:
            - Delete created vm, volume, flavor

        """

        LOG.tc_step("Create flavor with {} vcpus".format(vcpus))
        flavor_id = nova_helper.create_flavor(name='cpu_thread', vcpus=vcpus)[1]
        ResourceCleanup.add('flavor', flavor_id)

        specs = {FlavorSpec.CPU_THREAD_POLICY: cpu_thread_policy,
                 FlavorSpec.CPU_POLICY: 'dedicated'}
        if min_vcpus is not None:
            specs[FlavorSpec.MIN_VCPUS] = min_vcpus

        LOG.tc_step("Set following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor_id, **specs)

        LOG.tc_step("Attempt to boot a vm with the above flavor.")
        code, vm_id, msg = vm_helper.boot_vm(
            name='cpu_thread_{}'.format(cpu_thread_policy),
            flavor=flavor_id, fail_ok=True, cleanup='function')

        if expt_err:
            assert 1 == code, "Boot vm cli is not rejected. Details: " \
                              "{}".format(msg)
        else:
            assert 0 == code, "Boot vm with isolate policy was unsuccessful. " \
                              "Details: {}".format(msg)
