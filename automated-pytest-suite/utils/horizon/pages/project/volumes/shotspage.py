from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from utils.horizon.pages.project.compute import instancespage
from time import sleep


class VolumesnapshotsTable(tables.TableRegion):
    name = 'volume_snapshots'

    EDIT_SNAPSHOT_FORM_FIELDS = ("name", "description")

    CREATE_VOLUME_FORM_FIELDS = ("name", "description", "snapshot_source", "size")

    @tables.bind_table_action('delete')
    def delete_volume_snapshot(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_volume_snapshot_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('edit')
    def edit_snapshot(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.EDIT_SNAPSHOT_FORM_FIELDS)

    @tables.bind_row_action('create_from_snapshot')
    def create_volume(self, create_volume_button, row):
        create_volume_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.CREATE_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('launch_snapshot_ng')
    def launch_as_instance(self, launch_button, row):
        launch_button.click()
        self.wait_till_spinner_disappears()
        return instancespage.LaunchInstanceForm(self.driver)


class VolumesnapshotsPage(basepage.BasePage):
    PARTIAL_URL = 'project/snapshots'
    SNAPSHOT_TABLE_NAME_COLUMN = 'Name'
    SNAPSHOT_TABLE_STATUS_COLUMN = 'Status'

    @property
    def volumes_napshots_table(self):
        return VolumesnapshotsTable(self.driver)

    def _get_row_with_volume_snapshot_name(self, name):
        return self.volumes_napshots_table.get_row(
            self.SNAPSHOT_TABLE_NAME_COLUMN,
            name)

    def is_snapshot_present(self, name):
        return bool(self._get_row_with_volume_snapshot_name(name))

    def get_snapshot_info(self, name, header):
        row = self._get_row_with_volume_snapshot_name(name)
        return row.cells[header].text

    def delete_volume_snapshot_by_row(self, name):
        row = self._get_row_with_volume_snapshot_name(name)
        confirm_form = self.volumes_napshots_table.delete_volume_snapshot_by_row(row)
        confirm_form.submit()

    def delete_volume_snapshots(self, names):
        for name in names:
            row = self._get_row_with_volume_snapshot_name(name)
            row.mark()
        confirm_form = self.volumes_napshots_table.delete_volume_snapshots()
        confirm_form.submit()

    def is_volume_snapshot_deleted(self, name):
        return self.volumes_napshots_table.is_row_deleted(
            lambda: self._get_row_with_volume_snapshot_name(name))

    def is_volume_snapshot_available(self, name):
        def cell_getter():
            row = self._get_row_with_volume_snapshot_name(name)
            return row and row.cells[self.SNAPSHOT_TABLE_STATUS_COLUMN]

        return bool(self.volumes_napshots_table.wait_cell_status(cell_getter,
                                                                 'Available'))

    def edit_snapshot(self, name, new_name=None, description=None):
        row = self._get_row_with_volume_snapshot_name(name)
        snapshot_edit_form = self.volumes_napshots_table.edit_snapshot(row)
        if new_name:
            snapshot_edit_form.name.text = new_name
        if description:
            snapshot_edit_form.description.text = description
        snapshot_edit_form.submit()

    def create_volume_from_snapshot(self, snapshot_name, volume_name=None,
                                    description=None, volume_size=None):
        row = self._get_row_with_volume_snapshot_name(snapshot_name)
        volume_form = self.volumes_napshots_table.create_volume(row)
        if volume_name:
            volume_form.name.text = volume_name
        if description:
            volume_form.description.text = description
        if volume_size is not None:
            volume_form.size.value = volume_size
        volume_form.submit()

    def launch_as_instance(self, name, instance_name, availability_zone=None, count=None,
                           boot_source_type=None, create_new_volume=None,
                           delete_volume_on_instance_delete=None, volume_size=None,
                           source_name=None, flavor_name=None, network_names=None):
        row = self._get_row_with_volume_snapshot_name(name)
        instance_form = self.volumes_napshots_table.launch_as_instance(row)
        instance_form.fields['name'].text = instance_name
        if availability_zone is not None:
            instance_form.fields['availability-zone'].text = availability_zone
        if count is not None:
            instance_form.fields['instance-count'].value = count
        instance_form.switch_to(1)
        if boot_source_type is not None:
            instance_form.fields['boot-source-type'].text = boot_source_type
        sleep(1)
        instance_form._init_tab_fields(1)
        if create_new_volume is True:
            instance_form.fields['Create New Volume'].click_yes()
            if delete_volume_on_instance_delete is True:
                instance_form.fields['Delete Volume on Instance Delete'].click_yes()
            if delete_volume_on_instance_delete is False:
                instance_form.fields['Delete Volume on Instance Delete'].click_no()
        if create_new_volume is False:
            instance_form.fields['Create New Volume'].click_no()
        if volume_size is not None:
            instance_form.fields['volume-size'].value = volume_size
        instance_form.addelement('Name', source_name)
        instance_form.switch_to(2)
        instance_form.addelement('Name', flavor_name)
        instance_form.switch_to(3)
        instance_form.addelements('Network', network_names)
        instance_form.submit()
