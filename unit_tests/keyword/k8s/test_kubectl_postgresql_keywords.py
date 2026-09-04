"""Unit tests for KubectlPostgresqlKeywords.execute_sql_no_result.

Verifies the SQL-building path of execute_sql_no_result without a live cluster:
when the caller supplies a pod name, no pod resolution happens and the psql
command is assembled and sent verbatim through kubectl exec. When the pod name
is omitted, the keyword falls back to resolving it via get_postgres_pod_name.

The base keyword logs every keyword call, so each test patches the logger to
avoid requiring a configured logger.
"""

import shlex
from unittest.mock import NonCallableMagicMock, patch

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.postgresql.kubectl_postgresql_keywords import KubectlPostgresqlKeywords


def build_mock_ssh_connection() -> NonCallableMagicMock:
    """Build a non-callable mocked SSH connection.

    A non-callable mock is required because BaseKeyword.__getattribute__ wraps
    callable attributes with its keyword-logging hook.

    Returns:
        NonCallableMagicMock: The mocked SSH connection reporting a success return code.
    """
    ssh_connection = NonCallableMagicMock(spec=SSHConnection)
    ssh_connection.send.return_value = ""
    ssh_connection.get_return_code.return_value = 0
    return ssh_connection


@patch("keywords.base_keyword.get_logger")
def test_execute_sql_with_pod_name_skips_resolution(mock_get_logger):
    """A supplied pod name is used directly, without resolving the pod."""
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="db-ns", kubeconfig_path="/tmp/fake-kubeconfig")

    with patch("keywords.k8s.postgresql.kubectl_postgresql_keywords.KubectlGetPodsKeywords") as mock_get_pods:
        keyword.execute_sql_no_result(
            statement="DELETE FROM metrics;",
            database="cloudify_db",
            db_user="cloudify",
            container="postgresql",
            pod_name="postgresql-0",
        )

    mock_get_pods.assert_not_called()


@patch("keywords.base_keyword.get_logger")
def test_execute_sql_builds_expected_kubectl_exec_command(mock_get_logger):
    """The kubectl exec command carries the pod, namespace, container, and psql invocation."""
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="db-ns", kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.execute_sql_no_result(
        statement="DELETE FROM metrics;",
        database="cloudify_db",
        db_user="cloudify",
        container="postgresql",
        pod_name="postgresql-0",
    )

    sent_command = ssh_connection.send.call_args[0][0]
    assert "kubectl exec" in sent_command
    assert "postgresql-0" in sent_command
    assert "-n db-ns" in sent_command
    assert "-c postgresql" in sent_command
    assert "psql -U cloudify -d cloudify_db -c" in sent_command
    assert "DELETE FROM metrics;" in sent_command


@patch("keywords.base_keyword.get_logger")
def test_execute_sql_quotes_statement_with_spaces(mock_get_logger):
    """A statement with spaces and embedded quotes is shell-quoted as a single argument."""
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="db-ns", kubeconfig_path="/tmp/fake-kubeconfig")

    statement = "UPDATE metrics SET timestamp = timestamp - interval '2 days'"
    keyword.execute_sql_no_result(
        statement=statement,
        database="cloudify_db",
        db_user="cloudify",
        container="postgresql",
        pod_name="postgresql-0",
    )

    sent_command = ssh_connection.send.call_args[0][0]
    assert f"-c {shlex.quote(statement)}" in sent_command


@patch("keywords.base_keyword.get_logger")
def test_execute_sql_without_pod_name_falls_back_to_resolution(mock_get_logger):
    """Omitting the pod name resolves it via get_postgres_pod_name before executing."""
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="db-ns", kubeconfig_path="/tmp/fake-kubeconfig")

    with patch.object(keyword, "get_postgres_pod_name", return_value="postgresql-0") as mock_resolve:
        keyword.execute_sql_no_result(
            statement="DELETE FROM metrics;",
            database="cloudify_db",
            db_user="cloudify",
            container="postgresql",
        )

    mock_resolve.assert_called_once_with(KubectlPostgresqlKeywords.DEFAULT_POD_PREFIX)
    sent_command = ssh_connection.send.call_args[0][0]
    assert "postgresql-0" in sent_command


@patch("keywords.k8s.postgresql.kubectl_postgresql_keywords.KubectlExecInPodsKeywords")
@patch("keywords.base_keyword.get_logger")
def test_statement_with_shell_metacharacters_stays_single_quoted(mock_get_logger, mock_exec_cls):
    """A statement containing ';' is fully single-quoted in psql_cmd, preventing shell breakout.

    This pins the shell-escaping contract: if the shlex.quote is ever dropped or the
    psql_cmd f-string reworked, the statement separator would leak out unquoted and
    this test fails - flagging the reintroduced injection path immediately.
    """
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="db-ns", kubeconfig_path="/tmp/fake-kubeconfig")

    statement = "SELECT 1; SELECT 2"
    keyword.execute_sql_no_result(
        statement=statement,
        database="cloudify_db",
        db_user="cloudify",
        container="postgresql",
        pod_name="postgresql-0",
    )

    _, psql_cmd, options = mock_exec_cls.return_value.run_pod_exec_cmd.call_args[0]
    assert f"-c {shlex.quote(statement)}" in psql_cmd
    assert "-c 'SELECT 1; SELECT 2'" in psql_cmd
    assert "; SELECT 2" not in psql_cmd.replace(shlex.quote(statement), "")
    assert options == "-n db-ns -c postgresql"


@patch("keywords.k8s.postgresql.kubectl_postgresql_keywords.KubectlExecInPodsKeywords")
@patch("keywords.base_keyword.get_logger")
def test_non_statement_arguments_stay_quoted(mock_get_logger, mock_exec_cls):
    """Container and namespace carrying shell metacharacters stay quoted in the command.

    Extends the escaping contract beyond the statement to the other interpolated,
    shell-quoted arguments: if the shlex.quote is dropped from the container or
    namespace, a metacharacter in either would leak into the composed command and
    this test fails - flagging the reintroduced breakout path.
    """
    ssh_connection = build_mock_ssh_connection()
    keyword = KubectlPostgresqlKeywords(ssh_connection, namespace="ns; touch /tmp/x", kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.execute_sql_no_result(
        statement="SELECT 1",
        database="cloudify_db",
        db_user="cloudify",
        container="pg; rm -rf /",
        pod_name="postgresql-0",
    )

    _, psql_cmd, options = mock_exec_cls.return_value.run_pod_exec_cmd.call_args[0]
    assert f"-c {shlex.quote('pg; rm -rf /')}" in options
    assert f"-n {shlex.quote('ns; touch /tmp/x')}" in options
    assert "; rm -rf /" not in options.replace(shlex.quote("pg; rm -rf /"), "")
    assert "; touch /tmp/x" not in options.replace(shlex.quote("ns; touch /tmp/x"), "")
