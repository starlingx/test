from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class InterfacesTable(tables.TableRegion):
    name = "interfaces"
    CREATE_INTERFACE_FORM_FIELDS = ("subnet_id", "ip_address")

    @tables.bind_table_action('create')
    def create_interface(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.CREATE_INTERFACE_FORM_FIELDS
        )

    @tables.bind_table_action('delete')
    def delete_interface(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_interface_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)


class RouterInterfacesPage(basepage.BasePage):

    INTERFACES_TABLE_STATUS_COLUMN = 'Status'
    INTERFACES_TABLE_NAME_COLUMN = 'Name'
    DEFAULT_SUBNET = 'external-net0'

    def _get_row_with_interface_name(self, name):
        return self.interfaces_table.get_row(
            self.INTERFACES_TABLE_NAME_COLUMN, name)

    @property
    def interfaces_table(self):
        return InterfacesTable(self.driver)

    @property
    def interfaces_names(self):
        return list(map(lambda row: row.cells[self.
                   INTERFACES_TABLE_NAME_COLUMN].text,
                   self.interfaces_table.rows))

    def create_interface(self):
        interface_form = self.interfaces_table.create_interface()
        interface_form.subnet_id.text = self.DEFAULT_SUBNET
        # interface_form.ip_address.text = self.DEFAULT_IPv4_ADDRESS
        interface_form.submit()

    def delete_interface(self, interface_name):
        row = self._get_row_with_interface_name(interface_name)
        row.mark()
        confirm_delete_interface_form = self.interfaces_table.\
            delete_interface()
        confirm_delete_interface_form.submit()

    def delete_interface_by_row_action(self, interface_name):
        row = self._get_row_with_interface_name(interface_name)
        confirm_delete_interface = self.interfaces_table.\
            delete_interface_by_row_action(row)
        confirm_delete_interface.submit()

    def is_interface_present(self, interface_name):
        return bool(self._get_row_with_interface_name(interface_name))

    def is_interface_status(self, interface_name, status):
        row = self._get_row_with_interface_name(interface_name)
        return row.cells[self.INTERFACES_TABLE_STATUS_COLUMN].text == status
