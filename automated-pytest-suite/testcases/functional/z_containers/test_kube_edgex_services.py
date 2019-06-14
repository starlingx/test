#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from pytest import fixture, mark, skip

from keywords import kube_helper, system_helper, host_helper
from consts.stx import PodStatus, HostAvailState
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient

EDGEX_URL = \
    'https://github.com/rohitsardesai83/edgex-on-kubernetes/archive/master.zip'
EDGEX_ARCHIVE = '~/master.zip'
EDGEX_DIR = '~/edgex-on-kubernetes-master'
EDGEX_START = '{}/hack/edgex-up.sh'.format(EDGEX_DIR)
EDGEX_STOP = '{}/hack/edgex-down.sh'.format(EDGEX_DIR)


@fixture(scope='module')
def deploy_edgex(request):
    con_ssh = ControllerClient.get_active_controller()

    LOG.fixture_step("Downloading EdgeX-on-Kubernetes")
    con_ssh.exec_cmd('wget {}'.format(EDGEX_URL), fail_ok=False)
    charts_exist = con_ssh.file_exists(EDGEX_ARCHIVE)
    assert charts_exist, '{} does not exist'.format(EDGEX_ARCHIVE)

    LOG.fixture_step("Extracting EdgeX-on-Kubernetes")
    con_ssh.exec_cmd('unzip {}'.format(EDGEX_ARCHIVE), fail_ok=False)

    LOG.fixture_step("Deploying EdgeX-on-Kubernetes")
    con_ssh.exec_cmd(EDGEX_START, 300, fail_ok=False)

    def delete_edgex():
        LOG.fixture_step("Destroying EdgeX-on-Kubernetes")
        con_ssh.exec_cmd(EDGEX_STOP, 300, fail_ok=False)

        LOG.fixture_step("Removing EdgeX-on-Kubernetes")
        con_ssh.exec_cmd('rm -rf {} {}'.format(EDGEX_ARCHIVE, EDGEX_DIR))
    request.addfinalizer(delete_edgex)

    return


def check_host(controller):
    host = system_helper.get_active_controller_name()
    if controller == 'standby':
        controllers = system_helper.get_controllers(
            availability=(HostAvailState.AVAILABLE, HostAvailState.DEGRADED,
                          HostAvailState.ONLINE))
        controllers.remove(host)
        if not controllers:
            skip('Standby controller does not exist or not in good state')
        host = controllers[0]
    return host


@mark.platform
@mark.parametrize('controller', [
    'active',
    'standby'
])
def test_kube_edgex_services(deploy_edgex, controller):
    """
    Test edgex pods are deployed and running
    Args:
        deploy_edgex (str): module fixture
        controller: test param
    Test Steps:
        - ssh to given controller
        - Wait for EdgeX pods deployment
        - Check all EdgeX pods are running
        - Check EdgeX services displayed:
            'edgex-core-command', 'edgex-core-consul',
            'edgex-core-data', 'edgex-core-metadata'
        - Check EdgeX deployments displayed:
            'edgex-core-command', 'edgex-core-consul',
            'edgex-core-data', 'edgex-core-metadata'

    """
    pods = ('edgex-core-command', 'edgex-core-consul',
            'edgex-core-data', 'edgex-core-metadata')
    services = ('edgex-core-command', 'edgex-core-consul',
                'edgex-core-data', 'edgex-core-metadata')
    deployments = ('edgex-core-command', 'edgex-core-consul',
                   'edgex-core-data', 'edgex-core-metadata')

    host = check_host(controller=controller)
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Check EdgeX pods on {}: {}".format(controller, pods))
        edgex_services = kube_helper.get_resources(resource_type='service',
                                                   namespace='default',
                                                   con_ssh=con_ssh)
        edgex_deployments = kube_helper.get_resources(
            resource_type='deployment.apps', namespace='default',
            con_ssh=con_ssh)

        LOG.tc_step("Wait for EdgeX pods Running")
        kube_helper.wait_for_pods_status(partial_names=pods,
                                         namespace='default',
                                         status=PodStatus.RUNNING,
                                         con_ssh=con_ssh, fail_ok=False)

        LOG.tc_step("Check EdgeX services on {}: {}".format(controller,
                                                            services))
        for service in services:
            assert service in edgex_services, "{} not in kube-system " \
                                              "service table".format(service)

        LOG.tc_step("Check EdgeX deployments on {}: {}".format(controller,
                                                               deployments))
        for deployment in deployments:
            assert deployment in edgex_deployments, \
                "{} not in kube-system deployment.apps table".format(deployment)
