"""Keywords for the Calico Ingress Gateway and its Kubernetes Gateway API resources."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.calico.kubectl_calico_node_keywords import KubectlCalicoNodeKeywords
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.crd.kubectl_get_crd_keywords import KubectlGetCrdKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.gateway.object.envoy_service_object import EnvoyServiceObject
from keywords.k8s.gateway.object.kubectl_get_envoy_service_output import KubectlGetEnvoyServiceOutput
from keywords.k8s.gateway.object.kubectl_get_gateway_output import KubectlGetGatewayOutput
from keywords.k8s.gateway.object.kubectl_get_gatewayclass_output import KubectlGetGatewayClassOutput
from keywords.k8s.gateway.object.kubectl_get_httproute_output import KubectlGetHTTPRouteOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject
from keywords.network.ip_address_keywords import IPAddressKeywords

# Resource files applied to enable the Calico Ingress Gateway. On IPv6 and dual-stack clusters a
# custom EnvoyProxy (ipFamily: IPv6) is created and referenced from the GatewayClass.
GATEWAY_RESOURCE_DIR = "resources/cloud_platform/networking/calico"
GATEWAYAPI_RESOURCE = "gatewayapi_cr.yaml"
GATEWAYAPI_IPV6_RESOURCE = "gatewayapi_cr_ipv6.yaml"
ENVOYPROXY_IPV6_TEMPLATE = "envoyproxy_ipv6.yaml"
ENVOYPROXY_IPV6_NAME = "tigera-gateway-ipv6"
REMOTE_RESOURCE_DIR = "/tmp"
# Names created by the Calico operator for the Ingress Gateway.
GATEWAY_NAMESPACE = "tigera-gateway"
GATEWAY_CLASS_NAME = "tigera-gateway-class"
ENVOYPROXY_CRD_NAME = "envoyproxies.gateway.envoyproxy.io"
OWNING_GATEWAY_LABEL = "gateway.envoyproxy.io/owning-gateway-name"
GATEWAY_POLLING_SECONDS = 10
GATEWAY_CONTROL_PLANE_TIMEOUT_SECONDS = 180
# The gateway namespace removal waits for every object in it to be deleted. With the IPv6
# EnvoyProxy (IPv6-only and dual-stack clusters) this has been seen to take close to 4 minutes.
GATEWAY_TEARDOWN_TIMEOUT_SECONDS = 360
GATEWAY_RESOURCE_TIMEOUT_SECONDS = 120


class KubectlGatewayKeywords(K8sBaseKeyword):
    """Keywords for the Calico Ingress Gateway (GatewayAPI CR, Gateway, HTTPRoute and Envoy proxy)."""

    def _upload_gateway_resource(self, resource_name: str) -> str:
        """Upload a Gateway API resource file to the target system.

        Args:
            resource_name (str): The file name under the Calico networking resources directory.

        Returns:
            str: The remote path of the uploaded file.
        """
        remote_path = f"{REMOTE_RESOURCE_DIR}/{resource_name}"
        FileKeywords(self.ssh_connection).upload_file(get_stx_resource_path(f"{GATEWAY_RESOURCE_DIR}/{resource_name}"), remote_path, overwrite=True)
        return remote_path

    def enable_gateway_api(self) -> str:
        """Enable the Calico Ingress Gateway and wait for its control plane.

        Applies the GatewayAPI CR and waits for the GatewayClass. On IPv6-only and
        dual-stack clusters it also creates a custom EnvoyProxy (ipFamily: IPv6) and
        references it from the GatewayClass, as the Calico Ingress Gateway documentation
        requires, so the Envoy listener binds to :: and its readiness probes succeed.

        Returns:
            str: The cluster IP family ('ipv4', 'ipv6' or 'dual').
        """
        ip_family = KubectlGetInstallationKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_installation().get_ip_family()
        get_logger().log_info(f"Enabling the Calico Ingress Gateway on a {ip_family} cluster")
        apply_keywords = KubectlFileApplyKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())

        # When the gateway is not enabled, a previous run may still be tearing it down, and
        # enabling it before the namespace is gone races the operator's teardown.
        if not self.is_gateway_api_enabled():
            self.wait_for_gateway_teardown_complete()

        apply_keywords.apply_resource_from_yaml(self._upload_gateway_resource(GATEWAYAPI_RESOURCE))
        self.wait_for_crd_established(ENVOYPROXY_CRD_NAME)
        self.wait_for_gatewayclass_accepted(GATEWAY_CLASS_NAME)

        if ip_family in ("ipv6", "dual"):
            get_logger().log_info("Creating the IPv6 EnvoyProxy and referencing it from the GatewayClass")
            envoy_proxy_image = KubectlCalicoNodeKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_calico_image("envoy-proxy")
            envoyproxy_template = get_stx_resource_path(f"{GATEWAY_RESOURCE_DIR}/{ENVOYPROXY_IPV6_TEMPLATE}")
            envoyproxy_path = YamlKeywords(self.ssh_connection).generate_yaml_file_from_template(envoyproxy_template, {"envoy_proxy_image": envoy_proxy_image}, ENVOYPROXY_IPV6_TEMPLATE, REMOTE_RESOURCE_DIR)
            # Retried because the CRD RBAC can lag its establishment on the first enable.
            apply_keywords.apply_resource_from_yaml_with_retry(envoyproxy_path, timeout=60, poll_interval=GATEWAY_POLLING_SECONDS)
            apply_keywords.apply_resource_from_yaml(self._upload_gateway_resource(GATEWAYAPI_IPV6_RESOURCE))
            self.wait_for_gatewayclass_accepted(GATEWAY_CLASS_NAME)

        return ip_family

    def is_gateway_api_enabled(self) -> bool:
        """Check whether the Calico Ingress Gateway is enabled (the GatewayAPI CR exists).

        Returns:
            bool: True if the GatewayAPI CR 'default' exists, False otherwise.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get gatewayapi default --ignore-not-found -o name"))
        self.validate_success_return_code(self.ssh_connection)
        return "".join(output).strip() != ""

    def disable_gateway_api(self) -> None:
        """Disable the Calico Ingress Gateway and wait until its namespace is removed."""
        delete_keywords = KubectlDeleteResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        delete_keywords.delete_resource("envoyproxy", ENVOYPROXY_IPV6_NAME, namespace=GATEWAY_NAMESPACE)
        delete_keywords.delete_resource("gatewayapi", "default")
        self.wait_for_gateway_teardown_complete()

    def wait_for_gateway_teardown_complete(self, timeout: int = GATEWAY_TEARDOWN_TIMEOUT_SECONDS) -> None:
        """Wait until the gateway namespace is fully removed.

        Returns immediately when the gateway was never enabled.

        Args:
            timeout (int): Seconds to wait.
        """
        is_deleted = KubectlGetNamespacesKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).wait_for_namespace_deleted(GATEWAY_NAMESPACE, timeout=timeout, interval=GATEWAY_POLLING_SECONDS)
        validate_equals(is_deleted, True, f"Namespace {GATEWAY_NAMESPACE} is fully removed")

    def wait_for_crd_established(self, crd_name: str, timeout: int = GATEWAY_CONTROL_PLANE_TIMEOUT_SECONDS) -> None:
        """Wait for a CRD created by the operator to be Established.

        Args:
            crd_name (str): The fully-qualified CRD name.
            timeout (int): Seconds to wait.
        """
        crd_keywords = KubectlGetCrdKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())

        def is_crd_established() -> bool:
            return crd_keywords.get_crds().is_crd_present(crd_name) and crd_keywords.get_crd(crd_name).get_crd_by_name(crd_name).get_established() is True

        validate_equals_with_retry(is_crd_established, True, f"CRD {crd_name} is Established", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)

    def get_gatewayclass(self, gatewayclass_name: str) -> KubectlGetGatewayClassOutput:
        """Get a GatewayClass, which may not exist yet.

        Args:
            gatewayclass_name (str): The GatewayClass name.

        Returns:
            KubectlGetGatewayClassOutput: The parsed GatewayClass; is_present() is False when it does not exist.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get gatewayclass {gatewayclass_name} --ignore-not-found -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetGatewayClassOutput(output)

    def wait_for_gatewayclass_accepted(self, gatewayclass_name: str, timeout: int = GATEWAY_CONTROL_PLANE_TIMEOUT_SECONDS) -> None:
        """Wait for a GatewayClass to report Accepted=True.

        Args:
            gatewayclass_name (str): The GatewayClass name.
            timeout (int): Seconds to wait.
        """

        def is_gatewayclass_accepted() -> bool:
            return self.get_gatewayclass(gatewayclass_name).is_accepted()

        validate_equals_with_retry(is_gatewayclass_accepted, True, f"GatewayClass {gatewayclass_name} is Accepted", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)

    def get_gateway(self, gateway_name: str) -> KubectlGetGatewayOutput:
        """Get a Gateway.

        Args:
            gateway_name (str): The Gateway name.

        Returns:
            KubectlGetGatewayOutput: The parsed Gateway status.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get gateway {gateway_name} -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetGatewayOutput(output)

    def wait_for_gateway_accepted(self, gateway_name: str, timeout: int = GATEWAY_RESOURCE_TIMEOUT_SECONDS) -> None:
        """Wait for a Gateway to report Accepted=True.

        Args:
            gateway_name (str): The Gateway name.
            timeout (int): Seconds to wait.
        """

        def is_gateway_accepted() -> bool:
            return self.get_gateway(gateway_name).is_accepted()

        validate_equals_with_retry(is_gateway_accepted, True, f"Gateway {gateway_name} is Accepted", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)

    def wait_for_gateway_listener_programmed(self, gateway_name: str, listener_name: str, timeout: int = GATEWAY_RESOURCE_TIMEOUT_SECONDS) -> None:
        """Wait for a Gateway listener to report Programmed=True.

        Args:
            gateway_name (str): The Gateway name.
            listener_name (str): The listener name from the Gateway spec.
            timeout (int): Seconds to wait.
        """

        def is_listener_programmed() -> bool:
            return self.get_gateway(gateway_name).is_listener_programmed(listener_name)

        validate_equals_with_retry(is_listener_programmed, True, f"Gateway {gateway_name} listener {listener_name} is Programmed", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)

    def get_httproute(self, route_name: str) -> KubectlGetHTTPRouteOutput:
        """Get an HTTPRoute.

        Args:
            route_name (str): The HTTPRoute name.

        Returns:
            KubectlGetHTTPRouteOutput: The parsed HTTPRoute status.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get httproute {route_name} -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetHTTPRouteOutput(output)

    def wait_for_httproute_accepted(self, route_name: str, gateway_name: str, timeout: int = GATEWAY_RESOURCE_TIMEOUT_SECONDS) -> None:
        """Wait for an HTTPRoute to be Accepted by its parent Gateway.

        Args:
            route_name (str): The HTTPRoute name.
            gateway_name (str): The parent Gateway name.
            timeout (int): Seconds to wait.
        """

        def is_route_accepted() -> bool:
            return self.get_httproute(route_name).is_accepted_by(gateway_name)

        validate_equals_with_retry(is_route_accepted, True, f"HTTPRoute {route_name} is Accepted by Gateway {gateway_name}", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)

    def get_envoy_proxy_pods(self, gateway_name: str) -> list[KubectlPodObject]:
        """Get the Envoy proxy pods of a Gateway.

        Args:
            gateway_name (str): The owning Gateway name.

        Returns:
            list[KubectlPodObject]: The Envoy proxy pods; empty while the operator is still creating them.
        """
        return KubectlGetPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_pods_json(namespace=GATEWAY_NAMESPACE, label=f"{OWNING_GATEWAY_LABEL}={gateway_name}").get_pods()

    def wait_for_envoy_proxy_ready(self, gateway_name: str, timeout: int = GATEWAY_RESOURCE_TIMEOUT_SECONDS) -> KubectlPodObject:
        """Wait for the single Envoy proxy pod of a Gateway to be Running with every container ready.

        Args:
            gateway_name (str): The owning Gateway name.
            timeout (int): Seconds to wait.

        Returns:
            KubectlPodObject: The ready Envoy proxy pod.
        """

        def get_ready_envoy_proxy_pod_count() -> ValidationResponse:
            ready_pods = [pod for pod in self.get_envoy_proxy_pods(gateway_name) if pod.get_status() == "Running" and pod.is_ready()]
            return ValidationResponse(len(ready_pods), ready_pods)

        ready_pods = validate_equals_with_retry(get_ready_envoy_proxy_pod_count, 1, f"One Envoy proxy pod of Gateway {gateway_name} is Running with every container ready", timeout=timeout, polling_sleep_time=GATEWAY_POLLING_SECONDS)
        return ready_pods[0]

    def get_envoy_service(self, gateway_name: str) -> EnvoyServiceObject:
        """Get the Envoy proxy Service of a Gateway.

        Args:
            gateway_name (str): The owning Gateway name.

        Returns:
            EnvoyServiceObject: The Envoy proxy Service.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get services -n {GATEWAY_NAMESPACE} -l {OWNING_GATEWAY_LABEL}={gateway_name} -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetEnvoyServiceOutput(output).get_envoy_service()

    def get_envoy_proxy_node_ip(self, envoy_proxy_pod: KubectlPodObject, ip_family: str) -> str:
        """Get the address of the node that runs an Envoy proxy pod.

        The Envoy Service can keep NodePort traffic on the node that runs the proxy
        (externalTrafficPolicy: Local), so the node hosting the pod is used rather than
        an arbitrary node.

        Args:
            envoy_proxy_pod (KubectlPodObject): The Envoy proxy pod.
            ip_family (str): 'ipv4', 'ipv6' or 'dual'; IPv6 is used for 'ipv6' and 'dual'.

        Returns:
            str: The node InternalIP of the requested family.

        Raises:
            KeywordException: If the node has no InternalIP of that family.
        """
        ip_version = "IPv6" if ip_family in ("ipv6", "dual") else "IPv4"
        node = KubectlNodesKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_nodes_allocatable_resources().get_node_by_name(envoy_proxy_pod.get_node())
        node_ips = node.get_internal_ips() if node else []
        for node_ip in node_ips:
            if IPAddressKeywords(node_ip).check_ip_version(node_ip) == ip_version:
                return node_ip
        raise KeywordException(f"Node {envoy_proxy_pod.get_node()} running the Envoy proxy has no {ip_version} InternalIP; addresses: {node_ips}")
