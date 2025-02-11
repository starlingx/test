from config.configuration_manager import ConfigurationManager
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.secure_transfer_file.secure_transfer_file import SecureTransferFile
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from pytest import mark


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

    dashboard_file_name = 'admin-user.yaml'
    local_path = get_stx_resource_path(f'resources/cloud_platform/containers/k8s_dashboard/{dashboard_file_name}')
    remote_path = f'/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{dashboard_file_name}'

    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

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
