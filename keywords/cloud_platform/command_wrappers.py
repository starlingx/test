def source_openrc(cmd: str):
    return f"source /etc/platform/openrc;{cmd}"


def source_sudo_openrc(cmd: str):
    return f"bash -c 'source /etc/platform/openrc;{cmd}'"


def oidc_auth_wrap(cmd: str) -> str:
    """Wrap a dcmanager command for OIDC-authenticated execution.

    Injects --stx-auth-type=oidc after the 'dcmanager' binary name and
    prepends environment setup for OIDC sessions (KUBECONFIG, openrc
    without credentials, OS_USERNAME from whoami).

    The calling SSH session must already be authenticated via oidc-auth
    and have sourced local_starlingxrc oidc.

    Args:
        cmd (str): The dcmanager command (e.g. 'dcmanager subcloud list').

    Returns:
        str: Full command string ready for OIDC execution.
    """
    dcm_with_arg = cmd.replace("dcmanager ", "dcmanager --stx-auth-type=oidc ", 1)
    return f"export KUBECONFIG=$HOME/.kube/config && source /etc/platform/openrc --no_credentials && export OS_USERNAME=$(whoami) && {dcm_with_arg}"
