from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class ProviderNetworksTable(tables.TableRegion):
    name = "provider_networks"

    CREATE_PROVIDER_NETWORK_FORM_FIELDS = ("name", "description", "type", "mtu", "vlan_transparent")
    EDIT_PROVIDER_NETWORK_FORM_FIELDS = ("name", "type", "description", "mtu", "vlan_transparent")
    CREATE_SEGMENTATION_RANGE_FORM_FIELDS = ("name", "description", "shared", "tenant_id",
                                             "minimum", "maximum", "mode", "group", "id_port_0",
                                             "id_port_1", "id_port_2", "ttl")

    @tables.bind_table_action('create')
    def create_provider_network(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, self.CREATE_PROVIDER_NETWORK_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_provider_network(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('update')
    def edit_provider_network(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, self.EDIT_PROVIDER_NETWORK_FORM_FIELDS)

    @tables.bind_row_action('addrange')
    def create_segmentation_range(self, create_button, row):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, self.CREATE_SEGMENTATION_RANGE_FORM_FIELDS)


class ProviderNetworksPage(basepage.BasePage):
    PARTIAL_URL = 'admin/providernets'

    PROVIDER_NETWORKS_TABLE_NAME_COLUMN = "Network Name"

    def _get_row_with_provier_network_name(self, name):
        return self.provider_networks_table.get_row(
            self.PROVIDER_NETWORKS_TABLE_NAME_COLUMN, name)

    @property
    def provider_networks_table(self):
        return ProviderNetworksTable(self.driver)

    def create_provider_network(self, name, description=None, type=None,
                                mtu=None, is_vlan_transparent=None):

        create_provier_network_form = self.provider_networks_table.create_network()
        create_provier_network_form.name.text = name
        if description is not None:
            create_provier_network_form.description.text = description
        if type is not None:
            create_provier_network_form.type.text = type
        if mtu is not None:
            create_provier_network_form.mtu.value = mtu
        if is_vlan_transparent:
            create_provier_network_form.vlan_transparent.mark()
        create_provier_network_form.submit()

    def edit_provider_network(self, description=None, mtu=None, is_vlan_transparent=None):
        edit_provider_network_form = self.provider_networks_table.edit_provider_network()
        if description is not None:
            edit_provider_network_form.description.text = description
        if mtu is not None:
            edit_provider_network_form.mtu.value = mtu
        if is_vlan_transparent is True:
            edit_provider_network_form.vlan_transparent.mark()
        if is_vlan_transparent is False:
            edit_provider_network_form.vlan_transparent.unmark()
        edit_provider_network_form.submit()

    def create_segmentation_range(self, name=None, description=None,
                                  is_shared=None, project=None,
                                  minimum=None, maximum=None, mode=None,
                                  multicase_group_address=None,
                                  port_0=None, port_1=None,
                                  port_2=None, ttl=None):
        create_segmentation_range_form = self.provider_networks_table.create_segmentation_range()
        if name is not None:
            create_segmentation_range_form.name.text = name
        if description is not None:
            create_segmentation_range_form.description.text = name
        if is_shared:
            create_segmentation_range_form.shared.mark()
        if project is not None:
            create_segmentation_range_form.tenant_id.text = project
        if minimum is not None:
            create_segmentation_range_form.minimum.value = minimum
        if maximum is not None:
            create_segmentation_range_form.maximum.value = maximum
        if mode is not None:
            create_segmentation_range_form.mode.text = mode
        if multicase_group_address is not None:
            create_segmentation_range_form.group.value = multicase_group_address
        if port_0:
            create_segmentation_range_form.id_port_0.mark()
        if port_1:
            create_segmentation_range_form.id_port_0.mark()
        if port_2:
            create_segmentation_range_form.id_port_0.mark()
        if ttl is not None:
            create_segmentation_range_form.ttl.value = ttl
        create_segmentation_range_form.submit()

    def delete_provider_network(self, name):
        row = self._get_row_with_provier_network_name(name)
        row.mark()
        confirm_form = self.provider_networks_table.delete_provider_network()
        confirm_form.submit()

    def is_provider_network_present(self, name):
        return bool(self._get_row_with_provier_network_name(name))

    def get_provider_network_info(self, name, header):
        row = self._get_row_with_provier_network_name(name)
        return row.cells[header].text
