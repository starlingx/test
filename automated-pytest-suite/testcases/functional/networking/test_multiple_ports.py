#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import copy

from pytest import fixture, mark, skip, param

from utils.tis_log import LOG

from consts.stx import FlavorSpec, VMStatus
from consts.reasons import SkipHostIf
from keywords import vm_helper, nova_helper, network_helper, glance_helper, \
    system_helper
from testfixtures.fixture_resources import ResourceCleanup


def id_params(val):
    if not isinstance(val, str):
        new_val = []
        for val_1 in val:
            if isinstance(val_1, (tuple, list)):
                val_1 = '_'.join([str(val_2).lower() for val_2 in val_1])
            new_val.append(val_1)
    else:
        new_val = val

    return '_'.join(new_val)


def _append_nics_for_net(vifs, net_id, nics):
    glance_vif = None
    nics = copy.deepcopy(nics)
    for vif in vifs:
        vif_ = vif.split(sep='_x')
        vif_model = vif_[0]
        if vif_model in ('e1000', 'rt18139'):
            glance_vif = vif_model
        iter_ = int(vif_[1]) if len(vif_) > 1 else 1
        for i in range(iter_):
            nic = {'net-id': net_id, 'vif-model': vif_model}
            nics.append(nic)

    return nics, glance_vif


def _boot_multiports_vm(flavor, mgmt_net_id, vifs, net_id, net_type, base_vm,
                        pcipt_seg_id=None):
    nics = [{'net-id': mgmt_net_id}]

    nics, glance_vif = _append_nics_for_net(vifs, net_id=net_id, nics=nics)
    img_id = None
    if glance_vif:
        img_id = glance_helper.create_image(name=glance_vif,
                                            hw_vif_model=glance_vif,
                                            cleanup='function')[1]

    LOG.tc_step("Boot a test_vm with following nics on same networks as "
                "base_vm: {}".format(nics))
    vm_under_test = \
        vm_helper.boot_vm(name='multiports', nics=nics, flavor=flavor,
                          cleanup='function',
                          image_id=img_id)[1]
    vm_helper.wait_for_vm_pingable_from_natbox(vm_under_test, fail_ok=False)

    if pcipt_seg_id:
        LOG.tc_step("Add vlan to pci-passthrough interface for VM.")
        vm_helper.add_vlan_for_vm_pcipt_interfaces(vm_id=vm_under_test,
                                                   net_seg_id=pcipt_seg_id,
                                                   init_conf=True)

    LOG.tc_step("Ping test_vm's own {} network ips".format(net_type))
    vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=vm_under_test,
                               net_types=net_type)

    vm_helper.configure_vm_vifs_on_same_net(vm_id=vm_under_test)

    LOG.tc_step(
        "Ping test_vm from base_vm to verify management and data networks "
        "connection")
    vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=base_vm,
                               net_types=['mgmt', net_type])

    return vm_under_test, nics


class TestMutiPortsBasic:
    @fixture(scope='class')
    def base_setup(self):

        flavor_id = nova_helper.create_flavor(name='dedicated')[1]
        ResourceCleanup.add('flavor', flavor_id, scope='class')

        extra_specs = {FlavorSpec.CPU_POLICY: 'dedicated'}
        nova_helper.set_flavor(flavor=flavor_id, **extra_specs)

        mgmt_net_id = network_helper.get_mgmt_net_id()
        tenant_net_id = network_helper.get_tenant_net_id()
        internal_net_id = network_helper.get_internal_net_id()

        nics = [{'net-id': mgmt_net_id},
                {'net-id': tenant_net_id},
                {'net-id': internal_net_id}]

        LOG.fixture_step(
            "(class) Boot a base vm with following nics: {}".format(nics))
        base_vm = vm_helper.boot_vm(name='multiports_base',
                                    flavor=flavor_id, nics=nics,
                                    cleanup='class',
                                    reuse_vol=False)[1]

        vm_helper.wait_for_vm_pingable_from_natbox(base_vm)
        vm_helper.ping_vms_from_vm(base_vm, base_vm, net_types='data')

        return base_vm, flavor_id, mgmt_net_id, tenant_net_id, internal_net_id

    @mark.parametrize('vifs', [
        param(('virtio_x4',), marks=mark.priorities('nightly', 'sx_nightly'))
    ], ids=id_params)
    def test_multiports_on_same_network_vm_actions(self, vifs, base_setup):
        """
        Test vm actions on vm with multiple ports with given vif models on
        the same tenant network

        Args:
            vifs (tuple): each item in the tuple is 1 nic to be added to vm
                with specified (vif_mode, pci_address)
            base_setup (list): test fixture to boot base vm

        Setups:
            - create a flavor with dedicated cpu policy (class)
            - choose one tenant network and one internal network to be used
            by test (class)
            - boot a base vm - vm1 with above flavor and networks, and ping
            it from NatBox (class)
            - Boot a vm under test - vm2 with above flavor and with multiple
            ports on same tenant network with base vm,
            and ping it from NatBox      (class)
            - Ping vm2's own data network ips        (class)
            - Ping vm2 from vm1 to verify management and data networks
            connection    (class)

        Test Steps:
            - Perform given actions on vm2 (migrate, start/stop, etc)
            - Verify pci_address preserves
            - Verify ping from vm1 to vm2 over management and data networks
            still works

        Teardown:
            - Delete created vms and flavor
        """
        base_vm, flavor, mgmt_net_id, tenant_net_id, internal_net_id = \
            base_setup

        vm_under_test, nics = _boot_multiports_vm(flavor=flavor,
                                                  mgmt_net_id=mgmt_net_id,
                                                  vifs=vifs,
                                                  net_id=tenant_net_id,
                                                  net_type='data',
                                                  base_vm=base_vm)

        for vm_actions in [['auto_recover'],
                           ['cold_migrate'],
                           ['pause', 'unpause'],
                           ['suspend', 'resume'],
                           ['hard_reboot']]:
            if vm_actions[0] == 'auto_recover':
                LOG.tc_step(
                    "Set vm to error state and wait for auto recovery "
                    "complete, then verify ping from "
                    "base vm over management and data networks")
                vm_helper.set_vm_state(vm_id=vm_under_test, error_state=True,
                                       fail_ok=False)
                vm_helper.wait_for_vm_values(vm_id=vm_under_test,
                                             status=VMStatus.ACTIVE,
                                             fail_ok=True, timeout=600)
            else:
                LOG.tc_step("Perform following action(s) on vm {}: {}".format(
                    vm_under_test, vm_actions))
                for action in vm_actions:
                    if 'migrate' in action and system_helper.is_aio_simplex():
                        continue

                    kwargs = {}
                    if action == 'hard_reboot':
                        action = 'reboot'
                        kwargs['hard'] = True
                    kwargs['action'] = action

                    vm_helper.perform_action_on_vm(vm_under_test, **kwargs)

            vm_helper.wait_for_vm_pingable_from_natbox(vm_under_test)

            # LOG.tc_step("Verify vm pci address preserved after {}".format(
            # vm_actions))
            # check_helper.check_vm_pci_addr(vm_under_test, nics)

            LOG.tc_step(
                "Verify ping from base_vm to vm_under_test over management "
                "and data networks still works "
                "after {}".format(vm_actions))
            vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=base_vm,
                                       net_types=['mgmt', 'data'])


class TestMutiPortsPCI:

    @fixture(scope='class')
    def base_setup_pci(self):
        LOG.fixture_step(
            "(class) Get an internal network that supports both pci-sriov and "
            "pcipt vif to boot vm")
        avail_pcipt_nets, is_cx4 = network_helper.get_pci_vm_network(
            pci_type='pci-passthrough',
            net_name='internal0-net', rtn_all=True)
        avail_sriov_nets, _ = network_helper.get_pci_vm_network(
            pci_type='pci-sriov',
            net_name='internal0-net', rtn_all=True)

        if not avail_pcipt_nets and not avail_sriov_nets:
            skip(SkipHostIf.PCI_IF_UNAVAIL)

        avail_nets = list(set(avail_pcipt_nets) & set(avail_sriov_nets))
        extra_pcipt_net = avail_pcipt_net = avail_sriov_net = None
        pcipt_seg_ids = {}
        if avail_nets:
            avail_net_name = avail_nets[-1]
            avail_net, segment_id = network_helper.get_network_values(
                network=avail_net_name,
                fields=('id', 'provider:segmentation_id'))
            internal_nets = [avail_net]
            pcipt_seg_ids[avail_net_name] = segment_id
            avail_pcipt_net = avail_sriov_net = avail_net
            LOG.info(
                "Internal network(s) selected for pcipt and sriov: {}".format(
                    avail_net_name))
        else:
            LOG.info("No internal network support both sriov and pcipt")
            internal_nets = []
            if avail_pcipt_nets:
                avail_pcipt_net_name = avail_pcipt_nets[-1]
                avail_pcipt_net, segment_id = network_helper.get_network_values(
                    network=avail_pcipt_net_name,
                    fields=('id', 'provider:segmentation_id'))
                internal_nets.append(avail_pcipt_net)
                pcipt_seg_ids[avail_pcipt_net_name] = segment_id
                LOG.info("pci-passthrough net: {}".format(avail_pcipt_net_name))
            if avail_sriov_nets:
                avail_sriov_net_name = avail_sriov_nets[-1]
                avail_sriov_net = network_helper.get_net_id_from_name(
                    avail_sriov_net_name)
                internal_nets.append(avail_sriov_net)
                LOG.info("pci-sriov net: {}".format(avail_sriov_net_name))

        mgmt_net_id = network_helper.get_mgmt_net_id()
        tenant_net_id = network_helper.get_tenant_net_id()
        base_nics = [{'net-id': mgmt_net_id}, {'net-id': tenant_net_id}]
        nics = base_nics + [{'net-id': net_id} for net_id in internal_nets]

        if avail_pcipt_nets and is_cx4:
            extra_pcipt_net_name = avail_nets[0] if avail_nets else \
                avail_pcipt_nets[0]
            extra_pcipt_net, seg_id = network_helper.get_network_values(
                network=extra_pcipt_net_name,
                fields=('id', 'provider:segmentation_id'))
            if extra_pcipt_net not in internal_nets:
                nics.append({'net-id': extra_pcipt_net})
                pcipt_seg_ids[extra_pcipt_net_name] = seg_id

        LOG.fixture_step("(class) Create a flavor with dedicated cpu policy.")
        flavor_id = \
            nova_helper.create_flavor(name='dedicated', vcpus=2, ram=2048,
                                      cleanup='class')[1]
        extra_specs = {FlavorSpec.CPU_POLICY: 'dedicated',
                       FlavorSpec.PCI_NUMA_AFFINITY: 'preferred'}
        nova_helper.set_flavor(flavor=flavor_id, **extra_specs)

        LOG.fixture_step(
            "(class) Boot a base pci vm with following nics: {}".format(nics))
        base_vm_pci = \
            vm_helper.boot_vm(name='multiports_pci_base', flavor=flavor_id,
                              nics=nics, cleanup='class')[1]

        LOG.fixture_step("(class) Ping base PCI vm interfaces")
        vm_helper.wait_for_vm_pingable_from_natbox(base_vm_pci)
        vm_helper.ping_vms_from_vm(to_vms=base_vm_pci, from_vm=base_vm_pci,
                                   net_types=['data', 'internal'])

        return base_vm_pci, flavor_id, base_nics, avail_sriov_net, \
            avail_pcipt_net, pcipt_seg_ids, extra_pcipt_net

    @mark.parametrize('vifs', [
        param(('virtio', 'pci-sriov', 'pci-passthrough'), marks=mark.p3),
        param(('pci-passthrough',), marks=mark.nightly),
        param(('pci-sriov',), marks=mark.nightly),
    ], ids=id_params)
    def test_multiports_on_same_network_pci_vm_actions(self, base_setup_pci,
                                                       vifs):
        """
        Test vm actions on vm with multiple ports with given vif models on
        the same tenant network

        Args:
            base_setup_pci (tuple): base_vm_pci, flavor, mgmt_net_id,
                tenant_net_id, internal_net_id, seg_id
            vifs (list): list of vifs to add to same internal net

        Setups:
            - Create a flavor with dedicated cpu policy (class)
            - Choose management net, one tenant net, and internal0-net1 to be
            used by test (class)
            - Boot a base pci-sriov vm - vm1 with above flavor and networks,
            ping it from NatBox (class)
            - Ping vm1 from itself over data, and internal networks

        Test Steps:
            - Boot a vm under test - vm2 with above flavor and with multiple
            ports on same tenant network with vm1,
                and ping it from NatBox
            - Ping vm2's own data and internal network ips
            - Ping vm2 from vm1 to verify management and data networks
            connection
            - Perform one of the following actions on vm2
                - set to error/ wait for auto recovery
                - suspend/resume
                - cold migration
                - pause/unpause
            - Update vlan interface to proper eth if pci-passthrough device
            moves to different eth
            - Verify ping from vm1 to vm2 over management and data networks
            still works
            - Repeat last 3 steps with different vm actions

        Teardown:
            - Delete created vms and flavor
        """

        base_vm_pci, flavor, base_nics, avail_sriov_net, avail_pcipt_net, \
            pcipt_seg_ids, extra_pcipt_net = base_setup_pci

        pcipt_included = False
        internal_net_id = None
        for vif in vifs:
            if not isinstance(vif, str):
                vif = vif[0]
            if 'pci-passthrough' in vif:
                if not avail_pcipt_net:
                    skip(SkipHostIf.PCIPT_IF_UNAVAIL)
                internal_net_id = avail_pcipt_net
                pcipt_included = True
                continue
            elif 'pci-sriov' in vif:
                if not avail_sriov_net:
                    skip(SkipHostIf.SRIOV_IF_UNAVAIL)
                internal_net_id = avail_sriov_net

        assert internal_net_id, "test script error. Internal net should have " \
                                "been determined."

        nics, glance_vif = _append_nics_for_net(vifs, net_id=internal_net_id,
                                                nics=base_nics)
        if pcipt_included and extra_pcipt_net:
            nics.append(
                {'net-id': extra_pcipt_net, 'vif-model': 'pci-passthrough'})

        img_id = None
        if glance_vif:
            img_id = glance_helper.create_image(name=glance_vif,
                                                hw_vif_model=glance_vif,
                                                cleanup='function')[1]

        LOG.tc_step("Boot a vm with following vifs on same internal net: "
                    "{}".format(vifs))
        vm_under_test = vm_helper.boot_vm(name='multiports_pci',
                                          nics=nics, flavor=flavor,
                                          cleanup='function',
                                          reuse_vol=False, image_id=img_id)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm_under_test, fail_ok=False)

        if pcipt_included:
            LOG.tc_step("Add vlan to pci-passthrough interface for VM.")
            vm_helper.add_vlan_for_vm_pcipt_interfaces(vm_id=vm_under_test,
                                                       net_seg_id=pcipt_seg_ids,
                                                       init_conf=True)

        LOG.tc_step("Ping vm's own data and internal network ips")
        vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=vm_under_test,
                                   net_types=['data', 'internal'])

        LOG.tc_step(
            "Ping vm_under_test from base_vm over management, data, "
            "and internal networks")
        vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=base_vm_pci,
                                   net_types=['mgmt', 'data', 'internal'])

        for vm_actions in [['auto_recover'], ['cold_migrate'],
                           ['pause', 'unpause'], ['suspend', 'resume']]:
            if 'auto_recover' in vm_actions:
                LOG.tc_step(
                    "Set vm to error state and wait for auto recovery "
                    "complete, "
                    "then verify ping from base vm over management and "
                    "internal networks")
                vm_helper.set_vm_state(vm_id=vm_under_test, error_state=True,
                                       fail_ok=False)
                vm_helper.wait_for_vm_values(vm_id=vm_under_test,
                                             status=VMStatus.ACTIVE,
                                             fail_ok=False, timeout=600)
            else:
                LOG.tc_step("Perform following action(s) on vm {}: {}".format(
                    vm_under_test, vm_actions))
                for action in vm_actions:
                    vm_helper.perform_action_on_vm(vm_under_test, action=action)

            vm_helper.wait_for_vm_pingable_from_natbox(vm_id=vm_under_test)
            if pcipt_included:
                LOG.tc_step(
                    "Bring up vlan interface for pci-passthrough vm {}.".format(
                        vm_under_test))
                vm_helper.add_vlan_for_vm_pcipt_interfaces(
                    vm_id=vm_under_test, net_seg_id=pcipt_seg_ids)

            LOG.tc_step(
                "Verify ping from base_vm to vm_under_test over management "
                "and internal networks still works "
                "after {}".format(vm_actions))
            vm_helper.ping_vms_from_vm(to_vms=vm_under_test,
                                       from_vm=base_vm_pci,
                                       net_types=['mgmt', 'internal'])

    @mark.parametrize('vifs', [
        ('pci-sriov',),
        ('pci-passthrough',),
    ], ids=id_params)
    def test_multiports_on_same_network_pci_evacuate_vm(self, base_setup_pci,
                                                        vifs):
        """
        Test evacuate vm with multiple ports on same network

        Args:
            base_setup_pci (tuple): base vm id, vm under test id, segment id
                for internal0-net1
            vifs (list): list of vifs to add to same internal net

        Setups:
            - create a flavor with dedicated cpu policy (module)
            - choose one tenant network and one internal network to be used
            by test (module)
            - boot a base vm - vm1 with above flavor and networks, and ping
            it from NatBox (module)
            - Boot a vm under test - vm2 with above flavor and with multiple
            ports on same tenant network with base vm,
            and ping it from NatBox     (class)
            - Ping vm2's own data network ips       (class)
            - Ping vm2 from vm1 to verify management and internal networks
            connection   (class)

        Test Steps:
            - Reboot vm2 host
            - Wait for vm2 to be evacuated to other host
            - Wait for vm2 pingable from NatBox
            - Verify ping from vm1 to vm2 over management and internal
            networks still works

        Teardown:
            - Delete created vms and flavor
        """
        base_vm_pci, flavor, base_nics, avail_sriov_net, avail_pcipt_net, \
            pcipt_seg_ids, extra_pcipt_net = base_setup_pci

        internal_net_id = None
        pcipt_included = False
        nics = copy.deepcopy(base_nics)
        if 'pci-passthrough' in vifs:
            if not avail_pcipt_net:
                skip(SkipHostIf.PCIPT_IF_UNAVAIL)
            pcipt_included = True
            internal_net_id = avail_pcipt_net
            if extra_pcipt_net:
                nics.append(
                    {'net-id': extra_pcipt_net, 'vif-model': 'pci-passthrough'})
        if 'pci-sriov' in vifs:
            if not avail_sriov_net:
                skip(SkipHostIf.SRIOV_IF_UNAVAIL)
            internal_net_id = avail_sriov_net
        assert internal_net_id, "test script error. sriov or pcipt has to be " \
                                "included."

        for vif in vifs:
            nics.append({'net-id': internal_net_id, 'vif-model': vif})

        LOG.tc_step(
            "Boot a vm with following vifs on same network internal0-net1: "
            "{}".format(vifs))
        vm_under_test = vm_helper.boot_vm(name='multiports_pci_evac',
                                          nics=nics, flavor=flavor,
                                          cleanup='function',
                                          reuse_vol=False)[1]
        vm_helper.wait_for_vm_pingable_from_natbox(vm_under_test, fail_ok=False)

        if pcipt_included:
            LOG.tc_step("Add vlan to pci-passthrough interface.")
            vm_helper.add_vlan_for_vm_pcipt_interfaces(vm_id=vm_under_test,
                                                       net_seg_id=pcipt_seg_ids,
                                                       init_conf=True)

        LOG.tc_step("Ping vm's own data and internal network ips")
        vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=vm_under_test,
                                   net_types=['data', 'internal'])
        vm_helper.configure_vm_vifs_on_same_net(vm_id=vm_under_test)

        LOG.tc_step(
            "Ping vm_under_test from base_vm over management, data, and "
            "internal networks")
        vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=base_vm_pci,
                                   net_types=['mgmt', 'data', 'internal'])

        host = vm_helper.get_vm_host(vm_under_test)

        LOG.tc_step("Reboot vm host {}".format(host))
        vm_helper.evacuate_vms(host=host, vms_to_check=vm_under_test,
                               ping_vms=True)

        if pcipt_included:
            LOG.tc_step(
                "Add/Check vlan interface is added to pci-passthrough device "
                "for vm {}.".format(vm_under_test))
            vm_helper.add_vlan_for_vm_pcipt_interfaces(vm_id=vm_under_test,
                                                       net_seg_id=pcipt_seg_ids)

        LOG.tc_step(
            "Verify ping from base_vm to vm_under_test over management and "
            "internal networks still works after evacuation.")
        vm_helper.ping_vms_from_vm(to_vms=vm_under_test, from_vm=base_vm_pci,
                                   net_types=['mgmt', 'internal'])
