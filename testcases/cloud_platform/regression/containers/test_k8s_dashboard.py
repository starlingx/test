import os
import time

from pytest import fixture, mark

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.rest.rest_client import RestClient
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.openstack.endpoint.openstack_endpoint_list_keywords import OpenStackEndpointListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.patch.kubectl_apply_patch_keywords import KubectlApplyPatchKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords
from keywords.k8s.serviceaccount.kubectl_delete_serviceaccount_keywords import KubectlDeleteServiceAccountKeywords
from keywords.k8s.token.kubectl_create_token_keywords import KubectlCreateTokenKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


def check_url_access(url: str) -> tuple:
    """
    Check the access to a given url.

    Args:
        url (str): URL to check.

    Returns:
        tuple: A tuple containing the status code and the response text.
    """
    get_logger().log_info(f"curl -i {url}...")
    req = RestClient().get(url=url)
    return req.response.status_code, req.response.text


def copy_k8s_files(request: fixture, ssh_connection: SSHConnection):
    """
    Copy the necessary k8s dashboard yaml files

    Args:
        request (fixture): pytest fixture
        ssh_connection (SSHConnection): ssh connection object
    """
    k8s_dashboard_dir = "k8s_dashboard"
    dashboard_file_names = ["admin-user.yaml", "kubeconfig.yaml", "k8s_dashboard.yaml"]
    get_logger().log_info("Creating k8s_dashboard directory")
    ssh_connection.send("mkdir -p {}".format(k8s_dashboard_dir))
    for dashboard_file_name in dashboard_file_names:
        local_path = get_stx_resource_path(f"resources/cloud_platform/containers/k8s_dashboard/{dashboard_file_name}")
        FileKeywords(ssh_connection).upload_file(local_path, f"/home/sysadmin/{k8s_dashboard_dir}/{dashboard_file_name}")

    def teardown():
        get_logger().log_info("Deleting k8s_dashboard directory")
        FileKeywords(ssh_connection).delete_folder_with_sudo(f"/home/sysadmin/{k8s_dashboard_dir}")

    request.addfinalizer(teardown)


def create_k8s_dashboard(request: fixture, namespace: str, con_ssh: SSHConnection):
    """
    Create all necessary resources for the k8s dashboard
    Args:
        request (fixture): pytest fixture
        namespace (str): kubernetes_dashboard namespace name
        con_ssh (SSHConnection): the SSH connection

    Raises:
        KeywordException: if the k8s dashboard is not accessible
    """
    k8s_dashboard_file = "k8s_dashboard.yaml"
    cert_dir = "k8s_dashboard_certs"

    name = "kubernetes-dashboard"
    port = 30000
    secrets_name = "kubernetes-dashboard-certs"

    home_k8s = "/home/sysadmin/k8s_dashboard"

    k8s_dashboard_file_path = os.path.join(home_k8s, k8s_dashboard_file)

    sys_domain_name = ConfigurationManager.get_lab_config().get_floating_ip()

    path_cert = os.path.join(home_k8s, cert_dir)
    get_logger().log_info(f"Creating {path_cert} directory")
    con_ssh.send("mkdir -p {}".format(path_cert))

    dashboard_key = "k8s_dashboard_certs/dashboard.key"
    dashboard_cert = "k8s_dashboard_certs/dashboard.crt"
    key = os.path.join(home_k8s, dashboard_key)
    crt = os.path.join(home_k8s, dashboard_cert)
    get_logger().log_info("Creating SSL certificate file for kubernetes dashboard secret")
    OpenSSLKeywords(con_ssh).create_certificate(key=key, crt=crt, sys_domain_name=sys_domain_name)
    KubectlCreateSecretsKeywords(ssh_connection=con_ssh).create_secret_generic(secret_name=secrets_name, tls_crt=crt, tls_key=key, namespace=namespace)

    get_logger().log_info(f"Creating resource from file {k8s_dashboard_file_path}")
    KubectlFileApplyKeywords(ssh_connection=con_ssh).apply_resource_from_yaml(k8s_dashboard_file_path)

    def teardown():
        KubectlFileDeleteKeywords(ssh_connection=con_ssh).delete_resources(k8s_dashboard_file_path)
        # delete created dashboard secret
        KubectlDeleteSecretsKeywords(con_ssh).cleanup_secret(namespace=namespace, secret_name=secrets_name)

    get_logger().log_info(f"Updating {name} service to be exposed on port {port}")
    arg_port = '{"spec":{"type":"NodePort","ports":[{"port":443, "nodePort": ' + str(port) + "}]}}"
    request.addfinalizer(teardown)
    KubectlApplyPatchKeywords(ssh_connection=con_ssh).apply_patch_service(svc_name=name, namespace=namespace, args_port=arg_port)

    get_logger().log_info("Waiting 30s for the service to be up")
    time.sleep(30)

    get_logger().log_info(f"Verify that {name} is working")
    end_point = OpenStackEndpointListKeywords(ssh_connection=con_ssh).get_k8s_dashboard_url()
    status_code, _ = check_url_access(end_point)
    if not status_code == 200:
        raise KeywordException(detailed_message=f"Kubernetes dashboard returned status code {status_code}")


def get_k8s_token(request: fixture, con_ssh: SSHConnection) -> str:
    """
    Get token for login to dashboard.

    For Kubernetes versions above 1.24.4, create an admin-user service-account
    in the kube-system namespace and bind the cluster-admin ClusterRoleBinding
    to this user. Then, create a token for this user in the kube-system namespace.

    Args:
        request (fixture): pytest fixture
        con_ssh (SSHConnection): SSH connection object

    Returns:
        str: Token for login to the dashboard
    """
    get_logger().log_info("Create the admin-user service-account in kube-system and bind the " "cluster-admin ClusterRoleBinding to this user")
    adminuserfile = "admin-user.yaml"
    serviceaccount = "admin-user"
    home_k8s = "/home/sysadmin/k8s_dashboard"

    admin_user_file_path = os.path.join(home_k8s, adminuserfile)

    get_logger().log_info("Creating the admin-user service-account")
    KubectlFileApplyKeywords(ssh_connection=con_ssh).apply_resource_from_yaml(admin_user_file_path)

    get_logger().log_info("Creating the token for admin-user")
    token = KubectlCreateTokenKeywords(ssh_connection=con_ssh).create_token(nspace="kube-system", user=serviceaccount)

    def teardown():
        get_logger().log_info(f"Removing serviceaccount {serviceaccount} in kube-system")
        KubectlDeleteServiceAccountKeywords(ssh_connection=con_ssh).cleanup_serviceaccount(serviceaccount_name=serviceaccount, nspace="kube-system")

    request.addfinalizer(teardown)

    get_logger().log_info(f"Token for login to dashboard: {token}")
    return token


@mark.p0
def test_k8s_dashboard_access(request):
    """
    Test the access to k8s dashboard by token
    and by kubeconfig file.


    Test Steps:
        Step 1: Transfer the dashboard files to the active controller (setup)
            - Copy test files from local to the SystemController.
            - Check the copies on the SystemController.
        Step 2: Create namespace kubernetes-dashboard
            - Check that the dashboard is correctly created

    Teardown:
        - Delete the kubernetes-dashboard namespace

    """

    # Step 1: Transfer the dashboard files to the active controller

    # Defines dashboard file name, source (local) and destination (remote) file paths.
    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    copy_k8s_files(request, ssh_connection)
    # Create Dashboard namespace
    namespace_name = "kubernetes-dashboard"
    kubectl_create_ns_keyword = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns_keyword.create_namespaces(namespace_name)

    # Get namespaces and confirm namespace is created
    ns_list = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()

    assert ns_list.is_namespace(namespace_name=namespace_name)

    def teardown():
        # cleanup created dashboard namespace
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace=namespace_name)

    request.addfinalizer(teardown)

    # Step 2: Create the necessary k8s dashboard resources
    test_namespace = "kubernetes-dashboard"
    create_k8s_dashboard(request, namespace=test_namespace, con_ssh=ssh_connection)

    # Step 3: Create the token for the dashboard
    get_k8s_token(request=request, con_ssh=ssh_connection)
