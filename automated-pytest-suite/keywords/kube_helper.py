#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import re
import configparser
import time

import yaml

from utils import table_parser, exceptions
from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient
from keywords import common, system_helper
from consts.stx import PodStatus


def exec_kube_cmd(sub_cmd, args=None, con_ssh=None, fail_ok=False, grep=None):
    """
    Execute an kubectl cmd on given ssh client. i.e., 'kubectl <sub_cmd> <args>'
    Args:
        sub_cmd (str):
        args (None|str):
        con_ssh:
        fail_ok:
        grep (None|str|tuple|list)

    Returns (tuple):
        (0, <std_out>)
        (1, <std_err>)

    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    cmd = 'kubectl {} {}'.format(sub_cmd.strip(),
                                 args.strip() if args else '').strip()

    get_exit_code = True
    if cmd.endswith(';echo'):
        get_exit_code = False
    if grep:
        if isinstance(grep, str):
            grep = (grep,)
        for grep_str in grep:
            if '-v ' not in grep_str and '-e ' in grep_str and 'NAME' not in \
                    grep_str:
                grep_str += ' -e NAME'
            cmd += ' | grep --color=never {}'.format(grep_str)

    code, out = con_ssh.exec_cmd(cmd, fail_ok=True, get_exit_code=get_exit_code)
    if code <= 0:
        return 0, out

    if fail_ok:
        return 1, out
    else:
        raise exceptions.KubeCmdError('CMD: {} Output: {}'.format(cmd, out))


def __get_resource_tables(namespace=None, all_namespaces=None,
                          resource_types=None, resource_names=None,
                          labels=None, field_selectors=None, wide=True,
                          con_ssh=None, fail_ok=False, grep=None):
    if not resource_types:
        resource_types = ''
    elif isinstance(resource_types, (list, tuple)):
        resource_types = ','.join(resource_types)
    resources = resource_types

    if resource_names:
        if ',' in resource_types:
            raise ValueError(
                "At most 1 resource_types can be specified if resource_names "
                "are provided.")
        if all_namespaces and not namespace:
            raise ValueError(
                "all_namespaces is disallowed when resource_names are provided")
        if isinstance(resource_names, (list, tuple)):
            resource_names = ' '.join(resource_names)
        resources = '{} {}'.format(resources, resource_names)

    args_dict = {
        '-n': namespace,
        '--all-namespaces': True if all_namespaces and not namespace else None,
        '-l': labels,
        '--field-selector': field_selectors,
        '-o': 'wide' if wide else None
    }
    args = '{} {}'.format(resources,
                          common.parse_args(args_dict, repeat_arg=False,
                                            vals_sep=','))
    code, out = exec_kube_cmd(sub_cmd='get', args=args, con_ssh=con_ssh,
                              fail_ok=fail_ok, grep=grep)
    if code > 0:
        return code, out

    tables = table_parser.tables_kube(out)
    return code, tables


def get_unhealthy_pods(field='NAME', namespace=None, all_namespaces=True,
                       pod_names=None,
                       labels=None, exclude=False, strict=True, con_ssh=None,
                       **kwargs):
    """
    Get pods that are not Completed and not Running
    Args:
        namespace (str|None):
        all_namespaces: (bool|None)
        pod_names (str|list|tuple|None): full names of pods to check
        labels (str|dict|None):
        field (str|tuple|list):
        exclude:
        strict:
        con_ssh:

    Returns (list):

    """
    field_selector = 'status.phase!=Running,status.phase!=Succeeded'
    return get_pods(field=field, namespace=namespace,
                    all_namespaces=all_namespaces, pod_names=pod_names,
                    labels=labels, field_selectors=field_selector,
                    exclude=exclude, strict=strict,
                    con_ssh=con_ssh, **kwargs)


def get_pods(field='NAME', namespace=None, all_namespaces=False, pod_names=None,
             labels=None, field_selectors=None,
             fail_ok=False, con_ssh=None, exclude=False, strict=True, **kwargs):
    """
    Get pods values for specified field(s)
    Args:
        field (str|tuple|list): return values for given header(s)
        namespace (str|None): when None, --all-namespaces will be used.
        all_namespaces (bool|none):
        pod_names (str|list|tuple): Full pod name(s). When specified, labels
        and field_selectors will be ignored.
        labels (str|dict|None|list|tuple): label selectors. Used only if
        full_names are unspecified.
            e.g., application=nova,component=compute
        field_selectors (str): Used only if full_names are unspecified.
            e.g., , 'spec.nodeName=controller-0,status.phase!=Running,
            status.phase!=Succeeded'
        exclude (bool):
        strict (bool):
        con_ssh:
        fail_ok (bool)
        **kwargs: table filters for post processing output to return filtered
            values

    Returns (list): examples:
        Input:
            field=('NAME', 'STATUS') OR 'Name'
            labels='application=nova,component=compute',
            field_selector='spec.nodeName=compute-0'
        Output:
            [('nova-compute-compute-0-xdjkds', 'Running')] OR [
            'nova-compute-compute-0-xdjkds']

    """
    return get_resources(field=field, namespace=namespace,
                         all_namespaces=all_namespaces, resource_type='pod',
                         resource_names=pod_names, labels=labels,
                         field_selectors=field_selectors,
                         con_ssh=con_ssh, fail_ok=fail_ok, exclude=exclude,
                         strict=strict, **kwargs)


def get_resources(field='NAME', namespace=None, all_namespaces=None,
                  resource_names=None, resource_type='pod',
                  labels=None, field_selectors=None, con_ssh=None,
                  fail_ok=False, grep=None,
                  exclude=False, strict=True, **kwargs):
    """
    Get resources values for single resource type via kubectl get
    Args:
        field (str|tuple|list)
        namespace (None|str): e.g., kube-system, openstack, default.
        all_namespaces (bool|None): used only when namespace is unspecified
        resource_names (str|None|list|tuple): e.g., calico-typha
        resource_type (str): e.g., "deployments.apps", "pod", "service"
        labels (dict|str|list|tuple): Used only when resource_names are
            unspecified
        field_selectors (dict|str|list|tuple): Used only when resource_names
        are unspecified
        con_ssh:
        fail_ok:
        grep (str|None): grep on cmd output
        exclude
        strict
        **kwargs: table filters for post processing return values

    Returns (list):
        key is the name prefix, e.g., service, default, deployment.apps,
        replicaset.apps
        value is a list. Each item is a dict rep for a row with lowercase keys.
            e.g., [{'name': 'cinder-api', 'age': '4d19h', ... },  ...]

    """
    name_filter = None
    if resource_names and (
            (all_namespaces and not namespace) or field_selectors or labels):
        name_filter = {'name': resource_names}
        resource_names = None

    code, tables = __get_resource_tables(namespace=namespace,
                                         all_namespaces=all_namespaces,
                                         resource_types=resource_type,
                                         resource_names=resource_names,
                                         labels=labels,
                                         field_selectors=field_selectors,
                                         con_ssh=con_ssh, fail_ok=fail_ok,
                                         grep=grep)
    if code > 0:
        output = tables
        if 'NAME ' not in output:  # no resource returned
            return []

        output = output.split('\nError from server')[0]
        tables = table_parser.tables_kube(output)

    final_table = tables[0]
    if len(tables) > 1:
        combined_values = final_table['values']
        column_count = len(combined_values)
        for table_ in tables[1:]:
            table_values = table_['values']
            combined_values = [combined_values[i] + table_values[i] for i in
                               range(column_count)]
        final_table['values'] = combined_values

    if name_filter:
        final_table = table_parser.filter_table(final_table, **name_filter)

    return table_parser.get_multi_values(final_table, fields=field,
                                         zip_values=True, strict=strict,
                                         exclude=exclude, **kwargs)


def apply_pod(file_path, pod_name, namespace=None, recursive=None,
              select_all=None,
              labels=None, con_ssh=None, fail_ok=False,
              check_both_controllers=True):
    """
    Apply a pod from given file via kubectl apply
    Args:
        file_path (str):
        pod_name (str):
        namespace (None|str):
        recursive (None|bool):
        select_all (None|bool):
        labels (dict|str|list|tuple|None): key value pairs
        con_ssh:
        fail_ok:
        check_both_controllers (bool):

    Returns (tuple):
        (0, <pod_info>(dict))
        (1, <std_err>)
        (2, <pod_info>)    # pod is not running after apply
        (3, <pod_info>)    # pod if not running on the other controller after
        apply

    """
    arg_dict = {
        '--all': select_all,
        '-l': labels,
        '--recursive': recursive,
    }

    arg_str = common.parse_args(args_dict=arg_dict, vals_sep=',')
    arg_str += ' -f {}'.format(file_path)

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    code, output = exec_kube_cmd(sub_cmd='apply', args=arg_str, con_ssh=con_ssh,
                                 fail_ok=fail_ok)
    if code > 0:
        return 1, output

    LOG.info("Check pod is running on current host")
    res = wait_for_pods_status(pod_names=pod_name, namespace=namespace,
                               status=PodStatus.RUNNING,
                               con_ssh=con_ssh, fail_ok=fail_ok)
    if not res:
        return 2, "Pod {} is not running after apply on active " \
                  "controller".format(pod_name)

    if check_both_controllers and not system_helper.is_aio_simplex(
            con_ssh=con_ssh):
        LOG.info("Check pod is running on the other controller as well")
        con_name = 'controller-1' if con_ssh.get_hostname() == 'controller-0' \
            else 'controller-0'
        from keywords import host_helper
        with host_helper.ssh_to_host(hostname=con_name,
                                     con_ssh=con_ssh) as other_con:
            res, pods_info = wait_for_pods_status(pod_names=pod_name,
                                                  namespace=namespace,
                                                  con_ssh=other_con,
                                                  fail_ok=fail_ok)
            if not res:
                return 3, "Pod {} is not running after apply on standby " \
                          "controller".format(pod_name)

    LOG.info("{} pod is successfully applied and running".format(pod_name))
    return 0, pod_name


def wait_for_pods_status(pod_names=None, partial_names=None, labels=None,
                         namespace=None, status=PodStatus.RUNNING,
                         timeout=120, check_interval=3, con_ssh=None,
                         fail_ok=False, strict=False, **kwargs):
    """
    Wait for pod(s) to reach given status via kubectl get pod
    Args:
        pod_names (str|list|tuple): full name of the pods
        partial_names (str|list|tuple): Used only if pod_names are not provided
        labels (str|list|tuple|dict|None): Used only if pod_names are not
            provided
        namespace (None|str):
        status (str|None|list): None means any state as long as pod exists.
        timeout:
        check_interval:
        con_ssh:
        fail_ok:
        strict (bool):

    Returns (tuple):
        (True, <actual_pods_info>)  # actual_pods_info is a dict with
        pod_name as key, and pod_info(dict) as value
        (False, <actual_pods_info>)

    """

    pods_to_check = []
    if pod_names:
        if isinstance(pod_names, str):
            pod_names = [pod_names]
        else:
            pod_names = list(pod_names)
        labels = partial_names = None
        pods_to_check = list(pod_names)
    elif partial_names:
        if isinstance(partial_names, str):
            partial_names = [partial_names]
        else:
            partial_names = list(partial_names)
        kwargs['NAME'] = partial_names
        pods_to_check = list(partial_names)

    actual_status = {}
    end_time = time.time() + timeout

    while time.time() < end_time:
        pod_full_names = pods_to_check if pod_names else None
        pods_values = get_pods(pod_names=pod_full_names,
                               field=('NAME', 'status'), namespace=namespace,
                               labels=labels,
                               strict=strict, fail_ok=True, con_ssh=con_ssh,
                               **kwargs)
        if not pods_values:
            # No pods returned, continue to check.
            time.sleep(check_interval)
            continue

        continue_check = False  # This is used when only labels are provided
        for pod_info in pods_values:
            pod_name, pod_status = pod_info
            actual_status[pod_name] = pod_status
            if status and pod_status not in status:
                # Status not as expected, continue to wait
                continue_check = True
                if partial_names:
                    # In this case, there might be multiple pods that matches
                    # 1 partial name, so the partial name that
                    # matches current pod could have been removed if there
                    # was one other pod that also matched the name
                    # had reached the desired state. In this case, we will
                    # add the partial name back to check list
                    for partial_name in partial_names:
                        if partial_name in pod_name and partial_name not in \
                                pods_to_check:
                            pods_to_check.append(partial_name)
                            break
            else:
                # Criteria met for current pod, remove it from check_list
                if pod_names:
                    pods_to_check.remove(pod_name)
                elif partial_names:
                    for partial_name in partial_names:
                        if partial_name in pod_name and partial_name in \
                                pods_to_check:
                            pods_to_check.remove(partial_name)
                            break

        if not pods_to_check and not continue_check:
            return True, actual_status

        time.sleep(check_interval)

    name_str = 'Names: {}'.format(pods_to_check) if pods_to_check else ''
    label_str = 'Labels: {}'.format(labels) if labels else ''
    criteria = '{} {}'.format(name_str, label_str).strip()
    msg = "Pods did not reach expected status within {}s. Criteria not met: " \
          "{}. Actual info: {}".format(timeout, criteria, actual_status)
    if fail_ok:
        LOG.info(msg)
        return False, actual_status

    raise exceptions.KubeError(msg)


def wait_for_resources_gone(resource_names=None, resource_type='pod',
                            namespace=None, timeout=120,
                            check_interval=3, con_ssh=None, fail_ok=False,
                            strict=True, exclude=False, **kwargs):
    """
        Wait for pod(s) to be gone from kubectl get
        Args:
            resource_names (str|list|tuple): full name of a pod
            resource_type (str):
            namespace (None|str):
            timeout:
            check_interval:
            con_ssh:
            fail_ok:
            strict (bool):
            exclude
            **kwargs

        Returns (tuple):
            (True, None)
            (False, <actual_pods_info>)   # actual_pods_info is a dict with
            pod_name as key, and pod_info(dict) as value

        """

    end_time = time.time() + timeout
    resources_to_check = resource_names

    while time.time() < end_time:

        resources_to_check = get_resources(resource_names=resources_to_check,
                                           namespace=namespace,
                                           resource_type=resource_type,
                                           con_ssh=con_ssh,
                                           fail_ok=True, strict=strict,
                                           exclude=exclude, **kwargs)

        if not resources_to_check:
            return True, resources_to_check

        time.sleep(check_interval)

    msg = 'Resources did not disappear in {} seconds. Remaining resources: ' \
          '{}, namespace: {}'.format(timeout, resources_to_check, namespace)

    if fail_ok:
        LOG.info(msg)
        return False, resources_to_check

    raise exceptions.KubeError(msg)


def delete_resources(resource_names=None, select_all=None, resource_types='pod',
                     namespace=None,
                     recursive=None, labels=None, con_ssh=None, fail_ok=False,
                     post_check=True,
                     check_both_controllers=True):
    """
    Delete pods via kubectl delete
    Args:
        resource_names (None|str|list|tuple):
        select_all (None|bool):
        resource_types (str|list|tuple):
        namespace (None|str):
        recursive (bool):
        labels (None|dict):
        con_ssh:
        fail_ok:
        post_check (bool): Whether to check if resources are gone after deletion
        check_both_controllers (bool):

    Returns (tuple):
        (0, None)   # pods successfully deleted
        (1, <std_err>)
        (2, <undeleted_resources>(list of dict))    # pod(s) still exist in
        kubectl after deletion
        (3, <undeleted_resources_on_other_controller>(list of dict))    #
        pod(s) still exist on the other controller

    """
    arg_dict = {
        '--all': select_all,
        '-l': labels,
        '--recursive': recursive,
    }

    arg_str = common.parse_args(args_dict=arg_dict, vals_sep=',')
    if resource_types:
        if isinstance(resource_types, str):
            resource_types = [resource_types]
        arg_str = '{} {}'.format(','.join(resource_types), arg_str).strip()

    if resource_names:
        if isinstance(resource_names, str):
            resource_names = [resource_names]
        arg_str = '{} {}'.format(arg_str, ' '.join(resource_names))

    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()
    code, output = exec_kube_cmd(sub_cmd='delete', args=arg_str,
                                 con_ssh=con_ssh, fail_ok=fail_ok)
    if code > 0:
        return 1, output

    if post_check:
        def __wait_for_resources_gone(ssh_client):
            final_remaining = []
            if resource_types:
                for resource_type in resource_types:
                    res, remaining_res = wait_for_resources_gone(
                        resource_names=resource_names,
                        resource_type=resource_type,
                        namespace=namespace,
                        con_ssh=ssh_client, fail_ok=fail_ok)
                    if not res:
                        final_remaining += remaining_res
            else:
                res, final_remaining = wait_for_resources_gone(
                    resource_names=resource_names,
                    namespace=namespace,
                    con_ssh=ssh_client, fail_ok=fail_ok)
            return final_remaining

        LOG.info("Check pod is not running on current host")

        remaining = __wait_for_resources_gone(con_ssh)
        if remaining:
            return 2, remaining

        if check_both_controllers and not system_helper.is_aio_simplex(
                con_ssh=con_ssh):
            LOG.info("Check pod is running on the other controller as well")
            con_name = 'controller-1' if \
                con_ssh.get_hostname() == 'controller-0' else 'controller-0'
            from keywords import host_helper
            with host_helper.ssh_to_host(hostname=con_name,
                                         con_ssh=con_ssh) as other_con:
                remaining = __wait_for_resources_gone(other_con)
                if remaining:
                    return 3, remaining

    LOG.info("{} are successfully removed.".format(resource_names))
    return 0, None


def get_pods_info_yaml(type_names='pods', namespace=None, con_ssh=None,
                       fail_ok=False):
    """
    pods info parsed from yaml output of kubectl get cmd
    Args:
        namespace (None|str): e.g., kube-system, openstack, default. If set
        to 'all', use --all-namespaces.
        type_names (None|list|tuple|str): e.g., ("deployments.apps",
        "services/calico-typha")
        con_ssh:
        fail_ok:

    Returns (list): each item is a pod info dictionary

    """
    if isinstance(type_names, (list, tuple)):
        type_names = ','.join(type_names)
    args = type_names

    if namespace == 'all':
        args += ' --all-namespaces'
    elif namespace:
        args += ' --namespace={}'.format(namespace)

    args += ' -o yaml'

    code, out = exec_kube_cmd(sub_cmd='get', args=args, con_ssh=con_ssh,
                              fail_ok=fail_ok)
    if code > 0:
        return []

    try:
        pods_info = yaml.load(out)
    except yaml.YAMLError:
        LOG.warning('Output is not yaml')
        return []

    pods_info = pods_info.get('items', [pods_info])

    return pods_info


def get_pod_value_jsonpath(type_name, jsonpath, namespace=None, con_ssh=None):
    """
    Get value for specified pod with jsonpath
    Args:
        type_name (str): e.g., 'service/kubernetes'
        jsonpath (str): e.g., '{.spec.ports[0].targetPort}'
        namespace (str|None): e.g.,  'kube-system'
        con_ssh:

    Returns (str):

    """
    args = '{} -o jsonpath="{}"'.format(type_name, jsonpath)
    if namespace:
        args += ' --namespace {}'.format(namespace)

    args += ';echo'
    value = exec_kube_cmd('get', args, con_ssh=con_ssh)[1]
    return value


def expose_the_service(deployment_name, type, service_name, namespace=None,  con_ssh=None):
    """
    Exposes the service of a deployment
    Args:
        deployment_name (str): name of deployment
        type (str): "LoadBalancer" or "NodePort"
        service_name(str): service name
        namespace (str|None): e.g.,  'kube-system'
        con_ssh:

    Returns (str):

    """
    args = '{} --type={} --name={}'.format(deployment_name, type, service_name)
    if namespace:
        args += ' --namespace {}'.format(namespace)
    return exec_kube_cmd('expose deployment', args, con_ssh=con_ssh)


def get_nodes(hosts=None, status=None, field='STATUS', exclude=False,
              con_ssh=None, fail_ok=False):
    """
    Get nodes values via 'kubectl get nodes'
    Args:
        hosts (None|str|list|tuple): table filter
        status (None|str|list|tuple): table filter
        field (str|list|tuple): any header of the nodes table
        exclude (bool): whether to exclude rows with given criteria
        con_ssh:
        fail_ok:

    Returns (None|list): None if cmd failed.

    """
    code, output = exec_kube_cmd('get', args='nodes', con_ssh=con_ssh,
                                 fail_ok=fail_ok)
    if code > 0:
        return None

    table_ = table_parser.table_kube(output)
    if hosts or status:
        table_ = table_parser.filter_table(table_, exclude=exclude,
                                           **{'NAME': hosts, 'STATUS': status})

    return table_parser.get_multi_values(table_, field)


def wait_for_nodes_ready(hosts=None, timeout=120, check_interval=5,
                         con_ssh=None, fail_ok=False):
    """
    Wait for hosts in ready state via kubectl get nodes
    Args:
        hosts (None|list|str|tuple): Wait for all hosts ready if None is
            specified
        timeout:
        check_interval:
        con_ssh:
        fail_ok:

    Returns (tuple):
        (True, None)
        (False, <nodes_not_ready>(list))

    """
    end_time = time.time() + timeout
    nodes_not_ready = None
    while time.time() < end_time:
        nodes_not_ready = get_nodes(status='Ready', field='NAME',
                                    exclude=True, con_ssh=con_ssh,
                                    fail_ok=True)

        if nodes_not_ready and hosts:
            nodes_not_ready = list(set(nodes_not_ready) & set(hosts))

        if nodes_not_ready:
            LOG.info('{} not ready yet'.format(nodes_not_ready))
        elif nodes_not_ready is not None:
            LOG.info("All nodes are ready{}".format(
                ': {}'.format(hosts) if hosts else ''))
            return True, None

        time.sleep(check_interval)

    msg = '{} are not ready within {}s'.format(nodes_not_ready, timeout)
    LOG.warning(msg)
    if fail_ok:
        return False, nodes_not_ready
    else:
        raise exceptions.KubeError(msg)


def exec_cmd_in_container(cmd, pod, namespace=None, container_name=None,
                          stdin=None, tty=None, con_ssh=None,
                          fail_ok=False):
    """
    Execute given cmd in given pod via kubectl exec
    Args:
        cmd:
        pod:
        namespace:
        container_name:
        stdin:
        tty:
        con_ssh:
        fail_ok:

    Returns (tuple):
        (0, <std_out>)
        (1, <std_err>)

    """
    args = pod
    if namespace:
        args += ' -n {}'.format(namespace)
    if container_name:
        args += ' -c {}'.format(container_name)
    if stdin:
        args += ' -i'
    if tty:
        args += ' -t'
    args += ' -- {}'.format(cmd)

    code, output = exec_kube_cmd(sub_cmd='exec', args=args, con_ssh=con_ssh,
                                 fail_ok=fail_ok)
    return code, output


def wait_for_pods_healthy(pod_names=None, namespace=None, all_namespaces=True,
                          labels=None, timeout=300,
                          check_interval=5, con_ssh=None, fail_ok=False,
                          exclude=False, strict=False, **kwargs):
    """
    Wait for pods ready
    Args:
        pod_names (list|tuple|str|None): full name of pod(s)
        namespace (str|None):
        all_namespaces (bool|None)
        labels (str|dict|list|tuple|None):
        timeout:
        check_interval:
        con_ssh:
        fail_ok:
        exclude (bool)
        strict (bool): strict applies to node and name matching if given
        **kwargs

    Returns (tuple):

    """
    LOG.info("Wait for pods ready..")
    if not pod_names:
        pod_names = None
    elif isinstance(pod_names, str):
        pod_names = [pod_names]

    bad_pods = None
    end_time = time.time() + timeout
    while time.time() < end_time:
        bad_pods_info = get_unhealthy_pods(labels=labels,
                                           field=('NAME', 'STATUS'),
                                           namespace=namespace,
                                           all_namespaces=all_namespaces,
                                           con_ssh=con_ssh, exclude=exclude,
                                           strict=strict, **kwargs)
        bad_pods = {pod_info[0]: pod_info[1] for pod_info in bad_pods_info if
                    (not pod_names or pod_info[0] in pod_names)}
        if not bad_pods:
            LOG.info("Pods are Completed or Running.")
            if pod_names:
                pod_names = [pod for pod in pod_names if
                             not re.search('audit-|init-', pod)]
                if not pod_names:
                    return True

            is_ready = wait_for_running_pods_ready(
                pod_names=pod_names,
                namespace=namespace,
                all_namespaces=all_namespaces,
                labels=labels, timeout=int(end_time - time.time()),
                strict=strict,
                con_ssh=con_ssh,
                fail_ok=fail_ok, **kwargs)
            return is_ready
        time.sleep(check_interval)

    msg = 'Some pods are not Running or Completed: {}'.format(bad_pods)
    LOG.warning(msg)
    if fail_ok:
        return False
    dump_pods_info(con_ssh=con_ssh)
    raise exceptions.KubeError(msg)


def wait_for_running_pods_ready(pod_names=None, namespace=None,
                                all_namespaces=False, labels=None, timeout=300,
                                fail_ok=False, con_ssh=None, exclude=False,
                                strict=False, **kwargs):
    """
    Wait for Running pods to be Ready, such as 1/1, 3/3
    Args:
        pod_names:
        namespace:
        all_namespaces:
        labels:
        timeout:
        fail_ok:
        con_ssh:
        exclude:
        strict:
        **kwargs:

    Returns (bool):

    """
    unready_pods = get_unready_running_pods(namespace=namespace,
                                            all_namespaces=all_namespaces,
                                            pod_names=pod_names, labels=labels,
                                            exclude=exclude, strict=strict,
                                            con_ssh=con_ssh, **kwargs)
    if not unready_pods:
        return True

    end_time = time.time() + timeout
    while time.time() < end_time:
        pods_info = get_pods(field=('NAME', 'READY'), namespace=namespace,
                             all_namespaces=all_namespaces,
                             pod_names=unready_pods, con_ssh=con_ssh)
        for pod_info in pods_info:
            pod_name, pod_ready = pod_info
            ready_count, total_count = pod_ready.split('/')
            if ready_count == total_count:
                unready_pods.remove(pod_name)
        if not unready_pods:
            return True

    msg = "Some pods are not ready within {}s: {}".format(timeout, unready_pods)
    LOG.warning(msg)
    if fail_ok:
        return False
    raise exceptions.KubeError(msg)


def get_unready_running_pods(pod_names=None, namespace=None,
                             all_namespaces=False, labels=None,
                             con_ssh=None, exclude=False, strict=False,
                             **kwargs):
    """
    Get Running pods that are not yet Ready.
    Args:
        pod_names:
        namespace:
        all_namespaces:
        labels:
        con_ssh:
        exclude:
        strict:
        **kwargs:

    Returns (list): pod names

    """
    # field_selector does not work with pod_names, determine whether to use
    # field_selector or do post filtering instead
    # If field_selector is specified, the underlying get_pods function will
    # use pod_names for post filtering
    if exclude or labels or (not namespace and all_namespaces) or not pod_names:
        field_selector = 'status.phase=Running'
    else:
        field_selector = None
        kwargs['Status'] = 'Running'

    pods_running = get_pods(field=('NAME', 'READY'), namespace=namespace,
                            all_namespaces=all_namespaces,
                            pod_names=pod_names, labels=labels,
                            field_selectors=field_selector, grep='-v 1/1',
                            exclude=exclude, strict=strict, con_ssh=con_ssh,
                            fail_ok=True, **kwargs)
    not_ready_pods = []
    for pod_info in pods_running:
        pod_name, pod_ready = pod_info
        ready_count, total_count = pod_ready.split('/')
        if ready_count != total_count:
            not_ready_pods.append(pod_name)

    return not_ready_pods


def wait_for_openstack_pods_status(pod_names=None, application=None,
                                   component=None, status=PodStatus.RUNNING,
                                   con_ssh=None, timeout=60, check_interval=5,
                                   fail_ok=False):
    """
    Wait for openstack pods to be in Completed or Running state
    Args:
        pod_names (str|tuple|list|None):
        application (str|None): only used when pod_names are not provided
        component (str|None): only used when pod_names are not provided
        status (str|tuple|list|None):
        con_ssh:
        timeout:
        check_interval:
        fail_ok:

    Returns:

    """
    if not pod_names and not application and not component:
        raise ValueError(
            'pod_names, or application and component have to be provided to '
            'filter out pods')

    labels = None
    if not pod_names:
        labels = []
        if application:
            labels.append('application={}'.format(application))
        if component:
            labels.append('component={}'.format(component))

    return wait_for_pods_status(pod_names=pod_names, labels=labels,
                                status=status, namespace='openstack',
                                con_ssh=con_ssh, check_interval=check_interval,
                                timeout=timeout, fail_ok=fail_ok)


def get_pod_logs(pod_name, namespace='openstack', grep_pattern=None,
                 tail_count=10, strict=False,
                 fail_ok=False, con_ssh=None):
    """
    Get logs for given pod via kubectl logs cmd
    Args:
        pod_name (str): partial or full pod_name. If full name, set strict to
        True.
        namespace (str|None):
        grep_pattern (str|None):
        tail_count (int|None):
        strict (bool):
        fail_ok:
        con_ssh:

    Returns (str):

    """
    if pod_name and not strict:
        grep = '-E -i "{}|NAME"'.format(pod_name)
        pod_name = get_resources(namespace='openstack', resource_type='pod',
                                 con_ssh=con_ssh, rtn_list=True,
                                 grep=grep, fail_ok=fail_ok)[0].get('name')
    namespace = '-n {} '.format(namespace) if namespace else ''

    grep = ''
    if grep_pattern:
        if isinstance(grep_pattern, str):
            grep_pattern = (grep_pattern,)
        grep = ''.join(
            [' | grep --color=never {}'.format(grep_str) for grep_str in
             grep_pattern])
    tail = ' | tail -n {}'.format(tail_count) if tail_count else ''
    args = '{}{}{}{}'.format(namespace, pod_name, grep, tail)
    code, output = exec_kube_cmd(sub_cmd='logs', args=args, con_ssh=con_ssh)
    if not output and not fail_ok:
        raise exceptions.KubeError(
            "No kubectl logs found with args: {}".format(args))
    return output


def dump_pods_info(con_ssh=None):
    """
    Dump pods info for debugging purpose.
    Args:
        con_ssh:

    Returns:

    """
    LOG.info('------- Dump pods info --------')
    exec_kube_cmd('get pods',
                  '--all-namespaces -o wide | grep -v -e Running -e Completed',
                  con_ssh=con_ssh,
                  fail_ok=True)
    exec_kube_cmd(
        'get pods',
        "--all-namespaces -o wide | grep -v -e Running -e Completed "
        "-e NAMESPACE | awk "
        + """'{system("kubectl describe pods -n "$1" "$2)}'""""",
        con_ssh=con_ssh, fail_ok=True)


def get_openstack_pods(field='Name', namespace='openstack', application=None,
                       component=None, pod_names=None,
                       extra_labels=None, field_selectors=None,
                       exclude_label=False, fail_ok=False, con_ssh=None,
                       strict=True, exclude=False, **kwargs):
    """
    Get openstack pods via kubectl get pods
    Note that pod labels can be found via kubectl get pods -n <namespace>
    --show-labels
    Args:
        field (str|list|tuple):
        namespace:
        application (str|None): label: application
        component (str|None): label: component
        pod_names
        extra_labels (str|None):
        field_selectors (str|list|tuple|dict|None):
        exclude_label
        fail_ok:
        con_ssh:
        exclude:
        strict:
        **kwargs:

    Returns (list):

    """
    if pod_names:
        labels = None
    else:
        connector = '!=' if exclude_label else '='
        labels = []
        if application:
            labels.append('application{}{}'.format(connector, application))
        if component:
            labels.append('component{}{}'.format(connector, component))
        if extra_labels:
            labels.append(extra_labels)
        labels = ','.join(labels)

    pods = get_pods(pod_names=pod_names, field=field, namespace=namespace,
                    labels=labels, fail_ok=fail_ok,
                    field_selectors=field_selectors, strict=strict,
                    exclude=exclude, con_ssh=con_ssh, **kwargs)
    if not pods:
        msg = "No pods found for namespace - {} with selectors: {}".format(
            namespace, labels)
        LOG.info(msg)
        if not fail_ok:
            raise exceptions.KubeError(msg)

    return pods


def get_openstack_configs(conf_file, configs=None, node=None, pods=None,
                          label_component=None, label_app=None,
                          fail_ok=False, con_ssh=None):
    """
    Get config values for openstack pods with given chart
    Args:
        pods (str|list|tuple): openstack pod name(s)
        label_app (str|None): e.g., nova, neutron, panko, ...
        label_component (str|None): e.g., api, compute, etc.
        conf_file (str): config file path inside the filtered openstack
            container, e.g., /etc/nova/nova.conf
        configs (dict): {<section1>(str): <field(s)>(str|list|tuple),
            <section2>: ..}
            e.g., {'database': 'event_time_to_live'}
        node (str|None)
        fail_ok:
        con_ssh:

    Returns (dict): {<pod1>(str): <settings>(dict), ... }

    """
    if not pods and not (label_component and label_app):
        raise ValueError('Either pods, or label_component and label_app '
                         'have to be specified to locate the containers')

    if not pods:
        pods = get_openstack_pods(component=label_component,
                                  application=label_app, fail_ok=fail_ok,
                                  node=node,
                                  con_ssh=con_ssh)
    elif isinstance(pods, str):
        pods = (pods,)

    LOG.info('Getting {} {} values from openstack pods: {}'.format(conf_file,
                                                                   configs,
                                                                   pods))

    cmd = 'cat {}'.format(conf_file)
    if configs:
        all_fields = []
        section_filter = r'$1 ~ /^\[.*\]/'
        for fields in configs.values():
            if isinstance(fields, str):
                all_fields.append(fields)
            elif isinstance(fields, (tuple, list)):
                all_fields += list(fields)

        fields_filter = '|| '.join(
            ['$1 ~ /^{}/'.format(field) for field in set(all_fields)])
        cmd += r" | awk '{{ if ( {} || {})  print }}' | grep --color=never " \
               r"--group-separator='' -B 1 -v '\[.*\]'". \
            format(section_filter, fields_filter)

    config_values = {}
    for pod in pods:
        code, output = exec_cmd_in_container(cmd, pod=pod,
                                             namespace='openstack',
                                             con_ssh=con_ssh, fail_ok=fail_ok)
        if code > 0:
            config_values[pod] = {}
            continue

        # Remove irrelevant string at beginning of the output
        output = "[{}".format(
            re.split(r'\n\[', r'\n{}'.format(output), maxsplit=1)[-1])
        settings = configparser.ConfigParser()
        settings.read_string(output)
        config_values[pod] = settings

    return config_values
