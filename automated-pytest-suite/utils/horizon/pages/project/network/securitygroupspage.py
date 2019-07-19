from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from utils.horizon.pages.project.network.managerulespage import ManageRulesPage


class SecurityGroupsTable(tables.TableRegion):
    name = "security_groups"
    CREATE_SECURITYGROUP_FORM_FIELDS = ("name", "description")

    @tables.bind_table_action('create')
    def create_group(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver, field_mappings=self.CREATE_SECURITYGROUP_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_group(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver, None)

    @tables.bind_row_action('manage_rules')
    def manage_rules(self, manage_rules_button, row):
        manage_rules_button.click()
        return ManageRulesPage(self.driver)


class SecuritygroupsPage(basepage.BasePage):
    PARTIAL_URL = 'project/security_groups'

    SECURITYGROUPS_TABLE_NAME_COLUMN = 'Name'

    def _get_row_with_securitygroup_name(self, name):
        return self.securitygroups_table.get_row(
            self.SECURITYGROUPS_TABLE_NAME_COLUMN, name)

    @property
    def securitygroups_table(self):
        return SecurityGroupsTable(self.driver)

    def create_securitygroup(self, name, description=None):
        create_securitygroups_form = self.securitygroups_table.create_group()
        create_securitygroups_form.name.text = name
        if description is not None:
            create_securitygroups_form.description.text = description
        create_securitygroups_form.submit()

    def delete_securitygroup(self, name):
        row = self._get_row_with_securitygroup_name(name)
        row.mark()
        modal_confirmation_form = self.securitygroups_table.delete_group()
        modal_confirmation_form.submit()

    def is_securitygroup_present(self, name):
        return bool(self._get_row_with_securitygroup_name(name))

    def get_security_group_info(self, name, header):
        row = self._get_row_with_securitygroup_name(name)
        return row.cells[header].text

    def go_to_manage_rules(self, name):
        row = self._get_row_with_securitygroup_name(name)
        return self.securitygroups_table.manage_rules(row)
