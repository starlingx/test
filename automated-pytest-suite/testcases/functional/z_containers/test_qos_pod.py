#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import json

from pytest import fixture
from pytest import mark

from utils.tis_log import LOG
from keywords import common
from keywords import kube_helper
from consts.auth import HostLinuxUser


@fixture(scope='module')
def copy_pod_yamls():
    home_dir = HostLinuxUser.get_home()
    filename = "qos_deployment.yaml"
    ns = "qos"
    LOG.fixture_step("Copying deployment yaml file")
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/{}".format(filename), dest_path=home_dir)
    kube_helper.exec_kube_cmd(
        sub_cmd="create -f {}".format(filename))
    yield ns
    LOG.fixture_step("Delete all pods in namespace {}".format(ns))
    kube_helper.exec_kube_cmd(
        sub_cmd="delete pods --all --namespace={}".format(ns))
    LOG.fixture_step("Delete the namespace")
    kube_helper.exec_kube_cmd(sub_cmd="delete namespace {}".format(ns))


@mark.parametrize('expected,pod', [("guaranteed", "qos-pod-1"),
                                   ("burstable", "qos-pod-2"),
                                   ("besteffort", "qos-pod-3"),
                                   ("burstable", "qos-pod-with-two-containers")])
def test_qos_class(copy_pod_yamls, expected, pod):
    """
    Testing the Qos class for pods
    Args:
        copy_pod_yamls : module fixture
        expected : test param
        pod : test param
    Setup:
        - Scp qos pod yaml files(module)
        - Create the deployment of namespace and qos pods
    Steps:
        - Check status of the pod
        - Check the qos-class type is as expected
    Teardown:
        - Delete all pods in the namespace
        - Delete the namespace

    """
    ns = copy_pod_yamls
    kube_helper.wait_for_pods_status(pod_names=pod, namespace=ns)
    _, out = kube_helper.exec_kube_cmd(
        sub_cmd="get pod {} --namespace={} --output=json".format(pod, ns))
    out = json.loads(out)
    LOG.tc_step("pod qos class is {} and expected is {}".format(
        out["status"]["qosClass"], expected))
    assert out["status"]["qosClass"].lower() == expected
