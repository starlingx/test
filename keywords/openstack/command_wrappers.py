def source_admin_openrc(cmd: str):
    return f"source /var/opt/openstack/admin-openrc;/var/opt/openstack/clients-wrapper.sh {cmd}"

def source_sudo_admin_openrc(cmd: str):
    return f"bash -c '/var/opt/openstack/admin-openrc;/var/opt/openstack/clients-wrapper.sh {cmd}'"
