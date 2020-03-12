#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import os
import json

from pytest import fixture
from pytest import mark

from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient

from keywords import container_helper
from keywords import host_helper
from keywords import kube_helper
from keywords import system_helper
from consts.stx import SysType
from consts.auth import HostLinuxUser

from consts.auth import Tenant

STX_MONITOR_TAR = 'stx-monitor.tgz'
STX_MONITOR_APP_NAME = 'stx-monitor'

MONITOR_PORT = 31001

POD_NAME = 0
POD_NODE = 1

MONITORING_HOSTS = ["controller", "compute"]

STX_MONITOR_LABELS = ['elastic-client', 'elastic-controller', 'elastic-data', 'elastic-master']

CONTROLLER_LABELS = STX_MONITOR_LABELS
COMPUTE_LABELS = ['elastic-master']
SUBCLOUD_CONTROLLER_LABELS = ['elastic-controller']

POD_RUNNING_ALL_HOSTS = 'all_hosts'
POD_RUNNING_ONE_INSTANCE = 'one_instance'

POD_READY_STATE_ARGS = '--namespace=monitor --for=condition=Ready pods --timeout=30s --all ' \
                       '--selector=app!=elasticsearch-curator'

MON_METRICBEAT_DS = 'mon-metricbeat-YYYYY'
MON_METRICBEAT_LABEL = 'mon-metricbeat-LABEL'
MON_METRICBEAT_PATIAL_NAME = 'mon-metricbeat-'

# This is a dictionary of labels and their corresponding pods names. Each pod
# can either run on all labeled hosts or on 1 instance on a labeled host.
# Daemon set pods run on all hosts and not correspond on a label.
PODS_LABEL_MATCHING_DICT = {
    # 'daemon_set' is a custom label for automation only
    'daemon_set': {
        'mon-filebeat-': POD_RUNNING_ALL_HOSTS,
        MON_METRICBEAT_DS: POD_RUNNING_ALL_HOSTS
    },
    'elastic-client': {
        'mon-elasticsearch-client-': POD_RUNNING_ALL_HOSTS,
    },
    'elastic-controller': {
        # the curator is a transient pod so we will skip checking for it
        # 'mon-elasticsearch-curator-': POD_RUNNING_ONE_INSTANCE,
        'mon-kibana-': POD_RUNNING_ONE_INSTANCE,
        'mon-kube-state-metrics-': POD_RUNNING_ONE_INSTANCE,
        'mon-logstash-': POD_RUNNING_ALL_HOSTS,
        MON_METRICBEAT_LABEL: POD_RUNNING_ONE_INSTANCE,
        'mon-nginx-ingress-controller-': POD_RUNNING_ALL_HOSTS,
        'mon-nginx-ingress-default-backend-': POD_RUNNING_ONE_INSTANCE
    },
    'elastic-data': {
        'mon-elasticsearch-data-': POD_RUNNING_ALL_HOSTS
    },
    'elastic-master': {
        'mon-elasticsearch-master-': POD_RUNNING_ALL_HOSTS
    }
}

PODS_LABEL_MATCHING_SUBCLOUD_DICT = {
    # 'daemon_set' is a custom label for automation only
    'daemon_set': {
        'mon-filebeat-': POD_RUNNING_ALL_HOSTS,
        MON_METRICBEAT_DS: POD_RUNNING_ALL_HOSTS
    },
    'elastic-controller': {
        # the curator is a transient pod so we will skip checking for it
        # 'mon-elasticsearch-curator-': POD_RUNNING_ONE_INSTANCE,
        'mon-kube-state-metrics-': POD_RUNNING_ONE_INSTANCE,
        'mon-logstash-': POD_RUNNING_ALL_HOSTS,
        MON_METRICBEAT_LABEL: POD_RUNNING_ONE_INSTANCE
    }
}


def stx_monitor_file_exist():
    con_ssh = ControllerClient.get_active_controller()
    home_dir = HostLinuxUser.get_home()
    stx_mon_file = '{}/{}'.format(home_dir, STX_MONITOR_TAR)

    LOG.info("Check if file %s is present" % stx_mon_file)

    return con_ssh.file_exists(stx_mon_file)


@fixture()
def setup_app(request):
    LOG.fixture_step("Setup: Clean up any pre-existing stx-monitor resources")
    cleanup_app()

    def cleanup_after_test():
        LOG.fixture_step("Tear down: clean up any stx-monitor resources")
        cleanup_app()
    request.addfinalizer(cleanup_after_test)


def delete_images_from_host_registries(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    hosts = system_helper.get_hosts(con_ssh=con_ssh, auth_info=auth_info)
    for host in hosts:
        with host_helper.ssh_to_host(hostname=host, con_ssh=con_ssh) as host_ssh:
            LOG.info("Delete {} images for host: {}".format(STX_MONITOR_APP_NAME, host))
            container_helper.remove_docker_images_with_pattern(pattern="elastic", con_ssh=host_ssh,
                                                               timeout=120)


def cleanup_app(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Remove application stx-monitor
    Delete application stx-monitor
    Remove stx-monitor images registries from all hosts
    Remove stx-monitor labels from all hosts
    """

    LOG.info("Remove application {}".format(STX_MONITOR_APP_NAME))
    container_helper.remove_app(app_name=STX_MONITOR_APP_NAME, con_ssh=con_ssh, auth_info=auth_info)

    LOG.info("Delete application {}".format(STX_MONITOR_APP_NAME))
    container_helper.delete_app(app_name=STX_MONITOR_APP_NAME, con_ssh=con_ssh, auth_info=auth_info)

    delete_images_from_host_registries(con_ssh=con_ssh, auth_info=auth_info)

    LOG.info("Delete labels for {}".format(STX_MONITOR_APP_NAME))
    delete_all_monitor_labels(con_ssh=con_ssh, auth_info=auth_info)

    LOG.info("Cleanup completed")


def assign_labels(system_type, con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    The following labels are required on all controllers:
        elastic-controller=enabled
        elastic-master=enabled
        elastic-data=enabled
        elastic-client=enabled

    The following label is required on one compute:
        elastic-master=enabled
    """
    LOG.info("Assign stx-monitor labels to controller-0")
    host_list = system_helper.get_hosts(con_ssh=con_ssh, auth_info=auth_info)
    host_helper.assign_host_labels("controller-0", CONTROLLER_LABELS, lock=False, unlock=False,
                                   con_ssh=con_ssh, auth_info=auth_info)

    if system_type != SysType.AIO_SX and "controller-1" in host_list:
        LOG.info("Assign stx-monitor labels to controller-1")
        host_helper.assign_host_labels("controller-1", CONTROLLER_LABELS, lock=False, unlock=False,
                                       con_ssh=con_ssh, auth_info=auth_info)

    if "compute-0" in host_list:
        LOG.info("Assign stx-monitor labels to compute-0")
        host_helper.assign_host_labels("compute-0", COMPUTE_LABELS, lock=False, unlock=False,
                                       con_ssh=con_ssh, auth_info=auth_info)


def assign_subcloud_labels(system_type, con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    The following label is required on all Subcloud controllers:
        elastic-controller=enabled
    """
    LOG.info("Assign stx-monitor labels to controller-0")
    host_list = system_helper.get_hosts(con_ssh=con_ssh, auth_info=auth_info)
    host_helper.assign_host_labels("controller-0", SUBCLOUD_CONTROLLER_LABELS, lock=False,
                                   unlock=False, con_ssh=con_ssh, auth_info=auth_info)

    if system_type != SysType.AIO_SX and "controller-1" in host_list:
        LOG.info("Assign stx-monitor labels to controller-1")
        host_helper.assign_host_labels("controller-1", SUBCLOUD_CONTROLLER_LABELS, lock=False,
                                       unlock=False, con_ssh=con_ssh, auth_info=auth_info)


def delete_all_monitor_labels(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    LOG.info("Delete monitor labels from hosts")

    host_list = system_helper.get_hosts(con_ssh=con_ssh, auth_info=auth_info)
    for host in host_list:
        # Remove all monitor labels from all hosts on the system
        host_helper.remove_host_labels(host, STX_MONITOR_LABELS, lock=False, unlock=False,
                                       con_ssh=con_ssh, auth_info=auth_info)


def app_upload_apply(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Upload stx-monitor
    Apply stx-monitor
    """

    # Do application upload stx-monitor.
    app_dir = HostLinuxUser.get_home()
    tar_file = os.path.join(app_dir, STX_MONITOR_TAR)
    LOG.info("Upload %s" % tar_file)
    container_helper.upload_app(tar_file=tar_file, app_name=STX_MONITOR_APP_NAME, con_ssh=con_ssh,
                                auth_info=auth_info, uploaded_timeout=3600,)

    # Do application apply stx-monitor.
    LOG.info("Apply %s" % STX_MONITOR_APP_NAME)
    container_helper.apply_app(app_name=STX_MONITOR_APP_NAME, applied_timeout=3600,
                               check_interval=60, con_ssh=con_ssh, auth_info=auth_info)


def get_oam_floating_ip():
    """
    Get oam floating ip address
    """
    if system_helper.is_aio_simplex():
        fields = 'oam_ip'
    else:
        fields = ('oam_c0_ip', 'oam_c1_ip', 'oam_floating_ip')
    oam_info = system_helper.get_oam_values(fields=fields)

    for key, value in oam_info.items():
        if value is not None:
            oam_floating_ip = value

    return oam_floating_ip


def check_cluster_health(system_type):
    # Check the cluster health (cluster health status will be yellow for
    # AIO-SX as there will be no replicated shards)
    LOG.info("Check the cluster health")
    hosts = system_helper.get_hosts()
    LOG.info("System has hosts: ".format(hosts))
    prefix = 'http'
    oam_ip = get_oam_floating_ip()

    for host in hosts:
        with host_helper.ssh_to_host(hostname=host) as host_ssh:
            code, output = host_ssh.exec_cmd(
                'curl {}://{}:31001/mon-elasticsearch-client/_cluster/health?pretty'.format(
                    prefix, oam_ip), fail_ok=False)

        if output:
            data_dict = json.loads(output)

            # check that 'status' is green
            if not (data_dict['status'] == 'green' or
                    (system_type == SysType.AIO_SX and data_dict['status'] == 'yellow')):
                raise AssertionError("status not green or in case of AIO-SX yellow")

            # check that 'unassigned shards' is 0
            if system_type != SysType.AIO_SX and data_dict['unassigned_shards'] != 0:
                raise AssertionError("unassigned_shards not 0")

            # check that 'active_shards' is 0
            if data_dict['active_shards'] == 0:
                raise AssertionError("active_shards not 0")
        else:
            raise AssertionError("curl command failed")


def is_pod_running_on_host(pods, host, partial_pod_name):

    for pod in (_pod for _pod in pods if host == _pod[POD_NODE]):

        # Special case for 'mon-metricbeat-'. There are two running processes with that partial
        # name;
        #   - The daemon set pod 'mon-metricbeat-YYYYY'
        #   - The label 'mon-metricbeat-YYYYYYYYYY-YYYYY'. Note that the middle Y are variable
        #   lengths. e.g. mon-metricbeat-557fb9cb7-pbbzs vs mon-kube-state-metrics-77db855d59-5s566
        #   was seen in different labs.
        if partial_pod_name == MON_METRICBEAT_DS:
            if MON_METRICBEAT_PATIAL_NAME in pod[POD_NAME] and \
                            len(pod[POD_NAME]) == len(MON_METRICBEAT_DS):
                LOG.info('Found pod matching name {} for host {}. POD: {}'.format(
                    partial_pod_name, host, pod[POD_NAME]))
                return True

        elif partial_pod_name == MON_METRICBEAT_LABEL:
            if MON_METRICBEAT_PATIAL_NAME in pod[POD_NAME] and \
                            len(pod[POD_NAME]) >= len(MON_METRICBEAT_DS)+2:
                LOG.info('Found pod matching name {} for host {}. POD: {}'.format(
                    partial_pod_name, host, pod[POD_NAME]))
                return True

        elif partial_pod_name in pod[POD_NAME]:
            LOG.info('Found pod matching name {} for host {}. POD: {}'.format(
                partial_pod_name, host, pod[POD_NAME]))

            return True

    LOG.info('Missing pod matching name {} for host {}'.format(partial_pod_name, host))
    return False


def are_monitor_pods_running(system_type, con_ssh=None, auth_info=Tenant.get('admin_platform'),
                             matching_dict=PODS_LABEL_MATCHING_DICT):
    # Get all the pods for stx-monitor
    monitor_pods = kube_helper.get_pods(field=('NAME', 'NODE'), namespace="monitor", strict=False,
                                        con_ssh=con_ssh)

    LOG.info("Running pods for stx-monitor: %s" % monitor_pods)

    # Make a dictionary of which hosts are assigned to which stx-monitor
    # labels. e.g.
    #
    # {
    #   'daemon_set': ['controller-0', 'controller-1'],
    #   'elastic-client': ['controller-0', 'controller-1'],
    #   'elastic-controller': ['controller-0', 'controller-1'],
    #   ...
    # }
    #
    host_list = system_helper.get_host_list_data(columns=["hostname", "personality"],
                                                 con_ssh=con_ssh, auth_info=auth_info)
    labels_to_host_dict = {}
    for host in (_host for _host in host_list if _host.get('hostname')):
        hostname = host.get('hostname')
        personality = host.get('personality')
        if personality and personality in str(MONITORING_HOSTS):

            # Add the daemon set custom label, this is a special label only
            # for this labels_to_host_dict
            hosts_for_label = labels_to_host_dict.get('daemon_set', [])
            hosts_for_label.append(hostname)
            labels_to_host_dict.update({'daemon_set': hosts_for_label})

            # Add the host's assigned labels
            labels = host_helper.get_host_labels_info(hostname, con_ssh=con_ssh,
                                                      auth_info=auth_info)
            for label_name, label_status in labels.items():
                if label_status == 'enabled':
                    hosts_for_label = labels_to_host_dict.get(label_name, [])
                    hosts_for_label.append(hostname)
                    labels_to_host_dict.update({label_name: hosts_for_label})

    LOG.info('labels_running_hosts:{}'.format(labels_to_host_dict))

    # For each labels currently assigned on the system, get the matching
    # POD names from matching_dict
    for label, hosts_for_label in labels_to_host_dict.items():
        LOG.debug('----------')
        LOG.debug('label:{} hosts:{}'.format(label, hosts_for_label))

        pod_details = None
        for k, v in matching_dict.items():
            if k == label:
                pod_details = v
                break

        if pod_details is None:
            # Label not found in dict just return True
            return True

        # Get the list of pod names we need to search for, a label can have
        # more than one pods.
        for partial_pod_name, running_type in pod_details.items():
            LOG.info('-----')
            LOG.info('partial_pod_name:{} running_type:{}'.format(partial_pod_name, running_type))

            inst_found_count = 0
            for host in hosts_for_label:
                if is_pod_running_on_host(monitor_pods, host, partial_pod_name):
                    # The pod was found, increment the no of instances running on all hosts for this
                    # pod
                    inst_found_count += 1

            # Special case for AIO-DX and mon-elasticsearch-master-x
            if partial_pod_name == 'mon-elasticsearch-master-' and system_type == SysType.AIO_DX \
                    and inst_found_count == 1:
                LOG.info('Pod {} only needs to run one instances for AIO-DX'.format(
                    partial_pod_name))
                pass
            # Some pods only run one instances even if the label is on multiple hosts
            elif inst_found_count == 1 and running_type == POD_RUNNING_ONE_INSTANCE:
                LOG.info('Pod {} only needs to run one instances'.format(partial_pod_name))
                pass
            # Pod did not match the number of hosts its supposed to run on
            elif inst_found_count != len(hosts_for_label):
                LOG.error('Pod check for {} failed, missing instances'.format(partial_pod_name))
                return False

            LOG.info('Check for pod {} SUCCESS'.format(partial_pod_name))

    return True


@mark.skipif(not stx_monitor_file_exist(), reason="Missing stx-monitor tar file from system")
@mark.platform_sanity
def test_stx_monitor(setup_app):
    """
    Test stx-monitor application

    Assumptions: /home/sysadmin/stx-monitor.tgz is present on controller-0

    Args:
        setup_app: fixture

    Setups:
        - application remove and delete stx-monitor,
            application-remove stx-monitor
            application-delete stx-monitor
        - delete images from all registries on all hosts.
             docker images  | grep elastic | awk '{print $3}'
             docker image rm --force <image>
        - remove all stx-monitor labels from all hosts
            e.g. host-label-remove <hostname> <stx-monitor labels>

    Test Steps:
        - Assign labels (varies depending on type of system and hosts).
            e.g. host-label-assign <hostname> <label name>=enabled
            The following labels are required on all controllers:
                elastic-controller=enabled
                elastic-master=enabled
                elastic-data=enabled
                elastic-client=enabled
            The following label is required on one compute:
                elastic-master=enabled

        - Application upload.
            application-upload -n stx-monitor /home/sysadmin/stx-monitor.tgz

        - Application apply.
            application-apply stx-monitor

        - Check for pods Ready state.
            kubectl wait --namespace=monitor --for=condition=Ready pods --timeout=30s --all
                --selector=app!=elasticsearch-curator

        - Verify all Pods are assigned according to the specified labels and DaemonSets.

        - Check the cluster health (cluster health status will be yellow for AIO-SX as there will be
        no replicated shards). Validate 'status', 'active_shards' and 'unassigned_shards' values.
            curl <oam ip>:31001/mon-elasticsearch-client/_cluster/health?pretty

    Teardown:
        Same as Setups above

    """

    system_helper.get_system_values()
    system_type = system_helper.get_sys_type()

    # Assign the stx-monitor labels.
    LOG.tc_step("Assign labels")
    assign_labels(system_type)

    # Upload and apply stx-monitor.
    LOG.tc_step("Upload and Apply %s" % STX_MONITOR_APP_NAME)
    app_upload_apply()

    # Check for pods Ready state.
    LOG.tc_step("Check Pod Ready state")
    kube_helper.exec_kube_cmd(sub_cmd="wait", args=POD_READY_STATE_ARGS, fail_ok=False)

    # Verify all Pods are assigned according to the specified labels and DaemonSets
    LOG.tc_step("Verify all Pods are assigned properly")
    assert are_monitor_pods_running(system_type), "Error: Some monitor pods are not running"

    # Check the cluster health
    LOG.tc_step("Check the cluster health")
    check_cluster_health(system_type)
