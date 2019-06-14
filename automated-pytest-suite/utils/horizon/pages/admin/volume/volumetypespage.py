from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class QosSpecsTable(tables.TableRegion):
    name = 'qos_specs'
    CREATE_QOS_SPEC_FORM_FIELDS = ("name", "consumer")
    EDIT_CONSUMER_FORM_FIELDS = ("consumer_choice", )

    @tables.bind_table_action('create')
    def create_qos_spec(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.CREATE_QOS_SPEC_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_qos_spec(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_qos_spec_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('edit_consumer')
    def edit_consumer(self, edit_consumer_button, row):
        edit_consumer_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.EDIT_CONSUMER_FORM_FIELDS)


class VolumeTypesTable(tables.TableRegion):
    name = 'volume_types'

    CREATE_VOLUME_TYPE_FORM_FIELDS = ("name", "vol_type_description", "is_public")
    CREATE_ECRYPTION_FORM_FIELDS = ("name", "provider", "control_location", "cipher", "key_size")
    MANAGE_QOS_SPEC_ASSOCIATION_FORM_FIELDS = ("qos_spec_choice",)

    @tables.bind_table_action('create')
    def create_volume_type(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.CREATE_VOLUME_TYPE_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_volume_type(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_volume_type_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('create_encryption')
    def create_encryption(self, create_button, row):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver, field_mappings=self.CREATE_QOS_SPEC_FORM_FIELDS)

    @tables.bind_row_action('associate')
    def manage_qos_spec_association(self, manage_button, row):
        manage_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver, field_mappings=self.MANAGE_QOS_SPEC_ASSOCIATION_FORM_FIELDS)


class VolumetypesPage(basepage.BasePage):
    PARTIAL_URL = 'admin/volume_types'
    QOS_SPECS_TABLE_NAME_COLUMN = 'Name'
    VOLUME_TYPES_TABLE_NAME_COLUMN = 'Name'

    @property
    def qos_specs_table(self):
        return QosSpecsTable(self.driver)

    @property
    def volume_types_table(self):
        return VolumeTypesTable(self.driver)

    def _get_row_with_qos_spec_name(self, name):
        return self.qos_specs_table.get_row(
            self.QOS_SPECS_TABLE_NAME_COLUMN, name)

    def _get_row_with_volume_type_name(self, name):
        return self.volume_types_table.get_row(
            self.VOLUME_TYPES_TABLE_NAME_COLUMN, name)

    def create_qos_spec(self, qos_spec_name, consumer=None):
        create_qos_spec_form = self.qos_specs_table.create_qos_spec()
        create_qos_spec_form.name.text = qos_spec_name
        if consumer is not None:
            create_qos_spec_form.consumer.text = consumer
        create_qos_spec_form.submit()

    def create_volume_type(self, volume_type_name, description=None):
        volume_type_form = self.volume_types_table.create_volume_type()
        volume_type_form.name.text = volume_type_name
        if description is not None:
            volume_type_form.description.text = description
        volume_type_form.submit()

    def delete_qos_spec(self, name):
        row = self._get_row_with_qos_spec_name(name)
        row.mark()
        confirm_delete_qos_spec_form = self.qos_specs_table.delete_qos_spec()
        confirm_delete_qos_spec_form.submit()

    def delete_qos_spec_by_row(self, name):
        row = self._get_row_with_qos_spec_name(name)
        confirm_delete_qos_spec_form = self.qos_specs_table.delete_qos_spec_by_row(row)
        confirm_delete_qos_spec_form.submit()

    def delete_volume_type(self, name):
        row = self._get_row_with_volume_type_name(name)
        row.mark()
        confirm_delete_volume_types_form = self.volume_types_table.delete_volume_type()
        confirm_delete_volume_types_form.submit()

    def delete_volume_type_by_row(self, name):
        row = self._get_row_with_volume_type_name(name)
        confirm_delete_volume_types_form = self.volume_types_table.delete_volume_type_by_row(row)
        confirm_delete_volume_types_form.submit()

    def edit_consumer(self, name, consumer_choice):
        row = self._get_row_with_qos_spec_name(name)
        edit_consumer_form = self.qos_specs_table.edit_consumer(row)
        edit_consumer_form.consumer_choice.value = consumer_choice
        edit_consumer_form.submit()

    def create_encryption(self, name, provider, control_location=None, cipher=None, key_size=None):
        row = self._get_row_with_volume_type_name(name)
        create_encrypted_form = self.volume_types_table.create_encryption(row)
        create_encrypted_form.provider.tesxt = provider
        if control_location is not None:
            create_encrypted_form.control_location.text = control_location
        if cipher is not None:
            create_encrypted_form.cipher.text = cipher
        if key_size is not None:
            create_encrypted_form.key_size = key_size
        create_encrypted_form.submit()

    def manage_qos_spec_association(self, name, associated_qos_spec):
        row = self._get_row_with_volume_type_name(name)
        associate_qos_spec_form = self.volume_types_table.manage_qos_spec_association(row)
        associate_qos_spec_form.qos_spec_choice.text = associated_qos_spec
        associate_qos_spec_form.submit()

    def is_qos_spec_present(self, name):
        return bool(self._get_row_with_qos_spec_name(name))

    def is_volume_type_present(self, name):
        return bool(self._get_row_with_volume_type_name(name))

    def get_volume_type_info(self, name, header):
        row = self._get_row_with_volume_type_name(name)
        return row.cells[header].text

    def get_qos_spec_info(self, name, header):
        row = self._get_row_with_qos_spec_name(name)
        return row.cells[header].text
