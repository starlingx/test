#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture, mark

from consts import horizon
from consts.auth import Tenant
from consts.stx import GuestImages
from keywords import nova_helper
from utils.tis_log import LOG
from utils.horizon import helper
from utils.horizon.regions import messages
from utils.horizon.pages.project.compute import instancespage


@fixture(scope='function')
def instances_pg(tenant_home_pg_container, request):
    LOG.fixture_step('Go to Project > Compute > Instance')
    instance_name = helper.gen_resource_name('instance')
    instances_pg = instancespage.InstancesPage(
        tenant_home_pg_container.driver, port=tenant_home_pg_container.port)
    instances_pg.go_to_target_page()

    def teardown():
        LOG.fixture_step('Back to instance page')
        if instances_pg.is_instance_present(instance_name):
            instances_pg.delete_instance_by_row(instance_name)
        instances_pg.go_to_target_page()

    request.addfinalizer(teardown)

    return instances_pg, instance_name


@mark.sanity
@mark.cpe_sanity
@mark.sx_sanity
def test_horizon_create_delete_instance(instances_pg):
    """
    Test the instance creation and deletion functionality:

    Setups:
        - Login as Tenant
        - Go to Project > Compute > Instance

    Teardown:
        - Back to Instances page
        - Logout

    Test Steps:
        - Create a new instance
        - Verify the instance appears in the instances table as active
        - Delete the newly lunched instance
        - Verify the instance does not appear in the table after deletion
    """
    instances_pg, instance_name = instances_pg

    mgmt_net_name = '-'.join([Tenant.get_primary()['tenant'], 'mgmt', 'net'])
    flavor_name = nova_helper.get_basic_flavor(rtn_id=False)
    guest_img = GuestImages.DEFAULT['guest']

    LOG.tc_step('Create new instance {}'.format(instance_name))
    instances_pg.create_instance(instance_name,
                                 boot_source_type='Image',
                                 source_name=guest_img,
                                 flavor_name=flavor_name,
                                 network_names=mgmt_net_name,
                                 create_new_volume=False)
    assert not instances_pg.find_message_and_dismiss(messages.ERROR)

    LOG.tc_step('Verify the instance appears in the instances table as active')
    assert instances_pg.is_instance_active(instance_name)

    LOG.tc_step('Delete instance {}'.format(instance_name))
    instances_pg.delete_instance_by_row(instance_name)
    assert instances_pg.find_message_and_dismiss(messages.INFO)
    assert not instances_pg.find_message_and_dismiss(messages.ERROR)

    LOG.tc_step(
        'Verify the instance does not appear in the table after deletion')
    assert instances_pg.is_instance_deleted(instance_name)
    horizon.test_result = True
