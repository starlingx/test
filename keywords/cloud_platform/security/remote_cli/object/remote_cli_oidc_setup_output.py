from keywords.cloud_platform.security.remote_cli.object.remote_cli_oidc_setup_object import RemoteCliOidcSetupObject


class RemoteCliOidcSetupOutput:
    """Holds the local file paths produced by the remote CLI OIDC setup.

    Populates a RemoteCliOidcSetupObject following the ACE framework output pattern.
    """

    def __init__(self, ca_cert_path: str, kubeconfig_path: str):
        """Constructor.

        Args:
            ca_cert_path (str): Local path to the downloaded system-local-ca certificate.
            kubeconfig_path (str): Local path to the generated OIDC kubeconfig file.
        """
        self.remote_cli_oidc_setup_object = RemoteCliOidcSetupObject()
        self.remote_cli_oidc_setup_object.set_ca_cert_path(ca_cert_path)
        self.remote_cli_oidc_setup_object.set_kubeconfig_path(kubeconfig_path)

    def get_remote_cli_oidc_setup_object(self) -> RemoteCliOidcSetupObject:
        """Get the OIDC setup object.

        Returns:
            RemoteCliOidcSetupObject: Object containing local CA cert and kubeconfig paths.
        """
        return self.remote_cli_oidc_setup_object
