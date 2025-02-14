import os

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.secure_transfer_file.secure_transfer_file import SecureTransferFile
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.dashboard.kubectl_dashboard_apply_keywords import KubectlDashboardApplyKeywords
from keywords.k8s.dashboard.kubectl_dashboard_delete_keywords import KubectlDeleteDashboardKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords
from pytest import mark


def copy_k8s_files(ssh_connection):
    """
    Copy the necessary k8s dashboard yaml files

    Args:
        ssh_connection (SSHConnection): ssh connection object
    """
    k8s_dashboard_dir = 'k8s_dashboard'
    dashboard_file_names = list()
    dashboard_file_names = ['admin-user.yaml', 'kubeconfig.yaml', 'k8s_dashboard.yaml']
    get_logger().log_info("Creating k8s_dashboard directory")
    ssh_connection.send('mkdir -p {}'.format(k8s_dashboard_dir))
    for dashboard_file_name in dashboard_file_names:
        local_path = get_stx_resource_path(f'resources/cloud_platform/containers/k8s_dashboard/{dashboard_file_name}')
        remote_path = f'/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{k8s_dashboard_dir}/{dashboard_file_name}'

        # Opens an SFTP session to active controller.
        sftp_client = ssh_connection.get_sftp_client()

        # Sets the parameters for the app file transfer through a new instance of SecureTransferFileInputObject.
        secure_transfer_file_input_object = SecureTransferFileInputObject()
        secure_transfer_file_input_object.set_sftp_client(sftp_client)
        secure_transfer_file_input_object.set_origin_path(local_path)
        secure_transfer_file_input_object.set_destination_path(remote_path)
        secure_transfer_file_input_object.set_transfer_direction(TransferDirection.FROM_LOCAL_TO_REMOTE)
        secure_transfer_file_input_object.set_force(True)

        # Transfers the dashboard file from local path to remote path.
        secure_transfer_file = SecureTransferFile(secure_transfer_file_input_object)
        file_transfer_succeeded = secure_transfer_file.transfer_file()

        # Asserts the file was really transferred.
        assert file_transfer_succeeded


def create_k8s_dashboard(request, namespace, con_ssh):
    """
    Create all necessary resources for the k8s dashboard
    Args:
        namespace (str): kubernetes_dashboard namespace name
        con_ssh (SSHConnection): the SSH connection
    """
    # k8s_dashboard_file = "k8s_dashboard.yaml"
    # cert = 'k8s_dashboard_certs'
    dashboard_key = 'k8s_dashboard_certs/dashboard.key'
    dashboard_cert = 'k8s_dashboard_certs/dashboard.crt'

    # port = 30000
    secrets_name = 'kubernetes-dashboard-certs'

    # k8s_dashboard_file = "k8s_dashboard.yaml"

    home_k8s = "/home/sysadmin/k8s_dashboard"
    path_cert = os.path.join(home_k8s, dashboard_cert)
    key = os.path.join(home_k8s, dashboard_key)
    crt = os.path.join(home_k8s, dashboard_cert)
    kubeconfig_file_path = os.path.join(home_k8s, "kubeconfig.yaml")

    sys_domain_name = ConfigurationManager.get_lab_config().get_floating_ip()
    get_logger().log_info(f"Creating {path_cert} directory")
    con_ssh.send('mkdir -p {}'.format(path_cert))
    get_logger().log_info("Creating SSL certificate file for kubernetes dashboard secret")
    con_ssh.send('openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout {} -out {} ' '-subj "/CN={}"'.format(key, crt, sys_domain_name))

    KubectlCreateSecretsKeywords.create_secret_generic(secret_name=secrets_name, tls_crt=crt, tls_key=key)
    get_logger().log_info(f"Creating resource from file {kubeconfig_file_path}")

    KubectlDashboardApplyKeywords(ssh_connection=con_ssh).dashboard_apply_from_yaml(kubeconfig_file_path)

    def teardown():
        KubectlDeleteDashboardKeywords(ssh_connection=con_ssh).delete_resources(kubeconfig_file_path)
        # delete created dashboard secret
        KubectlDeleteSecretsKeywords(con_ssh).delete_secret(secret_name=secrets_name)

    request.addfinalizer(teardown)


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
    copy_k8s_files(ssh_connection)
    # Create Dashboard namespace
    namespace_name = 'kubernetes-dashboard'
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
    # TODO:
    # test_namespace = 'kubernetes-dashboard'
    # create_k8s_dashboard(namespace=test_namespace, con_ssh=ssh_connection)
