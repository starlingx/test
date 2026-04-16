class RemoteCliOidcSetupObject:
    """Represents the local file paths produced by the remote CLI OIDC setup.

    Follows the ACE framework object pattern.
    """

    def __init__(self):
        """Constructor."""
        self.ca_cert_path = None
        self.kubeconfig_path = None

    def set_ca_cert_path(self, ca_cert_path: str):
        """
        Setter for the ca_cert_path.
        """
        self.ca_cert_path = ca_cert_path

    def get_ca_cert_path(self) -> str:
        """
        Getter for the ca_cert_path.
        """
        return self.ca_cert_path

    def set_kubeconfig_path(self, kubeconfig_path: str):
        """
        Setter for the kubeconfig_path.
        """
        self.kubeconfig_path = kubeconfig_path

    def get_kubeconfig_path(self) -> str:
        """
        Getter for the kubeconfig_path.
        """
        return self.kubeconfig_path
