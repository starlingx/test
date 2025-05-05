from config.configuration_manager import ConfigurationManager
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.helm.system_helm_keywords import SystemHelmKeywords

from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.service.system_service_keywords import SystemServiceKeywords

from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords

from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_not_equals


def test_install_oidc():
    """
    Install (Upload and Apply) Application OIDC

    Raises:
        Exception: If application OIDC failed to upload or apply
    """

    # Setups app configs, obj instances and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    oidc_name = app_config.get_oidc_app_name()
    file_path_oidc: str = "/home/sysadmin/oidc/"
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    file_keywords = FileKeywords(ssh_connection)
    helm_keywords = SystemHelmKeywords(ssh_connection)
    oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
    addrpool_keywords = SystemAddrpoolListKeywords(ssh_connection)
    mgmt_ip = addrpool_keywords.get_management_floating_address()
    bind_pw = KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
    lab_ipv6 = ConfigurationManager.get_lab_config().is_ipv6()
    oam_ip = f"[{oam_ip}]" if lab_ipv6 else oam_ip

    # Verifies if the app is already uploaded
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(oidc_name):
        oidc_app_status = system_applications.get_application(oidc_name).get_status()
        validate_equals(oidc_app_status, "uploaded", f"{oidc_name} is already uploaded")
    else:
        # Setups the upload input object
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(oidc_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{oidc_name}*.tgz")

        # Uploads the app file and verifies it
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
        system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
        oidc_app_status = system_applications.get_application(oidc_name).get_status()
        validate_equals(oidc_app_status, "uploaded", f"{oidc_name} upload status validation")


    # Configures and applies Kubernetes OIDC service parameters
    sys_service = SystemServiceKeywords(ssh_connection)
    sys_service.add_service_parameter("kubernetes", "kube_apiserver oidc-client-id", "stx-oidc-client-app")
    sys_service.add_service_parameter("kubernetes", "kube_apiserver oidc-groups-claim", "groups")
    sys_service.add_service_parameter("kubernetes", "kube_apiserver oidc-issuer-url", f"https://{oam_ip}:30556/dex")
    sys_service.add_service_parameter("kubernetes", "kube_apiserver oidc-username-claim", "email")
    sys_service.apply_kubernetes_service_parameters()

    # Creates and applies OIDC auth yaml
    file_keywords.create_directory(file_path_oidc)
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/oidc/oidc-auth-apps-certificate.yaml")
    replacement_dictionary = {"oam_ip": oam_ip.strip("[]")}
    oidc_auth_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, "oidc-auth-apps-certificate.yaml", file_path_oidc, True)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(oidc_auth_yaml)

    # Creates dex and local LDAP certs
    dex_ca_cert = KubectlGetSecretsKeywords(ssh_connection).get_secret_with_custom_output(secret_name="system-local-ca", namespace="cert-manager", output_format="jsonpath", extra_parameters='"{.data.ca\.crt}"', base64=True)
    file_keywords.create_file_with_echo("/home/sysadmin/oidc/dex-ca-cert.crt", dex_ca_cert)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_generic(namespace="kube-system", secret_name="dex-ca-cert", tls_crt="/home/sysadmin/oidc/dex-ca-cert.crt")
    local_ldap_ca_cert = KubectlGetSecretsKeywords(ssh_connection).get_secret_with_custom_output(secret_name="system-local-ca", namespace="cert-manager", output_format="jsonpath", extra_parameters='"{.data.ca\.crt}"', base64=True)
    file_keywords.create_file_with_echo("/home/sysadmin/oidc/local-ldap-ca-cert.crt", local_ldap_ca_cert)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_generic(namespace="kube-system", secret_name="local-ldap-ca-cert", tls_crt="/home/sysadmin/oidc/local-ldap-ca-cert.crt")

    # Creates and applies OIDC client, secret observer and dex overrides
    yaml_path = get_stx_resource_path("resources/cloud_platform/nightly_regression/oidc/oidc-client-overrides.yaml")
    file_keywords.upload_file(yaml_path, f"{file_path_oidc}oidc-client-overrides.yaml", False)
    helm_keywords.helm_override_update("oidc-auth-apps", "oidc-client", "kube-system", f"{file_path_oidc}oidc-client-overrides.yaml")
    yaml_path = get_stx_resource_path("resources/cloud_platform/nightly_regression/oidc/secret-observer-overrides.yaml")
    file_keywords.upload_file(yaml_path, f"{file_path_oidc}secret-observer-overrides.yaml", False)
    helm_keywords.helm_override_update("oidc-auth-apps", "secret-observer", "kube-system", f"{file_path_oidc}secret-observer-overrides.yaml")
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/oidc/dex-overrides.yaml")
    replacement_dictionary = {"oam_ip": oam_ip, "mgmt_ip": mgmt_ip, "bind_pw": bind_pw}
    dex_auth_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, "dex-overrides.yaml", file_path_oidc, True)
    helm_keywords.helm_override_update("oidc-auth-apps", "dex", "kube-system", dex_auth_yaml)

    # Applies the app and verifies if it became applied
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(oidc_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"System application object should not be None")
    validate_equals(system_application_object.get_name(), oidc_name, f"Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"Application status validation")


def test_uninstall_oidc():
    """
    Uninstall (Remove and Delete) Application OIDC

    Raises:
        Exception: If application OIDC failed to remove or delete
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    oidc_name = app_config.get_oidc_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    
    # Verifies if the app is present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(oidc_name), True, f"The {oidc_name} application should be uploaded/applied on the system")

    # Removes the application
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(oidc_name)
    system_application_remove_input.set_force_removal(False)
    system_application_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    validate_equals(system_application_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"Application removal status validation")

    # Deletes the application
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(oidc_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {oidc_name} deleted.\n", f"Application deletion message validation")
