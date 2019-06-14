from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class UsersTable(tables.TableRegion):
    name = 'users'

    CREATE_USER_FORM_FIELDS = ("name", "description", "email", "password",
                               "confirm_password", "project", "role_id", "enabled")

    EDIT_USER_FORM_FIELDS = ("name", "description", "email", "project")

    CHANGE_PASSWORD_FORM_FIELDS = ("password", "confirm_password", "name")

    @tables.bind_table_action('create')
    def create_user(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.CREATE_USER_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_user(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_user_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('edit')
    def edit_user(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.EDIT_USER_FORM_FIELDS)

    @tables.bind_row_action('change_password')
    def change_password(self, change_password_button, row):
        change_password_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.CHANGE_PASSWORD_FORM_FIELDS)

    @tables.bind_row_action('toggle')
    def disable_user(self, disable_button, row):
        disable_button.click()

    @tables.bind_row_action('toggle')
    def enable_user(self, enable_button, row):
        enable_button.click()


class UsersPage(basepage.BasePage):
    PARTIAL_URL = 'identity/users'

    USERS_TABLE_NAME_COLUMN = 'User Name'

    def _get_row_with_user_name(self, name):
        return self.users_table.get_row(self.USERS_TABLE_NAME_COLUMN, name)

    @property
    def users_table(self):
        return UsersTable(self.driver)

    def create_user(self, name, password,
                    project, role, email=None):
        create_user_form = self.users_table.create_user()
        create_user_form.name.text = name
        if email is not None:
            create_user_form.email.text = email
        create_user_form.password.text = password
        create_user_form.confirm_password.text = password
        create_user_form.src_elem.click()   # Workaround for firefox insecure warning msg
        create_user_form.project.text = project
        create_user_form.role_id.text = role
        create_user_form.submit()

    def delete_user(self, name):
        row = self._get_row_with_user_name(name)
        row.mark()
        confirm_delete_users_form = self.users_table.delete_user()
        confirm_delete_users_form.submit()

    def delete_user_by_row(self, name):
        row = self._get_row_with_user_name(name)
        confirm_delete_users_form = self.users_table.delete_user_by_row(row)
        confirm_delete_users_form.submit()

    def disable_user(self, name):
        row = self._get_row_with_user_name(name)
        self.users_table.disable_user(row)

    def enable_user(self, name):
        row = self._get_row_with_user_name(name)
        self.users_table.enable_user(row)

    def is_user_present(self, name):
        return bool(self._get_row_with_user_name(name))

    def get_user_info(self, user_name, header):
        row = self._get_row_with_user_name(user_name)
        return row.cells[header].text
