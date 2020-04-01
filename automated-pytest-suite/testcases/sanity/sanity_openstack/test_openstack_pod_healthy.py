###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Check the health of PODs services; update and apply the helm chart via system application-apply.
# Author(s): Mihail-Laurentiu Trica mihai-laurentiu.trica@intel.com
###

import os
from pytest import mark

from keywords import common, container_helper, kube_helper
from utils.clients.ssh import ControllerClient

POD_YAML = "testpod.yaml"
POD_NAME = "testpod"
CHART_MANIFEST = "helm-charts-manifest.tgz"
STX_HOME = "/home/sysadmin/"
DELAY = 60


# OpenStack pods healthy
@mark.robotsanity
def test_openstack_pods_healthy():
    """
    Check the health of the OpenStack pods: healthy, running or in completed state
    """
    application_status = container_helper.get_apps(application="stx-openstack")[0]
    assert application_status == "applied", "System status is not in state applied"
    command_health = kube_helper.wait_for_pods_healthy(namespace="stx-openstack")
    assert command_health is None, "Check PODs health has failed"


# Reapply STX OpenStack
@mark.robotsanity
def test_reapply_stx_openstack():
    """
    Re-apply stx openstack application without any modification to helm charts.
    """
    # Modified the check_interval set on robot test from 300 t0 30 to shorten the timeouts
    application_status = container_helper.apply_app(app_name="stx-openstack", applied_timeout=5400,
                                                    check_interval=30)[0]
    assert application_status == 0, "Reapply STX OpenStack has failed"


# STX OpenStack Override Update Reset
@mark.robotsanity
def test_stx_openstack_override_update_reset():
    """
    Helm override for OpenStack nova chart and reset.
    """
    # Helm Override OpenStack
    args_override_pairs = {"conf.nova.DEFAULT.foo": "bar"}
    app_name_override = "stx-openstack"
    chart_override = "nova"
    namespace_override = "openstack"
    command_override = container_helper.update_helm_override(chart=chart_override,
                                                             namespace=namespace_override,
                                                             app_name=app_name_override,
                                                             kv_pairs=args_override_pairs)[0]
    assert command_override == 0, "Helm override has failed"
    # System Application Apply stx-openstack
    test_reapply_stx_openstack()
    # Check Helm Override OpenStack
    labels_override = "component=compute"
    nova_compute_controllers = kube_helper.get_pods(
        field="NAME", all_namespaces=True, labels=labels_override)
    conf_path = "/etc/nova/nova.conf"
    for nova_compute_controller in nova_compute_controllers:
        cmd_str = "grep foo {}".format(conf_path)
        code, command_output = kube_helper.exec_cmd_in_container(cmd=cmd_str,
                                                                 pod=nova_compute_controller,
                                                                 namespace=namespace_override)
        assert code == 0, "Controller kubectl command has exited with an error"
        assert "foo = bar" in command_output, "Check Helm Override OpenStack for {} " \
                                              "has failed".format(nova_compute_controller)


# Kube System Services
@mark.robotsanity
def test_kube_system_services():
    """
    Check pods status and kube-system services are displayed.
    """
    # Check PODs Health
    command_health = kube_helper.wait_for_pods_healthy(namespace="stx-openstack")
    assert command_health is None, "Check PODs health has failed"
    # Check Kube System Services
    services_to_check = ['ingress', 'ingress-error-pages', 'ingress-exporter', 'kube-dns',
                         'tiller-deploy']
    services_to_check.sort()
    services_list = kube_helper.get_resources(field="NAME", namespace="kube-system",
                                              resource_type="service")
    services_list.sort()
    for i in services_list:
        i = ''.join(i)
    assert services_to_check == services_list, "One or more services are missing from the list"


# Create Check Delete POD
@mark.robotsanity
def test_create_check_delete_pod():
    """
    Launch a POD via kubectl, wait until it is active, then delete it.
    """
    # Create pod
    test_pod_yaml_path = os.path.join(os.getcwd(), "testcases/sanity/sanity_platform", POD_YAML)
    stx_path = STX_HOME + POD_YAML
    current_controller = ControllerClient.get_active_controller()
    if not current_controller.file_exists(test_pod_yaml_path):
        common.scp_from_localhost_to_active_controller(
            source_path=test_pod_yaml_path, dest_path=stx_path, timeout=60, is_dir=False)
    sub_cmd_str = "create -f"
    code, output_create = kube_helper.exec_kube_cmd(
        sub_cmd=sub_cmd_str, args=stx_path, con_ssh=current_controller)
    assert code == 0, "Controller kubectl create has exited with an error"
    assert output_create == "pod/testpod created", "Creation of testpod has failed"
    timer = DELAY
    while timer != 0:
        command_check = kube_helper.get_pods(field="STATUS", all_namespaces=True,
                                             pod_names=POD_NAME)
        if command_check == "Running":
            assert command_check == "Running"
            timer = 0
        else:
            timer -= 5
    # Delete pod
    code, output_delete = kube_helper.delete_resources(resource_names=POD_NAME,
                                                       resource_types="pod",
                                                       con_ssh=current_controller,
                                                       check_both_controllers=True)
    assert code == 0, "Controller kubectl delete has exited with an error"
    assert output_delete is None, "Pod was not successfully deleted"
