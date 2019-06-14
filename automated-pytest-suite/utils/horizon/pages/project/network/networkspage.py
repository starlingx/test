from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class NetworksTable(tables.TableRegion):
    name = "networks"
    CREATE_NETWORK_FORM_FIELDS = (("net_name", "admin_state",
                                   "with_subnet", "az_hints"),
                                  ("subnet_name", "cidr", "ip_version",
                                   "gateway_ip", "no_gateway"),
                                  ("enable_dhcp", "allocation_pools",
                                   "dns_nameservers", "host_routes"))

    EDIT_NETWORK_FORM_FIELDS = ("name", "admin_state", "shared")
    CREATE_SUBNET_FORM_FIELDS = (("subnet_name", "cidr", "ip_version",
                                   "gateway_ip", "no_gateway"),
                                 ("enable_dhcp", "allocation_pools",
                                  "dns_nameservers", "host_routes"))

    @tables.bind_table_action('create')
    def create_network(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver, field_mappings=self.CREATE_NETWORK_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_network(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action("delete")
    def delete_network_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action("update")
    def edit_network(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_NETWORK_FORM_FIELDS)

    @tables.bind_row_action("subnet")
    def create_subnet(self, create_button, row):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.CREATE_SUBNET_FORM_FIELDS)


class NetworksPage(basepage.BasePage):
    PARTIAL_URL = 'project/networks'
    NETWORKS_TABLE_NAME_COLUMN = 'Name'
    NETWORKS_TABLE_STATUS_COLUMN = 'Status'

    def _get_row_with_network_name(self, name):
        return self.networks_table.get_row(
            self.NETWORKS_TABLE_NAME_COLUMN, name)

    @property
    def networks_table(self):
        return NetworksTable(self.driver)

    def create_network(self, network_name, enable_admin_state=None, qos_policy=None,
                       vlan_transparent=None, create_subnet=None,
                       subnet_name=None, network_address=None,
                       ip_version=None, gateway_ip=None, disable_gateway=None,
                       enable_dhcp=None, allocation_pools=None,
                       dns_name_servers=None, host_routes=None):
        create_network_form = self.networks_table.create_network()
        create_network_form.net_name.text = network_name
        if enable_admin_state is True:
            create_network_form.admin_state.mark()
        if enable_admin_state is False:
            create_network_form.admin_state.unmark()
        if qos_policy is not None:
            create_network_form.qos.text = qos_policy
        if vlan_transparent is True:
            create_network_form.vlan_transparent.mark()
        if vlan_transparent is False:
            create_network_form.vlan_transparent.unmark()
        if create_subnet is True:
            create_network_form.with_subnet.mark()
        if create_subnet is False:
            create_network_form.with_subnet.unmark()
        create_network_form.switch_to(1)
        if subnet_name is not None:
            create_network_form.subnet_name.text = subnet_name
        if network_address is not None:
            create_network_form.cidr.text = network_address
        if ip_version is not None:
            create_network_form.ip_version.value = ip_version
        if gateway_ip is not None:
            create_network_form.gateway_ip.text = gateway_ip
        if disable_gateway is True:
            create_network_form.disable_gateway.mark()
        if disable_gateway is False:
            create_network_form.disable_gateway.unmark()
        create_network_form.switch_to(2)
        if enable_dhcp is True:
            create_network_form.enable_dhcp.mark()
        if enable_dhcp is False:
            create_network_form.enable_dhcp.unmark()
        if allocation_pools is not None:
            create_network_form.allocation_pools.text = allocation_pools
        if dns_name_servers is not None:
            create_network_form.dns_nameservers.text = dns_name_servers
        if host_routes is not None:
            create_network_form.host_routes.text = host_routes
        create_network_form.submit()

    def edit_network(self, name, new_name=None, enable_admin_state=None, is_shared=None):
        row = self._get_row_with_network_name(name)
        edit_network_form = self.networks_table.edit_network(row)
        if new_name is not None:
            edit_network_form.name.text = new_name
        if enable_admin_state is True:
            edit_network_form.admin_state.mark()
        if enable_admin_state is False:
            edit_network_form.admin_state.unmark()
        if is_shared is True:
            edit_network_form.shared.mark()
        if is_shared is False:
            edit_network_form.shared.unmark()
        edit_network_form.submit()

    def create_subnet(self, name, subnet_name, network_address,
                      ip_version=None, gateway_ip=None, disable_gateway=None,
                      enable_dhcp=None, allocation_pools=None,
                      dns_name_servers=None, host_routes=None):
        row = self._get_row_with_network_name(name)
        create_subnet_form = self.networks_table.create_subnet(row)
        create_subnet_form.subnet_name.text = subnet_name
        create_subnet_form.cidr.text = network_address
        if ip_version is not None:
            create_subnet_form.ip_version.text = ip_version
        if gateway_ip is not None:
            create_subnet_form.gateway_ip.text = gateway_ip
        if disable_gateway is True:
            create_subnet_form.no_gateway.mark()
        if disable_gateway is False:
            create_subnet_form.no_gateway.unmark()
        create_subnet_form.switch_to(1)
        if enable_dhcp is True:
            create_subnet_form.enable_dhcp.mark()
        if enable_dhcp is False:
            create_subnet_form.enable_dhcp.unmark()
        if allocation_pools is not None:
            create_subnet_form.allocation_pools.text = allocation_pools
        if dns_name_servers is not None:
            create_subnet_form.dns_nameservers.text = dns_name_servers
        if host_routes is not None:
            create_subnet_form.host_routes.text = host_routes
        create_subnet_form.submit()

    def delete_network(self, name):
        row = self._get_row_with_network_name(name)
        row.mark()
        confirm_delete_networks_form = self.networks_table.delete_network()
        confirm_delete_networks_form.submit()

    def delete_network_by_row(self, name):
        row = self._get_row_with_network_name(name)
        confirm_delete_networks_form = self.networks_table.delete_network_by_row(row)
        confirm_delete_networks_form.submit()

    def is_network_present(self, name):
        return bool(self._get_row_with_network_name(name))

    def get_network_info(self, network_name, header):
        row = self._get_row_with_network_name(network_name)
        return row.cells[header].text

    def go_to_networks_tab(self):
        self.go_to_tab(0)

    def go_to_qos_policies_tab(self):
        self.go_to_tab(1)
