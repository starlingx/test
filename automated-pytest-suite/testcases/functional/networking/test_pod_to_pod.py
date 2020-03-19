#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import copy

from pytest import mark, fixture

from utils.tis_log import LOG
from utils import rest

from consts.proj_vars import ProjVar
from consts.auth import HostLinuxUser
from keywords import system_helper, kube_helper, common


@fixture(scope="class")
def deploy_test_pods(request):
    """
    Fixture to deploy the server app,client app and returns serverips & client pods
        - Label the nodes and add node selector to the deployment files
            if not simplex system
        - Copy the deployment files from localhost to active controller
        - Deploy server pod
        - Deploy client pods
        - Get the server pods and client pods
        - Get the server pods and client pods status before test begins
        - Delete the service
        - Delete the server pod deployment
        - Delete the client pods
        - Remove the labels on the nodes if not simplex
    """
    server_dep_file = "server_pod.yaml"
    home_dir = HostLinuxUser.get_home()
    service_name = "test-service"

    client_pod1_name = "client-pod1"
    client_pod2_name = "client-pod2"

    server_dep_file_path = "utils/test_files/server_pod_deploy.yaml"
    client_pod_template_file_path = "utils/test_files/client_pod.yaml"

    server_pod_dep_data = common.get_yaml_data(server_dep_file_path)
    client_pod1_data = common.get_yaml_data(client_pod_template_file_path)
    client_pod2_data = copy.deepcopy(client_pod1_data)

    client_pod1_data['metadata']['name'] = client_pod1_name
    client_pod2_data['metadata']['name'] = client_pod2_name
    deployment_name = server_pod_dep_data['metadata']['name']

    computes = system_helper.get_hypervisors(
        operational="enabled", availability="available")

    if len(computes) > 1:
        LOG.fixture_step("Label the nodes and add node selector to the deployment files\
        if not simplex system")
        kube_helper.exec_kube_cmd(sub_cmd="label nodes {}".format(
            computes[0]), args="test=server")
        kube_helper.exec_kube_cmd(sub_cmd="label nodes {}".format(
            computes[1]), args="test=client")
        server_pod_dep_data['spec']['template']['spec']['nodeSelector'] = {
            'test': 'server'}
        client_pod1_data['spec']['nodeSelector'] = {'test': 'server'}
        client_pod2_data['spec']['nodeSelector'] = {'test': 'client'}

    server_pod_path = common.write_yaml_data_to_file(
        server_pod_dep_data, server_dep_file)
    client_pod1_path = common.write_yaml_data_to_file(
        client_pod1_data, "{}.yaml".format(client_pod1_name))
    client_pod2_path = common.write_yaml_data_to_file(
        client_pod2_data, "{}.yaml".format(client_pod2_name))

    LOG.fixture_step(
        "Copy the deployment files from localhost to active controller")
    common.scp_from_localhost_to_active_controller(
        source_path=server_pod_path, dest_path=home_dir)

    common.scp_from_localhost_to_active_controller(
        source_path=client_pod1_path, dest_path=home_dir)

    common.scp_from_localhost_to_active_controller(
        source_path=client_pod2_path, dest_path=home_dir)

    LOG.fixture_step("Deploy server pods {}".format(server_dep_file))
    kube_helper.exec_kube_cmd(sub_cmd="create -f ", args=server_dep_file)
    LOG.fixture_step("Deploy client pod {}.yaml & client pod {}.yaml".format(
        client_pod1_name, client_pod2_name))
    kube_helper.exec_kube_cmd(sub_cmd="create -f ",
                              args="{}.yaml".format(client_pod1_name))

    kube_helper.exec_kube_cmd(sub_cmd="create -f ",
                              args="{}.yaml".format(client_pod2_name))

    LOG.fixture_step("Get the server pods and client pods")
    server_pods = kube_helper.get_pods(labels="server=pod-to-pod")
    client_pods = kube_helper.get_pods(labels="client=pod-to-pod")

    def teardown():
        LOG.fixture_step("Delete the service {}".format(service_name))
        kube_helper.exec_kube_cmd(
            sub_cmd="delete service  ", args=service_name)
        LOG.fixture_step("Delete the deployment {}".format(deployment_name))
        kube_helper.exec_kube_cmd(
            sub_cmd="delete deployment  ", args=deployment_name)
        LOG.fixture_step("Delete the client pods {} & {}".format(
            client_pod1_name, client_pod2_name))
        kube_helper.delete_resources(labels="client=pod-to-pod")
        if len(computes) > 1:
            LOG.fixture_step("Remove the labels on the nodes if not simplex")
            kube_helper.exec_kube_cmd(sub_cmd="label nodes {}".format(
                computes[0]), args="test-")
            kube_helper.exec_kube_cmd(sub_cmd="label nodes {}".format(
                computes[1]), args="test-")

    request.addfinalizer(teardown)
    LOG.fixture_step("Get the server pods and client pods status before test begins")
    kube_helper.wait_for_pods_status(
            pod_names=server_pods+client_pods, namespace="default")
    return get_pod_ips(server_pods), client_pods, deployment_name, service_name


def get_pod_ips(pods):
    """
    Returns the pods ips
    Args:
        pods(list): list of pod names
    Returns: pod ips
    """
    pod_ips = []
    for i in pods:
        pod_ips.append(kube_helper.get_pod_value_jsonpath(
            "pod {}".format(i), "{.status.podIP}"))
    return pod_ips


@mark.platform_sanity
@mark.dc_subcloud
class TestPodtoPod:
    def test_pod_to_pod_connection(self, deploy_test_pods):
        """
        Verify Ping test between pods
        Args:
            deploy_test_pods(fixture): returns server_ips, client_pods, deployment_name, service_name
        Setup:
            - Label the nodes and add node selector to the deployment files
                if not simplex system
            - Copy the deployment files from localhost to active controller
            - Deploy server pod
            - Deploy client pods
        Steps:
            - Ping the server pod ip from the client pod
        Teardown:
            - Delete the service
            - Delete the server pod deployment
            - Delete the client pods
            - Remove the labels on the nodes if not simplex

        """
        server_ips, client_pods, _, _ = deploy_test_pods
        for client_pod in client_pods:
            for ip in server_ips:
                LOG.tc_step("Ping the server pod ip {} from the client pod {}".format(
                    ip, client_pod))
                cmd = "ping -c 3 {} -w 5".format(ip)
                code, _ = kube_helper.exec_cmd_in_container(
                    cmd=cmd, pod=client_pod)
                assert code == 0

    def test_pod_to_service_connection(self, deploy_test_pods):
        """
        Verify client pod to service  multiple endpoints access
        Args:
            deploy_test_pods(fixture): returns server_ips, client_pods, deployment_name, service_name
        Setup:
            - Label the nodes and add node selector to the deployment files
                if not simplex system
            - Copy the deployment files from localhost to active controller
            - Deploy server pod
            - Deploy client pods
        Steps:
            - Curl the server pod ip from the client pod
        Teardown:
            - Delete the service
            - Delete the server pod deployment
            - Delete the client pods
            - Remove the labels on the nodes if not simplex

        """
        server_ips, client_pods, _, _ = deploy_test_pods
        for client_pod in client_pods:
            for ip in server_ips:
                if ProjVar.get_var('IPV6_OAM'):
                    ip = "[{}]".format(ip)
                cmd = "curl -Is {}:8080".format(ip)
                LOG.tc_step("Curl({}) the server pod ip {} from the client pod {}".format(
                    cmd, ip, client_pod))
                code, _ = kube_helper.exec_cmd_in_container(
                    cmd=cmd, pod=client_pod)
                assert code == 0

    def test_host_to_service_connection(self, deploy_test_pods):
        """
        Verify the service connectivity from external network
        Args:
            deploy_test_pods(fixture): returns server_ips, client_pods, deployment_name, service_name
        Setup:
            - Label the nodes and add node selector to the deployment files
                if not simplex system
            - Copy the deployment files from localhost to active controller
            - Deploy server pod
            - Deploy client pods
        Steps:
            - Expose the service with NodePort
            - Check the service access from local host
        Teardown:
            - Delete the service
            - Delete the server pod deployment
            - Delete the client pods
            - Remove the labels on the nodes if not simplex
        """
        _, _, deploy_name, service_name = deploy_test_pods
        LOG.tc_step("Expose the service {} with NodePort".format(service_name))
        kube_helper.expose_the_service(
            deployment_name=deploy_name, type="NodePort", service_name=service_name)
        node_port = kube_helper.get_pod_value_jsonpath(
            "service {}".format(service_name), "{.spec.ports[0].nodePort}")
        for i in system_helper.get_system_iplist():
            url = "http://{}:{}".format(i, node_port)
            LOG.tc_step(
                "Check the service access {} from local host".format(url))
            rest.check_url(url)
