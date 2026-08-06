class EjbcaConfig:
    """Configuration for EJBCA PKI system application tests."""

    def __init__(self, ejbca_dict: dict):
        """Initialize EJBCA configuration from config dictionary.

        Args:
            ejbca_dict (dict): The 'ejbca' section from security JSON5.
        """
        self._ejbca = ejbca_dict
        self._cmp = ejbca_dict.get("cmp", {})
        self._rest = ejbca_dict.get("rest", {})
        self._postgres = ejbca_dict.get("postgres", {})
        self._pod_counts = ejbca_dict.get("pod_counts", {})
        self._performance = ejbca_dict.get("performance", {})
        self._cert_manager = ejbca_dict.get("cert_manager", {})
        self._backup = ejbca_dict.get("backup", {})

    def get_app_name(self) -> str:
        """Get EJBCA application name."""
        return self._ejbca["app_name"]

    def get_namespace(self) -> str:
        """Get EJBCA Kubernetes namespace."""
        return self._ejbca["namespace"]

    def get_tarball_path(self) -> str:
        """Get path to EJBCA application tarball."""
        return self._ejbca["tarball_path"]

    def get_hostname(self) -> str:
        """Get EJBCA hostname for Helm override."""
        return self._ejbca["hostname"]

    def get_app_apply_timeout(self) -> int:
        """Get timeout for application apply operation."""
        return self._ejbca["app_apply_timeout"]

    def get_app_upload_timeout(self) -> int:
        """Get timeout for application upload operation."""
        return self._ejbca["app_upload_timeout"]

    def get_pod_ready_timeout(self) -> int:
        """Get timeout for pods to become ready."""
        return self._ejbca["pod_ready_timeout"]

    def get_pg_failover_timeout(self) -> int:
        """Get timeout for PostgreSQL failover completion."""
        return self._ejbca["pg_failover_timeout"]

    def get_swact_recovery_timeout(self) -> int:
        """Get timeout for EJBCA recovery after controller swact."""
        return self._ejbca["swact_recovery_timeout"]

    def get_ejbca_pod_label(self) -> str:
        """Get label selector for EJBCA pods."""
        return self._ejbca["ejbca_pod_label"]

    def get_pg_cluster_name(self) -> str:
        """Get PostgreSQL cluster resource name."""
        return self._ejbca["pg_cluster_name"]

    def get_management_ca_name(self) -> str:
        """Get ManagementCA name."""
        return self._ejbca["management_ca_name"]

    def get_crypto_token_name(self) -> str:
        """Get CryptoToken name."""
        return self._ejbca["crypto_token_name"]

    def get_superadmin_username(self) -> str:
        """Get SuperAdmin end entity username."""
        return self._ejbca["superadmin_username"]

    def get_superadmin_p12_path(self) -> str:
        """Get path to SuperAdmin P12 file inside EJBCA pod."""
        return self._ejbca["superadmin_p12_path"]

    def get_cmp_alias(self) -> str:
        """Get CMP alias name."""
        return self._cmp["alias"]

    def get_cmp_hmac_secret(self) -> str:
        """Get CMP HMAC shared secret."""
        return self._cmp["hmac_secret"]

    def get_cmp_internal_server(self) -> str:
        """Get CMP internal server address."""
        return self._cmp["internal_server"]

    def get_cmp_internal_path(self) -> str:
        """Get CMP internal URL path."""
        return self._cmp["internal_path"]

    def get_cmp_external_port(self) -> int:
        """Get CMP external port via OAM."""
        return self._cmp["external_port"]

    def get_rest_base_path(self) -> str:
        """Get REST API base path."""
        return self._rest["base_path"]

    def get_rest_cert_profile(self) -> str:
        """Get REST certificate profile name."""
        return self._rest["cert_profile"]

    def get_rest_ee_profile(self) -> str:
        """Get REST end entity profile name."""
        return self._rest["ee_profile"]

    def get_rest_ca_name(self) -> str:
        """Get REST CA name for enrollment."""
        return self._rest["ca_name"]

    def get_rest_enroll_password(self) -> str:
        """Get REST enrollment password."""
        return self._rest["enroll_password"]

    def get_pg_database_name(self) -> str:
        """Get PostgreSQL database name."""
        return self._postgres["database_name"]

    def get_pg_expected_table_count(self) -> int:
        """Get expected PostgreSQL table count."""
        return self._postgres["expected_table_count"]

    def get_pg_tls_secret_name(self) -> str:
        """Get PostgreSQL TLS secret name."""
        return self._postgres["tls_secret_name"]

    def get_pg_cluster_cr_name(self) -> str:
        """Get PostgreSQL Cluster CR name."""
        return self._postgres["cluster_cr_name"]

    def get_ejbca_replicas(self, system_type: str) -> int:
        """Get expected EJBCA replica count for a system type.

        Args:
            system_type (str): One of 'simplex', 'duplex', 'standard'.

        Returns:
            int: Expected EJBCA replica count.
        """
        return self._pod_counts[system_type]["ejbca_replicas"]

    def get_pg_instances(self, system_type: str) -> int:
        """Get expected PostgreSQL instance count for a system type.

        Args:
            system_type (str): One of 'simplex', 'duplex', 'standard'.

        Returns:
            int: Expected PG instance count.
        """
        return self._pod_counts[system_type]["pg_instances"]

    def get_performance_csr_rates(self) -> list:
        """Get list of CSR rates for performance testing."""
        return self._performance["csr_rates"]

    def get_performance_duration(self) -> int:
        """Get performance test duration in seconds."""
        return self._performance["duration_seconds"]

    def get_cert_manager_issuer_group(self) -> str:
        """Get cert-manager EJBCA issuer group."""
        return self._cert_manager["issuer_group"]

    def get_cert_manager_cluster_issuer_name(self) -> str:
        """Get cert-manager ClusterIssuer name."""
        return self._cert_manager["cluster_issuer_name"]

    def get_backup_playbook_path(self) -> str:
        """Get path to EJBCA backup ansible playbook."""
        return self._backup["playbook_path"]

    def get_restore_playbook_path(self) -> str:
        """Get path to EJBCA restore ansible playbook."""
        return self._backup["restore_playbook_path"]

    def get_backup_dir(self) -> str:
        """Get backup directory path."""
        return self._backup["backup_dir"]
