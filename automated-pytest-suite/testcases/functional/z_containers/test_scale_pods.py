"""
Xstudio testcase reference http://162.248.221.232:8080/nice/xstudio/xstudio.jsp?id=T_18189
"""
from pytest import fixture
from pytest import skip

from utils.tis_log import LOG
from keywords import common
from keywords import kube_helper
from keywords import system_helper

from consts.auth import HostLinuxUser
from consts.stx import PodStatus


@fixture(scope='module')
def get_yaml():
    filename = "rc_deployment.yaml"
    ns = "rc"
    number_nodes = 98
    relicas = number_nodes*len(system_helper.get_hypervisors())
    source_path = "utils/test_files/{}".format(filename)
    home_dir = HostLinuxUser.get_home()
    common.scp_from_localhost_to_active_controller(
        source_path, dest_path=home_dir)
    yield ns, relicas, filename
    LOG.fixture_step("Delete the deployment")
    kube_helper.exec_kube_cmd(
        "delete deployment --namespace={} resource-consumer".format(ns))
    LOG.fixture_step("Check pods are terminating")
    kube_helper.wait_for_pods_status(
        namespace=ns, status=PodStatus.TERMINATING)
    LOG.fixture_step("Wait for all pods are deleted")
    kube_helper.wait_for_resources_gone(namespace=ns)
    LOG.fixture_step("Delete the service and namespace")
    kube_helper.exec_kube_cmd(
        "delete service rc-service --namespace={}".format(ns))
    kube_helper.exec_kube_cmd("delete namespace {}".format(ns))


def test_scale_pods(get_yaml):
    """
    Testing the deployment of high number of pods
    Args:
        get_yaml : module fixture
    Setup:
        - Scp deployment file
    Steps:
        - Check the deployment of resource-consumer
        - Check the pods up
        - Scale to 99* number of worker nodes
        - Check all the pods are running
    Teardown:
        - Delete the deployment and service
    """
    ns, replicas, filename = get_yaml
    LOG.tc_step("Create the deployment")
    kube_helper.exec_kube_cmd(
        sub_cmd="create -f {}".format(filename))
    LOG.tc_step("Check resource consumer pods are running")
    state, _ = kube_helper.wait_for_pods_status(namespace=ns, timeout=180)
    if state:
        LOG.tc_step(
            "Scale the resource consumer app to {}* no of worker nodes".format(replicas))
        kube_helper.exec_kube_cmd(
            "scale deployment --namespace={} resource-consumer --replicas={}".format(ns, replicas))
        kube_helper.wait_for_pods_status(namespace=ns, timeout=180)
    else:
        skip("resource consumer deployment failed")
