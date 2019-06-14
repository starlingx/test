#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import fixture

from consts.stx import GuestImages
from keywords import nova_helper, glance_helper, keystone_helper, \
    container_helper
from utils.tis_log import LOG


# Session fixture to add affinitiy and anti-affinity server group
@fixture(scope='session')
def server_groups():
    def create_server_groups(soft=True, auth_info=None):
        srv_grps_tenant = []

        LOG.fixture_step(
            '(session) Creating affinity and anti-affinity server groups with '
            'best_effort set to {}'.
            format(soft))
        for policy in ['affinity', 'anti_affinity']:
            if soft:
                policy = 'soft_{}'.format(policy)

            name = 'srv_group_{}'.format(policy)
            srv_grp_id = \
                nova_helper.create_server_group(name=name, policy=policy,
                                                auth_info=auth_info,
                                                rtn_exist=True)[1]
            srv_grps_tenant.append(srv_grp_id)
        return srv_grps_tenant

    return create_server_groups


# Session fixture to add stxauto aggregate with stxauto availability zone
@fixture(scope='session')
def add_stxauto_zone(request):
    LOG.fixture_step(
        "(session) Add stxauto aggregate and stxauto availability zone")
    nova_helper.create_aggregate(name='stxauto', avail_zone='stxauto',
                                 check_first=True)

    def remove_aggregate():
        LOG.fixture_step("(session) Delete stxauto aggregate")
        nova_helper.delete_aggregates('stxauto')

    request.addfinalizer(remove_aggregate)

    # return name of aggregate/availability zone
    return 'stxauto'


# Fixtures to add admin role to primary tenant
@fixture(scope='module')
def add_admin_role_module(request):
    __add_admin_role(scope='module', request=request)


@fixture(scope='class')
def add_admin_role_class(request):
    __add_admin_role(scope='class', request=request)


@fixture(scope='function')
def add_admin_role_func(request):
    __add_admin_role(scope='function', request=request)


def __add_admin_role(scope, request):
    LOG.fixture_step(
        "({}) Add admin role to user under primary tenant".format(scope))
    code = keystone_helper.add_or_remove_role(add_=True, role='admin')[0]

    def remove_admin():
        if code != -1:
            LOG.fixture_step(
                "({}) Remove admin role from user under primary tenant".format(
                    scope))
            keystone_helper.add_or_remove_role(add_=False, role='admin')

    request.addfinalizer(remove_admin)


@fixture(scope='session')
def ubuntu14_image():
    return __create_image('ubuntu_14', 'session')


@fixture(scope='session')
def ubuntu12_image():
    return __create_image('ubuntu_12', 'session')


@fixture(scope='session')
def centos7_image():
    return __create_image('centos_7', 'session')


@fixture(scope='session')
def centos6_image():
    return __create_image('centos_6', 'session')


@fixture(scope='session')
def opensuse11_image():
    return __create_image('opensuse_11', 'session')


@fixture(scope='session')
def opensuse12_image():
    return __create_image('opensuse_12', 'session')


@fixture(scope='session')
def opensuse13_image():
    return __create_image('opensuse_13', 'session')


@fixture(scope='session')
def rhel6_image():
    return __create_image('rhel_6', 'session')


@fixture(scope='session')
def rhel7_image():
    return __create_image('rhel_7', 'session')


@fixture(scope='session', autouse=True)
def default_glance_image():
    if not container_helper.is_stx_openstack_deployed():
        return None
    return __create_image(None, 'session')


@fixture(scope='session', autouse=False)
def cgcs_guest_image():
    return __create_image('cgcs-guest', 'session')


def __create_image(img_os, scope):
    if not img_os:
        img_os = GuestImages.DEFAULT['guest']

    LOG.fixture_step(
        "({}) Get or create a glance image with {} guest OS".format(scope,
                                                                    img_os))
    img_info = GuestImages.IMAGE_FILES[img_os]
    img_id = glance_helper.get_image_id_from_name(img_os, strict=True)
    if not img_id:
        if img_info[0] is not None:
            image_path = glance_helper.scp_guest_image(img_os=img_os)
        else:
            img_dir = GuestImages.DEFAULT['image_dir']
            image_path = "{}/{}".format(img_dir, img_info[2])

        disk_format = 'raw' if img_os in ['cgcs-guest', 'tis-centos-guest',
                                          'vxworks'] else 'qcow2'
        img_id = \
            glance_helper.create_image(name=img_os,
                                       source_image_file=image_path,
                                       disk_format=disk_format,
                                       container_format='bare',
                                       cleanup=scope)[1]

    return img_id
