#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, param

from utils.tis_log import LOG

from consts.stx import FlavorSpec, ImageMetadata, GuestImages
from consts.cli_errs import CPUPolicyErr  # used by eval

from keywords import nova_helper, vm_helper, glance_helper, cinder_helper, \
    check_helper, host_helper
from testfixtures.fixture_resources import ResourceCleanup


@mark.parametrize(
    ('flv_vcpus', 'flv_pol', 'img_pol', 'boot_source', 'expt_err'), [
        param(3, None, 'shared', 'image', None, marks=mark.p3),
        param(4, 'dedicated', 'dedicated', 'volume', None, marks=mark.p3),
        param(1, 'dedicated', None, 'image', None, marks=mark.p3),
        param(1, 'shared', 'shared', 'volume', None, marks=mark.p3),
        param(2, 'shared', None, 'image', None, marks=mark.p3),
        param(3, 'dedicated', 'shared', 'volume', None,
              marks=mark.domain_sanity),
        param(1, 'shared', 'dedicated', 'image',
              'CPUPolicyErr.CONFLICT_FLV_IMG', marks=mark.p3),
    ])
def test_boot_vm_cpu_policy_image(flv_vcpus, flv_pol, img_pol, boot_source,
                                  expt_err):
    LOG.tc_step("Create flavor with {} vcpus".format(flv_vcpus))
    flavor_id = nova_helper.create_flavor(name='cpu_pol_{}'.format(flv_pol),
                                          vcpus=flv_vcpus)[1]
    ResourceCleanup.add('flavor', flavor_id)

    if flv_pol is not None:
        specs = {FlavorSpec.CPU_POLICY: flv_pol}

        LOG.tc_step("Set following extra specs: {}".format(specs))
        nova_helper.set_flavor(flavor_id, **specs)

    if img_pol is not None:
        image_meta = {ImageMetadata.CPU_POLICY: img_pol}
        LOG.tc_step(
            "Create image with following metadata: {}".format(image_meta))
        image_id = glance_helper.create_image(
            name='cpu_pol_{}'.format(img_pol), cleanup='function',
            **image_meta)[1]
    else:
        image_id = glance_helper.get_image_id_from_name(
            GuestImages.DEFAULT['guest'], strict=True)

    if boot_source == 'volume':
        LOG.tc_step("Create a volume from image")
        source_id = cinder_helper.create_volume(name='cpu_pol_img',
                                                source_id=image_id)[1]
        ResourceCleanup.add('volume', source_id)
    else:
        source_id = image_id

    prev_cpus = host_helper.get_vcpus_for_computes(field='used_now')

    LOG.tc_step("Attempt to boot a vm from above {} with above flavor".format(
        boot_source))
    code, vm_id, msg = vm_helper.boot_vm(name='cpu_pol', flavor=flavor_id,
                                         source=boot_source,
                                         source_id=source_id, fail_ok=True,
                                         cleanup='function')

    # check for negative tests
    if expt_err is not None:
        LOG.tc_step(
            "Check VM failed to boot due to conflict in flavor and image.")
        assert 4 == code, "Expect boot vm cli reject and no vm booted. " \
                          "Actual: {}".format(msg)
        assert eval(expt_err) in msg, \
            "Expected error message is not found in cli return."
        return  # end the test for negative cases

    # Check for positive tests
    LOG.tc_step("Check vm is successfully booted.")
    assert 0 == code, "Expect vm boot successfully. Actual: {}".format(msg)

    # Calculate expected policy:
    expt_cpu_pol = flv_pol if flv_pol else img_pol
    expt_cpu_pol = expt_cpu_pol if expt_cpu_pol else 'shared'

    vm_host = vm_helper.get_vm_host(vm_id)
    check_helper.check_topology_of_vm(vm_id, vcpus=flv_vcpus,
                                      cpu_pol=expt_cpu_pol, vm_host=vm_host,
                                      prev_total_cpus=prev_cpus[vm_host])


@mark.parametrize(('flv_vcpus', 'cpu_pol', 'pol_source', 'boot_source'), [
    param(4, None, 'flavor', 'image', marks=mark.p2),
    param(2, 'dedicated', 'flavor', 'volume', marks=mark.domain_sanity),
    param(3, 'shared', 'flavor', 'volume', marks=mark.p2),
    param(1, 'dedicated', 'flavor', 'image', marks=mark.p2),
    param(2, 'dedicated', 'image', 'volume', marks=mark.nightly),
    param(3, 'shared', 'image', 'volume', marks=mark.p2),
    param(1, 'dedicated', 'image', 'image', marks=mark.domain_sanity),
])
def test_cpu_pol_vm_actions(flv_vcpus, cpu_pol, pol_source, boot_source):
    LOG.tc_step("Create flavor with {} vcpus".format(flv_vcpus))
    flavor_id = nova_helper.create_flavor(name='cpu_pol', vcpus=flv_vcpus)[1]
    ResourceCleanup.add('flavor', flavor_id)

    image_id = glance_helper.get_image_id_from_name(
        GuestImages.DEFAULT['guest'], strict=True)
    if cpu_pol is not None:
        if pol_source == 'flavor':
            specs = {FlavorSpec.CPU_POLICY: cpu_pol}

            LOG.tc_step("Set following extra specs: {}".format(specs))
            nova_helper.set_flavor(flavor_id, **specs)
        else:
            image_meta = {ImageMetadata.CPU_POLICY: cpu_pol}
            LOG.tc_step(
                "Create image with following metadata: {}".format(image_meta))
            image_id = glance_helper.create_image(
                name='cpu_pol_{}'.format(cpu_pol), cleanup='function',
                **image_meta)[1]
    if boot_source == 'volume':
        LOG.tc_step("Create a volume from image")
        source_id = cinder_helper.create_volume(name='cpu_pol_{}'.format(cpu_pol),
                                                source_id=image_id)[1]
        ResourceCleanup.add('volume', source_id)
    else:
        source_id = image_id

    prev_cpus = host_helper.get_vcpus_for_computes(field='used_now')

    LOG.tc_step(
        "Boot a vm from {} with above flavor and check vm topology is as "
        "expected".format(boot_source))
    vm_id = vm_helper.boot_vm(name='cpu_pol_{}_{}'.format(cpu_pol, flv_vcpus),
                              flavor=flavor_id, source=boot_source,
                              source_id=source_id, cleanup='function')[1]

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    vm_host = vm_helper.get_vm_host(vm_id)
    check_helper.check_topology_of_vm(vm_id, vcpus=flv_vcpus, cpu_pol=cpu_pol,
                                      vm_host=vm_host,
                                      prev_total_cpus=prev_cpus[vm_host])

    LOG.tc_step("Suspend/Resume vm and check vm topology stays the same")
    vm_helper.suspend_vm(vm_id)
    vm_helper.resume_vm(vm_id)

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    check_helper.check_topology_of_vm(vm_id, vcpus=flv_vcpus, cpu_pol=cpu_pol,
                                      vm_host=vm_host,
                                      prev_total_cpus=prev_cpus[vm_host])

    LOG.tc_step("Stop/Start vm and check vm topology stays the same")
    vm_helper.stop_vms(vm_id)
    vm_helper.start_vms(vm_id)

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    prev_siblings = check_helper.check_topology_of_vm(
        vm_id, vcpus=flv_vcpus, cpu_pol=cpu_pol, vm_host=vm_host,
        prev_total_cpus=prev_cpus[vm_host])[1]

    LOG.tc_step("Live migrate vm and check vm topology stays the same")
    vm_helper.live_migrate_vm(vm_id=vm_id)

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    vm_host = vm_helper.get_vm_host(vm_id)
    prev_siblings = prev_siblings if cpu_pol == 'dedicated' else None
    check_helper.check_topology_of_vm(vm_id, vcpus=flv_vcpus, cpu_pol=cpu_pol,
                                      vm_host=vm_host,
                                      prev_total_cpus=prev_cpus[vm_host],
                                      prev_siblings=prev_siblings)

    LOG.tc_step("Cold migrate vm and check vm topology stays the same")
    vm_helper.cold_migrate_vm(vm_id=vm_id)

    vm_helper.wait_for_vm_pingable_from_natbox(vm_id)
    vm_host = vm_helper.get_vm_host(vm_id)
    check_helper.check_topology_of_vm(vm_id, vcpus=flv_vcpus, cpu_pol=cpu_pol,
                                      vm_host=vm_host,
                                      prev_total_cpus=prev_cpus[vm_host])
