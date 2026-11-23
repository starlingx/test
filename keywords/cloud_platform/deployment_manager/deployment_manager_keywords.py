import re

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords

DEPLOYMENT_MANAGER_ROLES_SOURCE = "/usr/local/share/applications/playbooks/roles"
DEPLOYMENT_MANAGER_ROLES_DESTINATION = "roles"
DEPLOYMENT_MANAGER_OVERRIDES_FILE = "local-install-overrides.yaml"
DEPLOYMENT_MANAGER_PLAYBOOK_TIMEOUT = 1800
DEPLOYMENT_MANAGER_NAMESPACE = "platform-deployment-manager"
DEPLOYMENT_MANAGER_POD_LABEL = "app=platform-deployment-manager"
DEPLOYMENT_MANAGER_POD_READY_TIMEOUT = 120


class DeploymentManagerKeywords(BaseKeyword):
    """
    This class applies the deployment config to the Deployment Manager with the deployment manager playbook.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def generate_deployment_config_if_missing(self, config_file: str):
        """Generate the deployment config file with the deployctl tool if it is not on the controller yet.

        Args:
            config_file (str): Path of the deployment config file on the controller.
        """
        if not FileKeywords(self.ssh_connection).file_exists(config_file):
            get_logger().log_info(f"{config_file} not found, generate the deployment configuration file with deployctl")
            lab_name = ConfigurationManager.get_lab_config().get_lab_name()
            self.ssh_connection.send("chmod +x deployctl")
            self.ssh_connection.send(f"./deployctl build -n deployment -s {lab_name} --minimal-config")
            self.validate_success_return_code(self.ssh_connection)
        else:
            get_logger().log_info(f"{config_file} already exists, skip the deployment configuration file generation")

    def deploy_deployment_manager(self, restart_pod: bool = False):
        """Apply the deployment config with the deployment manager playbook.

        The playbook is run from the home directory of the controller, with the roles directory
        copied next to it as the playbook requires.

        The playbook restarts the deployment manager pod only when a resource in the file has the
        principal scope. When no resource has it, for example when a resource is moved back from
        principal to bootstrap, the running pod does not pick up the new scope. Set restart_pod
        so that the pod is restarted and the new scope is applied.

        Args:
            restart_pod (bool): Restart the deployment manager pod after the playbook run.

        Raises:
            KeywordException: If the playbook run is not reported as successful in its PLAY RECAP.
        """
        if not FileKeywords(self.ssh_connection).file_exists(DEPLOYMENT_MANAGER_ROLES_DESTINATION):
            get_logger().log_info(f"Copy {DEPLOYMENT_MANAGER_ROLES_SOURCE} to {DEPLOYMENT_MANAGER_ROLES_DESTINATION}")
            self.ssh_connection.send(f"cp -r {DEPLOYMENT_MANAGER_ROLES_SOURCE} {DEPLOYMENT_MANAGER_ROLES_DESTINATION}")

        playbook = ConfigurationManager.get_deployment_assets_config().get_controller_deployment_assets().get_deploy_playbook_file()
        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        command = f'ansible-playbook {playbook} -e "@{DEPLOYMENT_MANAGER_OVERRIDES_FILE}" -e "ansible_become_pass={admin_password}"'

        output = self.ssh_connection.send(command, command_timeout=DEPLOYMENT_MANAGER_PLAYBOOK_TIMEOUT)
        self.validate_success_return_code(self.ssh_connection)

        recap = self.get_play_recap_result(output)
        if recap.get("failed") != "0" or recap.get("unreachable") != "0":
            raise KeywordException(f"{command} did not finish without failures. PLAY RECAP result: {recap}")

        if restart_pod:
            self.restart_deployment_manager_pod()

    def restart_deployment_manager_pod(self):
        """Restart the deployment manager pod and wait until the new pod is Ready.

        Uses the same commands as the principal task of the deployment manager playbook.
        'kubectl delete' returns once the old pod is gone, so 'kubectl wait' only sees the new pod.
        """
        get_logger().log_info("Restart the deployment manager pod")
        delete_command = f"kubectl -n {DEPLOYMENT_MANAGER_NAMESPACE} delete pods --selector '{DEPLOYMENT_MANAGER_POD_LABEL}'"
        self.ssh_connection.send(K8sConfigExporter().export(delete_command))
        self.validate_success_return_code(self.ssh_connection)
        KubectlWaitPodKeywords(self.ssh_connection).wait_for_pods_ready(DEPLOYMENT_MANAGER_POD_LABEL, DEPLOYMENT_MANAGER_NAMESPACE, timeout=DEPLOYMENT_MANAGER_POD_READY_TIMEOUT)

    def get_play_recap_result(self, output: list[str]) -> dict:
        """Read the per-host counters of the PLAY RECAP of an ansible-playbook run.

        Args:
            output (list[str]): Output lines of the ansible-playbook run.

        Returns:
            dict: Counter name to value, e.g. {"ok": "10", "failed": "0"}. Empty if there is no PLAY RECAP.
        """
        text = "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else str(output)
        if "PLAY RECAP" not in text:
            return {}
        recap_line = text.split("PLAY RECAP")[1].splitlines()[1]
        return dict(re.findall(r"(\w+)=(\d+)", recap_line))
