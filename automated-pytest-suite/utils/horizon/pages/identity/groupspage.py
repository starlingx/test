from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class GroupsTable(tables.TableRegion):

    name = "groups"

    MODIFY_GROUP_FORM_FIELDS = ("name", "description")

    @tables.bind_table_action('create')
    def create_group(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.MODIFY_GROUP_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_group(self, delete_button):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_group_by_row(self, delete_button, row):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('edit')
    def edit_group(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.MODIFY_GROUP_FORM_FIELDS)


class GroupsPage(basepage.BasePage):

    PARTIAL_URL = 'identity/groups'

    GROUPS_TABLE_NAME_COLUMN = 'Name'

    @property
    def groups_table(self):
        return GroupsTable(self.driver)

    def _get_row_with_group_name(self, name, strict=True):
        return self.groups_table.get_row(self.GROUPS_TABLE_NAME_COLUMN, name, exact_match=strict)

    def create_group(self, name, description=None):
        create_form = self.groups_table.create_group()
        create_form.name.text = name
        if description is not None:
            create_form.description.text = description
        create_form.submit()

    def delete_group(self, name, strict=True):
        row = self._get_row_with_group_name(name, strict=strict)
        row.mark()
        confirm_delete_form = self.groups_table.delete_group()
        confirm_delete_form.submit()

    def delete_group_by_row(self, name):
        row = self._get_row_with_group_name(name)
        confirm_delete_form = self.groups_table.delete_group_by_row(row)
        confirm_delete_form.submit()

    def edit_group(self, name, new_name=None, new_description=None):
        row = self._get_row_with_group_name(name)
        edit_form = self.groups_table.edit_group(row)
        if new_name is not None:
            edit_form.name.text = new_name
        if new_description is not None:
            edit_form.description.text = new_description
        edit_form.submit()

    def is_group_present(self, name):
        return bool(self._get_row_with_group_name(name))

    def get_group_info(self, group_name, header):
        row = self._get_row_with_group_name(group_name)
        return row.cells[header].text
