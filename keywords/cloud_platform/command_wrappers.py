def source_openrc(cmd: str):
    return f"source /etc/platform/openrc;{cmd}"


def source_sudo_openrc(cmd: str):
    return f"bash -c 'source /etc/platform/openrc;{cmd}'"
