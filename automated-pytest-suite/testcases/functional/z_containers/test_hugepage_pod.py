#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import yaml

from pytest import fixture

from utils import cli
from utils.tis_log import LOG

from consts.proj_vars import ProjVar
from consts.auth import HostLinuxUser
from consts.auth import Tenant
from keywords import common
from keywords import host_helper
from keywords import kube_helper
from keywords import system_helper
from testfixtures.recover_hosts import HostsToRecover


def modify_yaml(file_dir, file_name, str_to_add, hugepage_value):
    """
    Add hugepages value to hugepages_pod.yaml file
    Args:
        file_dir(str): deployment file directory
        file_name(str): deployment file name
        str_to_add(str): 2M or 1G hugepage to add
        hugepage_value(str): hugepage value to assign to str_to_add
    Return(str):
        returns the file_dir and filename with modified values
    """
    with open("{}/{}".format(file_dir, file_name), 'r') as f:
        data = yaml.safe_load(f)
    data['spec']['containers'][0]['resources']['limits'][str_to_add] = hugepage_value
    newfile = "hugepages_pod_{}.yaml".format(hugepage_value)
    with open("{}/{}".format(ProjVar.get_var('LOG_DIR'), newfile), 'w') as f:
        yaml.dump(data, f)
    return ProjVar.get_var('LOG_DIR'), newfile


@fixture(scope="module")
def get_hugepage_pod_file():
    """
    Fixture used to return the hugepage deployment file

        - Get the compute-0 if exist, else standby controller
        - Check 2M hugepages configured, elsif check 1G is configured
            else lock,configure 2G of 1G hugepages and unlock host
        - Call modify_yaml function to modify the yaml
          file with the values
        - Modified file scps to host to deploy hugepages pod
        - Deletes the hugepages pod from the host after the test

    """
    if system_helper.is_aio_duplex():
        hostname = system_helper.get_standby_controller_name()
    else:
        hostname = system_helper.get_hypervisors()[0]
    LOG.fixture_step("Checking hugepage values on {}".format(hostname))
    proc_id = 0
    out = host_helper.get_host_memories(
        hostname, ('app_hp_avail_2M', 'app_hp_avail_1G'), proc_id)
    if out[proc_id][0] > 0:
        hugepage_val = "{}Mi".format(out[proc_id][0])
        hugepage_str = "hugepages-2Mi"
    elif out[proc_id][1] > 0:
        hugepage_val = "{}Gi".format(out[proc_id][1])
        hugepage_str = "hugepages-1Gi"
    else:
        hugepage_val = "{}Gi".format(2)
        cmd = "{} -1G {}".format(proc_id, 2)
        hugepage_str = "hugepages-1Gi"
        HostsToRecover.add(hostname)
        host_helper.lock_host(hostname)
        LOG.fixture_step("Configuring hugepage values {} on {}".format(
            hugepage_val, hostname))
        cli.system('host-memory-modify {} {}'.format(hostname, cmd), ssh_client=None,
                   auth_info=Tenant.get('admin_platform'))
        host_helper.unlock_host(hostname)
    LOG.fixture_step("{} {} pod will be configured on {} proc id {}".format(
        hugepage_str, hugepage_val, hostname, proc_id))
    file_dir, file_name = modify_yaml(
        "utils/test_files/", "hugepages_pod.yaml", hugepage_str, hugepage_val)
    source_path = "{}/{}".format(file_dir, file_name)
    home_dir = HostLinuxUser.get_home()
    common.scp_from_localhost_to_active_controller(
        source_path, dest_path=home_dir)
    yield file_name
    LOG.fixture_step("Delete hugepages pod")
    kube_helper.delete_resources(
        resource_names="hugepages-pod")


def test_hugepage_pod(get_hugepage_pod_file):
    """
    Verify hugepage pod is deployed and running
    Args:
        get_hugepage_pod_file: module fixture

    Steps:
        - Create hugepage pod with deployment file
        - Verifies hugepage pod is deployed and running

    Teardown:
        - Deletes the hugepages pod from the host
    """
    LOG.tc_step("Create hugepage pod with deployment file")
    kube_helper.exec_kube_cmd(
        sub_cmd="create -f {}".format(get_hugepage_pod_file))
    LOG.tc_step("Verifies hugepage pod is deployed and running")
    kube_helper.wait_for_pods_status(
        pod_names="hugepages-pod", namespace="default")
