from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.o_ran_o2_keywords import OAUTH2_CONTAINER_NAME
from keywords.cloud_platform.security.keycloak.keycloak_cli_keywords import KeycloakCliKeywords


class O2TokenKeywords(BaseKeyword):
    """Keywords for obtaining an O2 IMS OAuth2 Bearer token on the controller.

    The token is minted by running the token request on the controller over SSH,
    not from the test runner, because the issuer listens on a plain host port
    that is refused off-host. The client secret is read live from the issuer
    rather than stored, so no secret is committed to configuration.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller
                running the OAuth2 provider container.
        """
        self.ssh_connection = ssh_connection
        o2ims_config = ConfigurationManager.get_o2ims_config()
        self.realm = o2ims_config.get_realm()
        self.client_id = o2ims_config.get_client_id()
        self.admin_user = o2ims_config.get_issuer_admin_user()
        self.admin_password = o2ims_config.get_issuer_admin_password()
        issuer_url = f"http://localhost:{o2ims_config.get_issuer_port()}"
        self.keycloak_keywords = KeycloakCliKeywords(ssh_connection, OAUTH2_CONTAINER_NAME, issuer_url)

    def get_token(self) -> str:
        """Obtain an OAuth2 Bearer token for the O2 IMS client.

        Authenticates the issuer admin CLI (kcadm caches credentials in the
        container per session), reads the client secret live from the issuer,
        then mints the token on the controller. The token value is never logged;
        only its length is.

        Returns:
            str: The OAuth2 access token.

        Raises:
            KeywordException: If the client is not found or no access token is returned.
        """
        self.keycloak_keywords.login_as_admin(self.admin_user, self.admin_password, realm=self.realm)
        client_uuid = self.keycloak_keywords.get_client_uuid(self.client_id, realm=self.realm)
        client_secret = self.keycloak_keywords.get_client_secret(client_uuid, realm=self.realm)
        token = self.keycloak_keywords.get_token(self.client_id, client_secret, realm=self.realm)
        get_logger().log_info(f"Obtained O2 IMS Bearer token for client '{self.client_id}' ({len(token)} chars)")
        return token
