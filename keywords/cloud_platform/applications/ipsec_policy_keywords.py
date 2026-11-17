"""IPsec policy operations composed with existing ACE Kubernetes readers."""

import re
from shlex import quote

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.cloud_platform.applications.object.ipsec_manager_workload_output import IPsecManagerWorkloadOutput
from keywords.cloud_platform.applications.object.ipsec_policy_configuration_output import IPsecPolicyConfigurationOutput
from keywords.cloud_platform.applications.object.ipsec_policy_images_output import IPsecPolicyImagesOutput
from keywords.cloud_platform.applications.object.ipsec_policy_list_output import IPsecPolicyListOutput
from keywords.cloud_platform.applications.object.ipsec_policy_nodes_output import IPsecPolicyNodesOutput
from keywords.cloud_platform.security.objects.ipsec_policy_sa_output import IPsecPolicySAOutput
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.daemonsets.kubectl_get_daemonsets_keywords import KubectlGetDaemonsetsKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.get_resource.object.kubernetes_resource_list_output import KubernetesResourceListOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput
from keywords.k8s.rollout.kubectl_rollout_status_keywords import KubectlRolloutStatusKeywords
from keywords.python.string import String

DEFAULT_READINESS_TIMEOUT = 300
DEFAULT_POLL_INTERVAL = 5
APPLICATION_NAME = "ipsec-policy-operator"
POLICY_RESOURCE = "ipsecpolicies.starlingx.io"


class IPsecPolicyKeywords(K8sBaseKeyword):
    """Read policy state independently from the management-IPsec SA parser."""

    def get_policies(self) -> IPsecPolicyListOutput:
        """Read cluster-scoped policies without treating command failure as absence.

        Returns:
            IPsecPolicyListOutput: Policy identity and desired-state records.
        """
        content = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_resource_field(POLICY_RESOURCE, "", "{@}")
        return IPsecPolicyListOutput(content)

    def has_policy_crd(self) -> bool:
        """Check CRD existence without treating failed reads as absence.

        Returns:
            bool: Whether the policy CRD exists in a checked inventory response.
        """
        content = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_resource_field("customresourcedefinitions", "", "{@}")
        resources = KubernetesResourceListOutput(content).get_resources()
        return any(item.get_name() == POLICY_RESOURCE for item in resources)

    def get_node_configuration(self, node: str) -> IPsecPolicyConfigurationOutput:
        """Read the per-node ConfigMap, including legacy or JSON configuration.

        Args:
            node (str): Independently discovered node name.

        Returns:
            IPsecPolicyConfigurationOutput: Decoded configuration evidence.
        """
        content = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_resource_field("configmaps", quote(f"system-ipsec-configmap-{node}"), "{@}", APPLICATION_NAME)
        return IPsecPolicyConfigurationOutput(content)

    def get_eligible_nodes(self, family: int = 4) -> IPsecPolicyNodesOutput:
        """Resolve ready non-storage nodes and cluster-host IPs independently.

        Args:
            family (int): Configured IP family, 4 or 6.

        Returns:
            IPsecPolicyNodesOutput: Eligible node identities and InternalIPs.
        """
        if family not in (4, 6):
            raise KeywordException("IP family must be 4 or 6")
        kubeconfig = self.k8s_config.get_kubeconfig_path()
        workload = KubectlGetDaemonsetsKeywords(self.ssh_connection, kubeconfig).get_daemonset_workload(APPLICATION_NAME)
        eligible = set(workload.get_eligible_nodes())
        hosts = {host.get_host_name(): host for host in SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_hosts()}
        content = KubectlGetResourceKeywords(self.ssh_connection, kubeconfig).get_resource_field("nodes", "", "{@}")
        return IPsecPolicyNodesOutput(content, eligible, hosts, family)

    def wait_for_agents_ready(self, timeout: int = DEFAULT_READINESS_TIMEOUT) -> dict[str, dict]:
        """Wait for current agent rollout using shared DaemonSet readiness.

        Args:
            timeout (int): Maximum wait in seconds.

        Returns:
            dict[str, dict]: Ready current agent pods indexed by node.
        """

        def has_scheduled_nodes() -> bool:
            """Observe asynchronous app-label propagation before the rollout wait.

            Returns:
                bool: Whether rendered scheduling now has eligible nodes.
            """
            workload = KubectlGetDaemonsetsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_daemonset_workload(APPLICATION_NAME)
            return bool(workload.get_matching_nodes())

        validate_equals_with_retry(has_scheduled_nodes, True, "Policy agent scheduling labels propagated", timeout=timeout, polling_sleep_time=DEFAULT_POLL_INTERVAL)
        return KubectlWaitPodKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).wait_for_daemonset_ready(APPLICATION_NAME, timeout=timeout)

    def read_policy_security_associations(self, node_connection: SSHConnection) -> IPsecPolicySAOutput:
        """Read policy SAs on the explicitly connected host without modifying them.

        Args:
            node_connection (SSHConnection): Connection to the independently selected host.

        Returns:
            IPsecPolicySAOutput: Parsed current IKE and CHILD_SA evidence.
        """
        output = node_connection.send_as_sudo_non_interactive("swanctl --list-sas --raw")
        self.validate_success_return_code(node_connection)
        return IPsecPolicySAOutput(output)

    def read_loaded_connections(self, node_connection: SSHConnection) -> str:
        """Read effective loaded connections, separately from ConfigMap intent.

        Args:
            node_connection (SSHConnection): Connection to the selected host.

        Returns:
            str: Nonempty loaded-connection evidence for policy connections.
        """
        output = node_connection.send_as_sudo_non_interactive("swanctl --list-conns")
        self.validate_success_return_code(node_connection)
        text = String.normalize_command_output(output)
        if "k8s-node-" not in text:
            raise KeywordException("No loaded policy connections")
        return text

    def read_node_configuration_file(self, node_connection: SSHConnection) -> str:
        """Read the agent-generated configuration without touching credentials.

        Args:
            node_connection (SSHConnection): Connection to the selected host.

        Returns:
            str: Nonempty generated configuration.
        """
        output = node_connection.send_as_sudo_non_interactive("cat /etc/swanctl/conf.d/k8s-nodes.conf")
        self.validate_success_return_code(node_connection)
        text = String.normalize_command_output(output)
        if not text.strip():
            raise KeywordException("Empty generated policy configuration")
        return text

    def get_running_images(self, timeout: int = DEFAULT_READINESS_TIMEOUT) -> IPsecPolicyImagesOutput:
        """Read current agent and manager container identities after rollout.

        Args:
            timeout (int): Rollout and manager convergence timeout.

        Returns:
            IPsecPolicyImagesOutput: Role/workload image evidence.
        """
        pods = self.wait_for_agents_ready(timeout)
        images = {}
        for node, pod in pods.items():
            images[f"agent/{node}"] = PodJsonOutput(pod).get_container_digests()

        def observe_manager_images() -> ValidationResponse:
            """Refresh manager evidence while old rollout pods terminate.

            Returns:
                ValidationResponse: Images when coverage is complete, else pending.
            """
            manager_images = self._get_manager_images(timeout)
            return ValidationResponse(manager_images is not None, manager_images)

        manager_images = validate_equals_with_retry(observe_manager_images, True, "Manager terminating pods removed and current coverage ready", timeout=timeout, polling_sleep_time=DEFAULT_POLL_INTERVAL)
        for workload in manager_images.get_workload_names():
            images[workload] = manager_images.get_container_images(workload)
        if any(not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for containers in images.values() for digest in containers.values()):
            raise KeywordException("Missing immutable image identity")
        return IPsecPolicyImagesOutput(images)

    def _get_manager_images(self, timeout: int = DEFAULT_READINESS_TIMEOUT) -> IPsecPolicyImagesOutput | None:
        """Read manager coverage, returning pending only for terminating pods.

        Args:
            timeout (int): Maximum rollout command duration.

        Returns:
            IPsecPolicyImagesOutput | None: Manager images, or pending evidence.
        """
        kubeconfig = self.k8s_config.get_kubeconfig_path()
        reader = KubectlGetResourceKeywords(self.ssh_connection, kubeconfig)
        deployment_name = "ipsec-policy-manager-controller-manager"
        KubectlRolloutStatusKeywords(self.ssh_connection, kubeconfig).wait_for_deployment_rollout(APPLICATION_NAME, deployment_name, timeout)

        return IPsecManagerWorkloadOutput(
            reader.get_resource_field("deployment", deployment_name, "{@}", APPLICATION_NAME),
            reader.get_resource_field("replicasets", "", "{@}", APPLICATION_NAME),
            reader.get_resource_field("pods", "", "{@}", APPLICATION_NAME),
        ).get_ready_images()

    def verify_candidate(self, version: str, images: dict[str, dict[str, str]], provenance: dict[str, str]) -> IPsecPolicyImagesOutput:
        """Verify an installed candidate without substituting released content.

        Candidate tarballs/custom ISOs are installed through existing application
        and lab APIs. This gate also supports configured unmerged image overrides.

        Args:
            version (str): Expected applied application/package version.
            images (dict[str, dict[str, str]]): Agent and manager container digests.
            provenance (dict[str, str]): Separate application_revision, automation_revision and build_reference.

        Returns:
            IPsecPolicyImagesOutput: Actual immutable container identities.
        """
        valid_images = bool(version) and set(images) == {"agent", "manager"} and all(values and all(re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for digest in values.values()) for values in images.values())
        validate_equals(valid_images, True, "Candidate version and all agent/manager container digests are supplied")
        valid_provenance = all(provenance.get(key) for key in ("application_revision", "automation_revision", "build_reference"))
        validate_equals(valid_provenance, True, "Separate application, automation and build provenance is supplied")

        validate_equals(SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME), (version, "applied"), "Applied policy application matches requested candidate version")
        observed = self.get_running_images()
        for workload in observed.get_workload_names():
            validate_equals(observed.get_container_images(workload), images[workload.split("/", 1)[0]], f"Candidate container identities on {workload}")
        get_logger().log_info(f"Policy candidate provenance: {provenance}; version={version}; images={observed.get_log_summary()}")
        return observed
