*** Settings ***
Documentation    Check the health of PODs services; update and apply the
...    helm chart via system application-apply.
...    Author(s):
...     - Hector Ivan Ramos Escobar <ramos.escobarx.hector.ivan@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Resource          Resources/Kubernetes.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    Utils.Stx Suite TearDown

*** Variables ***
${pod_yml}            testpod.yaml
${pod_name}           testpod
${chart_manifest}     helm-charts-manifest.tgz
${host_image_path}    /home/${CLI_USER_NAME}/

*** Test Cases ***
OpenStack PODs Healthy
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Check all OpenStack pods are healthy, in Running or
    ...    Completed state.
    Check System Application Status    stx-openstack    applied
    Check PODs Health

Reapply STX OpenStack
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Re apply stx openstack application without any
    ...    modification to helm charts.
    System Application Apply    stx-openstack

STX OpenStack Override Update Reset
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Helm override for OpenStack nova chart and reset.
    Helm Override OpenStack    stx-openstack    nova    openstack
    System Application Apply    stx-openstack
    Check Helm Override OpenStack

Kube System Services
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Check pods status and kube-system services are
    ...    displayed.
    Check PODs Health
    Check Kube System Services

Create Check Delete POD
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Launch a POD via kubectl.
    Put File    %{PYTHONPATH}/Utils/${pod_yml}
    ...    ${host_image_path}/${pod_yml}
    Create POD    ${pod_yml}    ${pod_name}
    Wait Until Keyword Succeeds    1 min     5 sec    Check POD    ${pod_name}
    Delete POD    ${pod_name}
