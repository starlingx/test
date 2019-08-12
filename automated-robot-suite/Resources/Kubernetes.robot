*** Settings ***
Documentation    Checks the health of the PODs, kube system services and
...    perform a helm override to openstack application.
...    Author(s):
...     - Jose Perez Carranza <jose.perez.carranza@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library      SSHLibrary
Library      Collections
Library      OperatingSystem
Library      Libraries/common.py
Library      String
Variables    Variables/Global.py
Variables    Variables/config_init.py    Config
...    %{PYTHONPATH}/Config/config.ini

*** Keywords ***
Check PODs Health
    [Documentation]    Check all OpenStack pods are healthy
    ${kubectl_cmd}    Set Variable    kubectl get pods --all-namespaces -o wide
    ${cmd}    Catenate    SEPARATOR=|    ${kubectl_cmd}    grep -v NAMESPACE
    ...    grep -v Running    grep -v Completed
    &{result}    Run Command    ${cmd}
    ${value}    Get From Dictionary    ${result}    stdout
    Should Be Empty    ${value}

Helm Override OpenStack
    [Arguments]    ${app_name}    ${char_name}    ${namespace}
    [Documentation]    Helm override for OpenStack nova chart and reset.
    ${kubectl_cmd}    Set Variable    system helm-override-update
    ${cmd}    Catenate    ${kubectl_cmd}    --set conf.nova.DEFAULT.foo=bar
    ...    ${app_name}    ${char_name}    ${namespace}
    Run Command    ${cmd}    True

Check Helm Override OpenStack
    [Documentation]    Check nova-compute.conf is updated in all nova-compute
    ...    containers.
    ${kubectl_cmd}    Set Variable    kubectl get pods --all-namespaces -o wide
    ${cmd}    Catenate    SEPARATOR=|    ${kubectl_cmd}    grep nova-compute
    ...    awk '{print $2}'
    &{result}    Run Command    ${cmd}
    @{nova_pod_list}    Convert Response To List    ${result}
    ${kubectl_cmd}    Set Variable    kubectl exec -n openstack -it
    : FOR    ${nova_pod}    IN    @{nova_pod_list}
    \    ${cmd}    Catenate    ${kubectl_cmd}    ${nova_pod}
    ...    -- grep foo /etc/nova/nova.conf
    \    &{result}    Run Command    ${cmd}
    \    Should Contain    ${result.stdout}    foo = bar

Check Kube System Services
    [Documentation]    Check pods status and kube-system services are
    ...    displayed.
    ${kubectl_cmd}    Set Variable    kubectl get services -n kube-system
    ${cmd}    Catenate    SEPARATOR=|    ${kubectl_cmd}    grep -v NAME
    ...    awk '{print $1}'
    &{result}    Run Command    ${cmd}
    ${kubeb_systems}    Get From Dictionary    ${result}    stdout
    Should Contain    ${kubeb_systems}    ingress
    Should Contain    ${kubeb_systems}    ingress-error-pages
    Should Contain    ${kubeb_systems}    ingress-exporter
    Should Contain    ${kubeb_systems}    kube-dns
    Should Contain    ${kubeb_systems}    tiller-deploy
    &{result}    Run Command    kubectl get deployments.apps -n kube-system
    ${kubeb_systems}    Get From Dictionary    ${result}    stdout
    Should Contain    ${kubeb_systems}    calico-kube-controllers
    Should Contain    ${kubeb_systems}    coredns
    Should Contain    ${kubeb_systems}    ingress-error-pages
    Should Contain    ${kubeb_systems}    rbd-provisioner
    Should Contain    ${kubeb_systems}    tiller-deploy

Create POD
    [Arguments]    ${pod_yml}    ${pod_name}
    [Documentation]    Create a POD.
    &{result}    Run Command    kubectl create -f ${pod_yml}
    ${value}    Get From Dictionary    ${result}    stdout
    Should Be Equal As Strings    ${value}    pod/${pod_name} created

Delete POD
    [Arguments]    ${pod_name}
    [Documentation]    Delete a POD.
    &{result}    Run Command    kubectl delete pods ${pod_name}    timeout=60
    ${value}    Get From Dictionary    ${result}    stdout
    Should Be Equal As Strings    ${value}    pod "${pod_name}" deleted

Check POD
    [Arguments]    ${pod_name}
    [Documentation]    Check if a POD is running.
    ${kubectl_cmd}    Set Variable    kubectl get pods -n default
    ${cmd}    Catenate    SEPARATOR=|    ${kubectl_cmd}    grep ${pod_name}
    ...    awk '{print $3}'
    &{result}    Run Command    ${cmd}
    ${status}    Get From Dictionary    ${result}    stdout
    Should Be Equal As Strings    ${status}    Running
