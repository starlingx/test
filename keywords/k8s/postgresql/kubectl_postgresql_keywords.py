"""Generic PostgreSQL operations executed inside a Kubernetes pod via kubectl exec.

This is a product-agnostic runner for SQL against a PostgreSQL database that runs
inside a Kubernetes pod. It resolves the postgres pod by name prefix within a
caller-supplied namespace, then runs ``psql`` in that pod with ``kubectl exec``.

Unlike ``cloud_platform/postgresql/PostgresqlKeywords`` (which runs ``sudo -u
postgres psql`` on a host over SSH), this keyword targets a pod.

Database, user, and container are caller-supplied arguments with no product-specific
defaults. Namespace and kubeconfig are passed in by the caller (product config
resolves them).
"""

import shlex

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class KubectlPostgresqlKeywords(K8sBaseKeyword):
    """Execute SQL against a PostgreSQL pod via kubectl exec."""

    DEFAULT_POD_PREFIX = "postgresql"

    def __init__(self, ssh_connection: SSHConnection, namespace: str, kubeconfig_path: str = None) -> None:
        """Initialize the pod-based PostgreSQL runner.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with kubectl access to the cluster.
            namespace (str): Kubernetes namespace where the PostgreSQL pod runs.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.namespace = namespace

    def get_postgres_pod_name(self, pod_prefix: str = DEFAULT_POD_PREFIX) -> str:
        """Resolve the postgres pod name by prefix within the namespace.

        Exposed so callers running several statements can resolve the pod once and
        pass it into ``execute_sql_no_result``, avoiding a ``kubectl get pods`` lookup
        per statement.

        Args:
            pod_prefix (str): Pod name prefix to match. Defaults to "postgresql".

        Returns:
            str: The full postgres pod name (e.g. "postgresql-0").

        Raises:
            KeywordException: If no running pod matches the prefix.
        """
        pods_output = KubectlGetPodsKeywords(self.ssh_connection, kubeconfig_path=self.k8s_config.get_kubeconfig_path()).get_pods(namespace=self.namespace)
        return pods_output.get_single_pod_start_with(pod_prefix, status="Running").get_name()

    def execute_sql_no_result(self, statement: str, database: str, db_user: str, container: str, pod_name: str = None, pod_prefix: str = DEFAULT_POD_PREFIX) -> None:
        """Execute a SQL statement that returns no result set.

        Runs arbitrary SQL (UPDATE, DELETE, INSERT, DDL) inside the postgres pod,
        delegating the kubectl-exec plumbing to KubectlExecInPodsKeywords. Success
        is guaranteed by the absence of an exception, so this returns None (the
        caller provides everything; nothing new is produced).

        Pod resolution is decoupled from execution: pass ``pod_name`` when it is
        already known (e.g. resolved once via ``get_postgres_pod_name`` before a batch
        of statements). When omitted, the pod is resolved from ``pod_prefix``.

        Args:
            statement (str): SQL statement to execute.
            database (str): Database to connect to.
            db_user (str): PostgreSQL role to connect as.
            container (str): Pod container running PostgreSQL.
            pod_name (str, optional): Target postgres pod name. If None, resolved via
                ``get_postgres_pod_name(pod_prefix)``.
            pod_prefix (str): Pod name prefix used to resolve the pod when ``pod_name``
                is not supplied. Defaults to "postgresql".

        Raises:
            AssertionError: If the kubectl exec command fails.
        """
        if pod_name is None:
            pod_name = self.get_postgres_pod_name(pod_prefix)
        psql_cmd = f"psql -U {shlex.quote(db_user)} -d {shlex.quote(database)} -c {shlex.quote(statement)}"
        options = f"-n {shlex.quote(self.namespace)} -c {shlex.quote(container)}"
        KubectlExecInPodsKeywords(self.ssh_connection, kubeconfig_path=self.k8s_config.get_kubeconfig_path()).run_pod_exec_cmd(pod_name, psql_cmd, options)
