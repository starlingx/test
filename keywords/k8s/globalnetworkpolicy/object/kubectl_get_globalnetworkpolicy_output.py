from typing import List

from keywords.k8s.globalnetworkpolicy.object.kubectl_get_globalnetworkpolicy_table_parser import KubectlGetGlobalNetworkPolicyTableParser
from keywords.k8s.globalnetworkpolicy.object.kubectl_globalnetworkpolicy_object import KubectlGlobalNetworkPolicyObject


class KubectlGetGlobalNetworkPolicyOutput:
    """
    Class for 'kubectl get globalnetworkpolicies.crd.projectcalico.org output' keywords
    """

    def __init__(self, kubectl_get_globalnetworkpolicy_output: List[str]):
        """
        Constructor

        Args:
            kubectl_get_globalnetworkpolicy_output (List[str]): Raw output lines from running a "kubectl get globalnetworkpolicies.crd.projectcalico.org" command.

        """
        self.kubectl_globalnetworkpolicies: List[KubectlGlobalNetworkPolicyObject] = []
        kubectl_get_globalnetworkpolicy_table_parser = KubectlGetGlobalNetworkPolicyTableParser(kubectl_get_globalnetworkpolicy_output)
        output_values_list = kubectl_get_globalnetworkpolicy_table_parser.get_output_values_list()

        for policy_dict in output_values_list:

            if "NAME" not in policy_dict:
                raise ValueError(f"There is no NAME associated with the GlobalNetworkPolicy: {policy_dict}")

            policy = KubectlGlobalNetworkPolicyObject(policy_dict["NAME"])

            if "AGE" in policy_dict:
                policy.set_age(policy_dict["AGE"])

            self.kubectl_globalnetworkpolicies.append(policy)

    def get_globalnetworkpolicies(self) -> List[KubectlGlobalNetworkPolicyObject]:
        """
        Return the list of all GlobalNetworkPolicies available.

        Returns:
            List[KubectlGlobalNetworkPolicyObject]: List of GlobalNetworkPolicy objects.

        """
        return self.kubectl_globalnetworkpolicies

    def get_globalnetworkpolicy_by_name(self, policy_name: str) -> KubectlGlobalNetworkPolicyObject:
        """
        Return a GlobalNetworkPolicy with the specified name.

        Args:
            policy_name (str): The name of the GlobalNetworkPolicy to retrieve.

        Returns:
            KubectlGlobalNetworkPolicyObject: The GlobalNetworkPolicy object with the specified name.

        Raises:
            ValueError: If no GlobalNetworkPolicy with the specified name is found.
        """
        for policy in self.kubectl_globalnetworkpolicies:
            if policy.get_name() == policy_name:
                return policy
        raise ValueError(f"GlobalNetworkPolicy '{policy_name}' not found")

    def has_globalnetworkpolicy(self, policy_name: str) -> bool:
        """
        Check if a GlobalNetworkPolicy with the specified name exists.

        Args:
            policy_name (str): The name of the GlobalNetworkPolicy to check.

        Returns:
            bool: True if the GlobalNetworkPolicy exists, False otherwise.

        """
        for policy in self.kubectl_globalnetworkpolicies:
            if policy.get_name() == policy_name:
                return True
        return False
