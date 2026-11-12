"""Unit tests for KubectlHostsOutput getters."""

from unittest.mock import patch

import pytest

from keywords.k8s.crd.object.kubectl_hosts_output import KubectlHostsOutput

HEADER = "NAME           ADMINISTRATIVE   OPERATIONAL   AVAILABILITY   PROFILE                INSYNC   SCOPE       RECONCILED\n"
HEADER_WITHOUT_RECONCILED = "NAME           ADMINISTRATIVE   OPERATIONAL   AVAILABILITY   PROFILE                INSYNC   SCOPE\n"


def build_output(*rows: str, header: str = HEADER) -> KubectlHostsOutput:
    """Build a KubectlHostsOutput from table rows, with logging disabled.

    The rows are passed as a list of lines, which is what the SSH connection returns.

    Args:
        *rows (str): Data rows of a 'kubectl get hosts' table.
        header (str): Header line of the table. Defaults to the full 'kubectl get hosts' header.

    Returns:
        KubectlHostsOutput: Parsed output.
    """
    with patch("keywords.k8s.crd.object.kubectl_hosts_output.get_logger"):
        return KubectlHostsOutput([header, *rows])


def test_get_hosts_returns_every_host():
    """get_hosts() returns one object per host, in table order."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "controller-1   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
    )

    hosts = output.get_hosts()

    assert [host.get_name() for host in hosts] == ["controller-0", "controller-1"]
    assert [host.get_reconcile() for host in hosts] == ["true", "true"]


def test_get_host_returns_the_named_host():
    """get_host() returns the host with the given name."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "controller-1   unlocked         enabled       available      controller-0-profile   false    bootstrap   false\n",
    )

    host = output.get_host("controller-1")

    assert host.get_name() == "controller-1"
    assert host.get_insync() == "false"
    assert host.get_reconcile() == "false"


def test_get_host_raises_when_the_host_is_missing():
    """get_host() raises ValueError when no host has the given name."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
    )

    with pytest.raises(ValueError, match="There is no host with the name compute-0."):
        output.get_host("compute-0")


def test_is_all_reconciled_true_when_every_host_is_reconciled():
    """is_all_reconciled() is True when every host reports RECONCILED true."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "compute-0      unlocked         enabled       available      compute-0-profile      true     bootstrap   true\n",
    )

    assert output.is_all_reconciled() is True


def test_is_all_reconciled_false_when_a_host_is_not_reconciled():
    """is_all_reconciled() is False as soon as one host reports RECONCILED false."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "controller-1   unlocked         enabled       available      controller-0-profile   false    bootstrap   false\n",
    )

    assert output.is_all_reconciled() is False


def test_is_all_insync_true_when_every_host_is_insync():
    """is_all_insync() is True when every host reports INSYNC true."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "compute-0      unlocked         enabled       available      compute-0-profile      true     bootstrap   true\n",
    )

    assert output.is_all_insync() is True


def test_is_all_insync_false_when_a_host_is_not_insync():
    """is_all_insync() is False as soon as one host reports INSYNC false, even if it is reconciled."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n",
        "controller-1   unlocked         enabled       available      controller-0-profile   false    bootstrap   true\n",
    )

    assert output.is_all_reconciled() is True
    assert output.is_all_insync() is False


def test_empty_output_has_no_hosts_and_is_all_reconciled():
    """With only the header, there are no hosts and the all-hosts checks are True, as in KubectlSystemsOutput.

    Callers that need at least one host must check get_hosts() themselves.
    """
    output = build_output()

    assert output.get_hosts() == []
    assert output.is_all_reconciled() is True
    assert output.is_all_insync() is True


def test_missing_reconciled_column_counts_as_not_reconciled():
    """Without a RECONCILED column, get_reconcile() is None and is_all_reconciled() is False."""
    output = build_output(
        "controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap\n",
        header=HEADER_WITHOUT_RECONCILED,
    )

    assert output.get_host("controller-0").get_reconcile() is None
    assert output.is_all_reconciled() is False
    assert output.is_all_insync() is True
