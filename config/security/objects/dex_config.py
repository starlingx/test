"""DexConfig object for typed access to DEX connector configuration.

Provides getters for all DEX connector configuration values
instead of raw dict access.
"""

from config.security.objects.dex_connector_attrs import DexConnectorAttrs
from config.security.objects.dex_test_user import DexTestUser
from config.security.objects.oidc_username_claim import OidcUsernameClaim
from config.security.objects.remote_oidc_config import RemoteOidcConfig
from config.security.objects.wad_connector_config import WadConnectorConfig


class DexConfig:
    """Typed configuration object for DEX connector settings.

    Provides getters for all DEX connector configuration values
    instead of raw dict access.
    """

    def __init__(self, config_dict: dict):
        """Initialize DexConfig from configuration dictionary.

        Args:
            config_dict (dict): DEX connector configuration dictionary.
        """
        self._oidc_app_name = config_dict.get("oidc_app_name", "oidc-auth-apps")
        self._namespace = config_dict.get("namespace", "kube-system")
        self._working_dir = config_dict.get("working_dir", "/home/sysadmin/dex-attr-test/")
        self._apply_timeout = config_dict.get("apply_timeout", 300)
        self._local_ldap = DexConnectorAttrs(config_dict.get("local_ldap", {}))
        self._wad_connector = WadConnectorConfig(config_dict.get("wad_connector", {}))
        self._remote_oidc = RemoteOidcConfig(config_dict.get("remote_oidc", {}))
        self._oidc_username_claim = OidcUsernameClaim(config_dict.get("oidc_username_claim", {}))
        self._test_user = DexTestUser(config_dict.get("test_user", {}))
        self._wad_test_user = DexTestUser(config_dict.get("wad_test_user", {}))
        self._keycloak_test_user = DexTestUser(config_dict.get("keycloak_test_user", {}))

    def get_oidc_app_name(self) -> str:
        """Get OIDC application name.

        Returns:
            str: Application name (e.g. 'oidc-auth-apps').
        """
        return self._oidc_app_name

    def get_namespace(self) -> str:
        """Get OIDC application namespace.

        Returns:
            str: Kubernetes namespace.
        """
        return self._namespace

    def get_working_dir(self) -> str:
        """Get working directory for override files.

        Returns:
            str: Working directory path on the lab.
        """
        return self._working_dir

    def get_apply_timeout(self) -> int:
        """Get application apply timeout.

        Returns:
            int: Timeout in seconds.
        """
        return self._apply_timeout

    def get_local_ldap(self) -> DexConnectorAttrs:
        """Get local LDAP connector attribute mappings.

        Returns:
            DexConnectorAttrs: LDAP attribute configuration.
        """
        return self._local_ldap

    def get_wad_connector(self) -> WadConnectorConfig:
        """Get WAD connector configuration.

        Returns:
            WadConnectorConfig: WAD connector config with attributes and server info.
        """
        return self._wad_connector

    def get_remote_oidc(self) -> RemoteOidcConfig:
        """Get remote OIDC (Keycloak) connector configuration.

        Returns:
            RemoteOidcConfig: Remote OIDC configuration.
        """
        return self._remote_oidc

    def get_oidc_username_claim(self) -> OidcUsernameClaim:
        """Get OIDC username claim configuration.

        Returns:
            OidcUsernameClaim: Username claim config with default and alternative.
        """
        return self._oidc_username_claim

    def get_test_user(self) -> DexTestUser:
        """Get LDAP test user configuration.

        Returns:
            DexTestUser: LDAP test user.
        """
        return self._test_user

    def get_wad_test_user(self) -> DexTestUser:
        """Get WAD test user configuration.

        Returns:
            DexTestUser: WAD test user.
        """
        return self._wad_test_user

    def get_keycloak_test_user(self) -> DexTestUser:
        """Get Keycloak test user configuration.

        Returns:
            DexTestUser: Keycloak test user.
        """
        return self._keycloak_test_user
