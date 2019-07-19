from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class ServerGroupsTable(tables.TableRegion):

    name = "server_groups"

    CREATE_SERVER_GROUP_FORM_FIELDS = ("tenantP", "name", "policy", "is_best_effort", "group_size")

    @tables.bind_table_action('create')
    def create_group(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.CREATE_SERVER_GROUP_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_group(self, delete_button):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)


class ServerGroupsPage(basepage.BasePage):

    PARTIAL_URL = 'admin/server_groups'

    SERVER_GROUPS_TABLE_NAME_COLUMN = 'Group Name'

    @property
    def server_groups_table(self):
        return ServerGroupsTable(self.driver)

    def create_group(self, name, project=None, policy=None, is_best_effort=False, group_size=None):
        create_form = self.server_groups_table.create_group()
        create_form.name.text = name
        if project is not None:
            create_form.tenantP.text = project
        create_form.tenantP.text = project
        if policy is not None:
            create_form.policy.text = policy
        if is_best_effort:
            create_form.is_best_effort.mark()
        if group_size is not None:
            create_form.group_size.text = group_size
        create_form.submit()

    def _get_row_with_server_group_name(self, name):
        return self.server_groups_table.get_row(self.SERVER_GROUPS_TABLE_NAME_COLUMN, name)

    def delete_group(self, name):
        row = self._get_row_with_server_group_name(name)
        row.mark()
        confirm_delete_form = self.server_groups_table.delete_group()
        confirm_delete_form.submit()

    def is_server_group_present(self, name):
        return bool(self._get_row_with_server_group_name(name))

    def get_server_group_info(self, server_group_name, header):
        row = self._get_row_with_server_group_name(server_group_name)
        return row.cells[header].text
