from typing import Optional


class KubectlGlobalNetworkPolicyObject:
    """
    Class to hold attributes of a 'kubectl get globalnetworkpolicies.crd.projectcalico.org' policy entry.
    """

    def __init__(self, name: str):
        """Constructor.

        Args:
            name (str): Name of the GlobalNetworkPolicy.
        """
        self.name = name
        self.age: Optional[str] = None

    def get_name(self) -> str:
        """Getter for NAME entry.

        Returns:
            str: The name of the GlobalNetworkPolicy.
        """
        return self.name

    def set_age(self, age: str) -> None:
        """Setter for AGE.

        Args:
            age (str): Age of the GlobalNetworkPolicy.
        """
        self.age = age

    def get_age(self) -> Optional[str]:
        """Getter for AGE entry.

        Returns:
            Optional[str]: The age of the GlobalNetworkPolicy.
        """
        return self.age
