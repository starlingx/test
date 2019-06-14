#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import re

from pytest import mark, skip

from keywords import kube_helper, system_helper, host_helper
from consts.stx import PodStatus, HostAvailState
from utils.tis_log import LOG


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


@mark.platform_sanity
@mark.parametrize('controller', [
    'active',
    'standby'
])
def test_kube_system_services(controller):
    """
    Test kube-system pods are deployed and running

    Test Steps:
        - ssh to given controller
        - Check all kube-system pods are running
        - Check kube-system services displayed: 'calico-typha',
            'kube-dns', 'tiller-deploy'
        - Check kube-system deployments displayed: 'calico-typha',
            'coredns', 'tiller-deploy'

    """
    host = check_host(controller=controller)

    with host_helper.ssh_to_host(hostname=host) as con_ssh:

        kube_sys_pods_values = kube_helper.get_resources(
            field=('NAME', 'STATUS'), resource_type='pod',
            namespace='kube-system', con_ssh=con_ssh)
        kube_sys_services = kube_helper.get_resources(
            resource_type='service', namespace='kube-system', con_ssh=con_ssh)
        kube_sys_deployments = kube_helper.get_resources(
            resource_type='deployment.apps', namespace='kube-system',
            con_ssh=con_ssh)

        LOG.tc_step("Check kube-system pods status on {}".format(controller))
        # allow max 1 coredns pending on aio-sx
        coredns_pending = False if system_helper.is_aio_simplex() else True
        for pod_info in kube_sys_pods_values:
            pod_name, pod_status = pod_info
            if not coredns_pending and 'coredns-' in pod_name and \
                    pod_status == PodStatus.PENDING:
                coredns_pending = True
                continue

            valid_status = PodStatus.RUNNING
            if re.search('audit-|init-', pod_name):
                valid_status = PodStatus.COMPLETED

            if pod_status not in valid_status:
                kube_helper.wait_for_pods_status(pod_names=pod_name,
                                                 status=valid_status,
                                                 namespace='kube-system',
                                                 con_ssh=con_ssh, timeout=300)

        services = ('kube-dns', 'tiller-deploy')
        LOG.tc_step("Check kube-system services on {}: {}".format(controller,
                                                                  services))
        for service in services:
            assert service in kube_sys_services, \
                "{} not in kube-system service table".format(service)

        deployments = ('calico-kube-controllers', 'coredns', 'tiller-deploy')
        LOG.tc_step("Check kube-system deployments on {}: "
                    "{}".format(controller, deployments))
        for deployment in deployments:
            assert deployment in kube_sys_deployments, \
                "{} not in kube-system deployment.apps table".format(deployment)
