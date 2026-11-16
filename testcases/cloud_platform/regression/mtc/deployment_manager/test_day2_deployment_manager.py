"""Deployment Manager day-2 configuration update tests."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.cloud_platform.deployment_assets.deployment_config_yaml_keywords import DeploymentConfigYamlKeywords
from keywords.cloud_platform.deployment_manager.deployment_manager_keywords import DeploymentManagerKeywords
from keywords.cloud_platform.deployment_manager.deployment_manager_log_keywords import DeploymentManagerLogKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.datanetwork.system_datanetwork_list_keywords import SystemDatanetworkListKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.crd.kubectl_dm_resources_keywords import EXPECTED_RESOURCE_VALUES, RECONCILE_POLLING_INTERVAL, RECONCILE_TIMEOUT, KubectlDmResourcesKeywords
from keywords.k8s.crd.kubectl_systems_keywords import KubectlSystemsKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords

DEPLOYMENT_NAMESPACE = "deployment"


def _get_deployment_config_file() -> str:
    """Get the path of the deployment config file on the controller.

    Returns:
        str: Path of the deployment config file.
    """
    return ConfigurationManager.get_deployment_assets_config().get_controller_deployment_assets().get_deployment_config_file()


def _backup_deployment_config(ssh: SSHConnection, config_file: str) -> str:
    """Generate the deployment config file if it is missing, then copy it to a backup file next to it.

    Args:
        ssh (SSHConnection): SSH to the active controller.
        config_file (str): Path of the deployment config file.

    Returns:
        str: Path of the backup file.
    """
    DeploymentManagerKeywords(ssh).generate_deployment_config_if_missing(config_file)
    backup_file = f"{config_file}.backup"
    FileKeywords(ssh).copy_file(config_file, backup_file)
    return backup_file


def _restore_deployment_config(ssh: SSHConnection, config_file: str, backup_file: str, resources: list[tuple[str, str]]):
    """Put the backed-up deployment config file back and restore the original values of the changed resources.

    The deployment manager only honours a deployment scope that is set in the 'status' of the resource in the
    deployment config file and applied with the deployment manager playbook. A kubectl patch or kubectl apply
    of the scope is ignored after the initial synchronization.

    In the bootstrap scope the deployment manager does not push the file's values to the live system, so the
    original values are pushed back first: each changed resource that is in the backed-up file is applied with
    its original spec in the principal scope. Then it is moved back to bootstrap. The playbook does not restart
    the deployment manager pod when no resource has the principal scope, so the pod is restarted for the
    bootstrap scope to be applied.

    Resources that are not in the backed-up file, such as resources added by the test, are left to the caller.

    Args:
        ssh (SSHConnection): SSH to the active controller.
        config_file (str): Path of the deployment config file.
        backup_file (str): Path of the backup file.
        resources (list[tuple[str, str]]): (kind, name) of the resources changed by the test.
    """
    FileKeywords(ssh).copy_file(backup_file, config_file)

    yaml_keywords = DeploymentConfigYamlKeywords(ssh)
    restored_resources = [(kind, name) for kind, name in resources if yaml_keywords.has_resource(config_file, kind, name)]
    get_logger().log_info(f"Resources to restore to their original values: {restored_resources}")

    if restored_resources:
        for kind, name in restored_resources:
            yaml_keywords.update_resource(config_file, kind, name, scope="principal")
        get_logger().log_info("Apply the original values with deploymentscope principal using ansible-playbook cmd")
        DeploymentManagerKeywords(ssh).deploy_deployment_manager()
        for kind, name in restored_resources:
            validate_equals_with_retry(lambda kind=kind, name=name: KubectlDmResourcesKeywords(ssh).get_resource_status(kind, name)[1:], ("principal", "true"), f"{kind} {name} original values are reconciled (SCOPE, RECONCILED)", timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)

        for kind, name in restored_resources:
            yaml_keywords.update_resource(config_file, kind, name, scope="bootstrap")
        get_logger().log_info("Apply the deploymentscope to bootstrap using ansible-playbook cmd")
        DeploymentManagerKeywords(ssh).deploy_deployment_manager(restart_pod=True)
        for kind, name in restored_resources:
            validate_equals_with_retry(lambda kind=kind, name=name: KubectlDmResourcesKeywords(ssh).get_deployment_scope(kind, name), "bootstrap", f"{kind} {name} deploymentscope is bootstrap", timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)

    FileKeywords(ssh).move_file(backup_file, config_file)


@mark.p1
@mark.lab_is_standard
def test_config_update_datanetworks(request: FixtureRequest):
    """TC_28766 Configuration Update - Datanetworks

    Test Steps:
        - get the deployment config file with deployctl, back it up, set a DataNetwork description and apply it
        - verify datanetwork resource status
        - verify detection of a new expected delta configuration
        - update deploymentscope from principal value to bootstrap
        - verify values and delta after deploymentscope to bootstrap

    Teardown:
        - Restore backup file and apply the original dm configuration

    Args:
        request (FixtureRequest): The pytest request object.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    config_file = _get_deployment_config_file()
    resource_name = SystemDatanetworkListKeywords(ssh).system_datanetwork_list().get_system_datanetwork_objects()[0].get_name()
    description = "Description test"

    get_logger().log_setup_step("update dm config for datanetwork description and deploymentscope to principal")
    backup_file = _backup_deployment_config(ssh, config_file)
    start_time = DeploymentManagerLogKeywords(ssh).get_controller_utc_time()

    def teardown():
        get_logger().log_teardown_step("Restore backup deployment-config.yaml file and apply config")
        _restore_deployment_config(ssh, config_file, backup_file, [("DataNetwork", resource_name)])

    request.addfinalizer(teardown)

    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, "DataNetwork", resource_name, {"description": description}, "principal")
    get_logger().log_info("Apply the new configuration using ansible-playbook cmd")
    DeploymentManagerKeywords(ssh).deploy_deployment_manager()

    get_logger().log_test_case_step("verify datanetworks resource status")
    KubectlDmResourcesKeywords(ssh).wait_for_principal_status("DataNetwork", resource_name, "dm config datanetworks resource status (INSYNC, SCOPE, RECONCILED)")

    get_logger().log_test_case_step("verify detection of a new expected delta configuration")
    DeploymentManagerLogKeywords(ssh).wait_for_log_line(r"(\+Description: Description test)", start_time, "delta configuration for datanetwork description in the platform-deployment-manager logs")

    get_logger().log_test_case_step("update deploymentscope from principal value to bootstrap")
    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, "DataNetwork", resource_name, scope="bootstrap")
    get_logger().log_info("Apply the deploymentscope to bootstrap using ansible-playbook cmd")
    DeploymentManagerKeywords(ssh).deploy_deployment_manager(restart_pod=True)

    get_logger().log_test_case_step("verify values and delta after deploymentscope as bootstrap")
    expected_dn_values = {"Name": resource_name, "Description": description, "Scope": "bootstrap", "Reconciled": "true", "DELTA": ""}
    KubectlDmResourcesKeywords(ssh).wait_for_resource_values("DataNetwork", resource_name, expected_dn_values, "datanetwork values after deploymentscope to bootstrap")


@mark.p1
@mark.lab_is_standard
def test_config_update_ptp_interfaces(request: FixtureRequest):
    """TC_30499 Configuration Update - PtpInstances
    TC_30496 Configuration Update - PtpInterfaces

    Test Steps:
        - get the deployment config file with deployctl, back it up, add a PtpInstance and a PtpInterface and apply them
        - verify ptp instance and ptp interface resource status
        - verify resource info is added for ptp instance and ptp interface
        - update deploymentscope from principal value to bootstrap
        - verify values and delta after deploymentscope to bootstrap

    Teardown:
        - Restore backup file and apply the original dm configuration
        - Delete PtpInterfaces and PtpInstances resource

    Args:
        request (FixtureRequest): The pytest request object.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    config_file = _get_deployment_config_file()
    instance_resource_name = "ptp-test-in"
    instance_resource_type = "PtpInstance"
    interface_resource_name = "ptp-test-if"
    interface_resource_type = "PtpInterface"

    get_logger().log_setup_step("Set dm config for ptp instances and ptp interfaces and deploymentscope to principal")
    backup_file = _backup_deployment_config(ssh, config_file)
    start_time = DeploymentManagerLogKeywords(ssh).get_controller_utc_time()

    def teardown():
        get_logger().log_teardown_step("Restore backup deployment-config.yaml file")
        _restore_deployment_config(ssh, config_file, backup_file, [(interface_resource_type, interface_resource_name), (instance_resource_type, instance_resource_name)])

        get_logger().log_info(f"Deleting PtpInterface {interface_resource_name}")
        KubectlDeleteResourceKeywords(ssh).delete_resource(interface_resource_type, interface_resource_name, DEPLOYMENT_NAMESPACE)

        get_logger().log_info(f"Deleting PtpInstances {instance_resource_name}")
        KubectlDeleteResourceKeywords(ssh).delete_resource(instance_resource_type, instance_resource_name, DEPLOYMENT_NAMESPACE)

    request.addfinalizer(teardown)

    ptp_instance_config = {
        "apiVersion": "starlingx.windriver.com/v1",
        "kind": instance_resource_type,
        "metadata": {"labels": {"controller-tools.k8s.io": "1.0"}, "name": instance_resource_name, "namespace": DEPLOYMENT_NAMESPACE},
        "status": {"deploymentScope": "principal"},
        "spec": {"service": "clock", "parameters": ["devtest=true"]},
    }
    DeploymentConfigYamlKeywords(ssh).add_resources(config_file, [ptp_instance_config])
    DeploymentManagerKeywords(ssh).deploy_deployment_manager()

    ptp_interface_config = {
        "apiVersion": "starlingx.windriver.com/v1",
        "kind": interface_resource_type,
        "metadata": {"labels": {"controller-tools.k8s.io": "1.0"}, "name": interface_resource_name, "namespace": DEPLOYMENT_NAMESPACE},
        "spec": {"parameters": ["devtest=true"], "ptpinstance": instance_resource_name},
        "status": {"deploymentScope": "principal"},
    }
    DeploymentConfigYamlKeywords(ssh).add_resources(config_file, [ptp_interface_config])
    DeploymentManagerKeywords(ssh).deploy_deployment_manager()

    get_logger().log_test_case_step("verify ptp instance resource status")
    KubectlDmResourcesKeywords(ssh).wait_for_principal_status(instance_resource_type, instance_resource_name, "dm config ptp instance resource status (INSYNC, SCOPE, RECONCILED)")

    get_logger().log_test_case_step("verify ptp interface resource status")
    KubectlDmResourcesKeywords(ssh).wait_for_principal_status(interface_resource_type, interface_resource_name, "dm config ptp interface resource status (INSYNC, SCOPE, RECONCILED)")

    get_logger().log_test_case_step("verify resource info is added for ptp interface and ptp instance")
    DeploymentManagerLogKeywords(ssh).wait_for_log_line(rf"(ptpinstance-resource.*{instance_resource_name})", start_time, "resource info for PtpInstances in the platform-deployment-manager logs")
    DeploymentManagerLogKeywords(ssh).wait_for_log_line(rf"(Resource Info is added.*{interface_resource_name})", start_time, "resource info for PtpInterfaces in the platform-deployment-manager logs")

    get_logger().log_test_case_step("update deploymentscope from principal value to bootstrap")
    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, instance_resource_type, instance_resource_name, scope="bootstrap")
    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, interface_resource_type, interface_resource_name, scope="bootstrap")
    get_logger().log_info("Apply the deploymentscope to bootstrap using ansible-playbook cmd")
    DeploymentManagerKeywords(ssh).deploy_deployment_manager(restart_pod=True)

    get_logger().log_test_case_step("verify values and delta after deploymentscope as bootstrap")
    expected_instance_values = {"Type": instance_resource_type, "Name": instance_resource_name, "Scope": "bootstrap", "Reconciled": "true", "DELTA": ""}
    KubectlDmResourcesKeywords(ssh).wait_for_resource_values(instance_resource_type, instance_resource_name, expected_instance_values, "ptp instance values after deploymentscope to bootstrap")

    expected_interface_values = {"Type": interface_resource_type, "Name": interface_resource_name, "Scope": "bootstrap", "Reconciled": "true", "DELTA": ""}
    KubectlDmResourcesKeywords(ssh).wait_for_resource_values(interface_resource_type, interface_resource_name, expected_interface_values, "ptp interface values after deploymentscope to bootstrap")


@mark.p1
@mark.lab_is_standard
def test_config_update_system(request: FixtureRequest):
    """TC_30495 Configuration Update - System

    Test Steps:
        - get the deployment config file with deployctl, back it up, set the System description and apply it
        - verify system resource status
        - verify system description configuration
        - update deploymentscope from principal value to bootstrap
        - verify values and delta after deploymentscope to bootstrap

    Teardown:
        - Restore backup file and apply the original dm configuration

    Args:
        request (FixtureRequest): The pytest request object.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    config_file = _get_deployment_config_file()
    description = "Description test"

    get_logger().log_setup_step("update dm config for system description and deploymentscope to principal")
    resource_name = KubectlSystemsKeywords(ssh).get_systems(namespace=DEPLOYMENT_NAMESPACE).get_systems()[0].get_name()
    backup_file = _backup_deployment_config(ssh, config_file)

    def teardown():
        get_logger().log_teardown_step("Restore backup deployment-config.yaml file and apply config")
        _restore_deployment_config(ssh, config_file, backup_file, [("System", resource_name)])

    request.addfinalizer(teardown)

    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, "System", resource_name, {"description": description}, "principal")
    get_logger().log_info("Apply the new configuration using ansible-playbook cmd")
    DeploymentManagerKeywords(ssh).deploy_deployment_manager()

    get_logger().log_test_case_step("verify system resource status")

    def _get_system_status() -> tuple:
        system = KubectlSystemsKeywords(ssh).get_systems(namespace=DEPLOYMENT_NAMESPACE).get_system(resource_name)
        return system.get_insync(), system.get_scope(), system.get_reconciled()

    get_resource_values = validate_equals_with_retry(_get_system_status, EXPECTED_RESOURCE_VALUES, "dm config system resource status (INSYNC, SCOPE, RECONCILED)", timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)
    get_logger().log_info(f"get system resource values : {get_resource_values}")

    get_logger().log_test_case_step("verify update system description configuration")
    # The deployment manager does not log the system description update, so the live system is checked.
    validate_equals_with_retry(lambda: SystemShowKeywords(ssh).system_show().get_system_show_object().get_description(), description, "system description configuration is applied to the live system", timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)

    get_logger().log_test_case_step("update deploymentscope from principal value to bootstrap")
    DeploymentConfigYamlKeywords(ssh).update_resource(config_file, "System", resource_name, scope="bootstrap")
    get_logger().log_info("Apply the deploymentscope to bootstrap using ansible-playbook cmd")
    DeploymentManagerKeywords(ssh).deploy_deployment_manager(restart_pod=True)

    get_logger().log_test_case_step("verify values and delta after deploymentscope as bootstrap")
    expected_dn_values = {"Name": resource_name, "Description": description, "Scope": "bootstrap", "Reconciled": "true", "DELTA": ""}
    KubectlDmResourcesKeywords(ssh).wait_for_resource_values("System", resource_name, expected_dn_values, "system values after deploymentscope to bootstrap")
