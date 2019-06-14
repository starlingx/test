from time import sleep

from selenium.webdriver.common.by import By

from utils.horizon.pages import basepage
from utils.horizon.pages.project.compute import instancespage
from utils.horizon.regions import forms, tables, messages
from utils import exceptions
from utils.tis_log import LOG

from consts.timeout import VolumeTimeout


class VolumesTable(tables.TableRegion):
    name = 'volumes'

    CREATE_VOLUME_FORM_FIELDS = (
        "name", "description", "volume_source_type", "image_source", "volume_source",
        "type", "size", "availability_zone")

    EDIT_VOLUME_FORM_FIELDS = ("name", "description", 'bootable')

    CREATE_VOLUME_SNAPSHOT_FORM_FIELDS = ("name", "description")

    EXTEND_VOLUME_FORM_FIELDS = ("new_size",)

    UPLOAD_VOLUME_FORM_FIELDS = ("image_name", "disk_format")

    CHANGE_VOLUME_TYPE_FORM_FIELDS = ("name", "volume_type", "migration_policy")

    @tables.bind_table_action('create')
    def create_volume(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver, field_mappings=self.CREATE_VOLUME_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_volume(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_volume_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('edit')
    def edit_volume(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.EDIT_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('retype')
    def change_volume_type(self, change_button, row):
        change_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.CHANGE_VOLUME_TYPE_FORM_FIELDS)

    @tables.bind_row_action('snapshots')
    def create_snapshot(self, create_snapshot_button, row):
        create_snapshot_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.CREATE_VOLUME_SNAPSHOT_FORM_FIELDS)

    @tables.bind_row_action('extend')
    def extend_volume(self, extend_button, row):
        extend_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.EXTEND_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('launch_volume_ng')
    def launch_as_instance(self, launch_volume_button, row):
        launch_volume_button.click()
        self.wait_till_spinner_disappears()
        return instancespage.LaunchInstanceForm(self.driver)

    @tables.bind_row_action('upload_to_image')
    def upload_to_image(self, upload_button, row):
        upload_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.UPLOAD_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('attachments')
    def manage_attachments(self, manage_attachments, row):
        manage_attachments.click()
        self.wait_till_spinner_disappears()
        return VolumeAttachForm(self.driver)


class VolumesPage(basepage.BasePage):
    PARTIAL_URL = 'project/volumes'
    VOLUMES_TABLE_NAME_COLUMN = 'Name'
    VOLUMES_TABLE_STATUS_COLUMN = 'Status'

    def _get_row_with_volume_name(self, name):
        return self.volumes_table.get_row(
            self.VOLUMES_TABLE_NAME_COLUMN, name)

    def _get_rows_with_volumes_names(self, names):
        return [self.volumes_table.get_row(self.VOLUMES_TABLE_NAME_COLUMN, n)
                for n in names]

    @property
    def volumes_table(self):
        return VolumesTable(self.driver)

    def create_volume(self, volume_name, description=None,
                      volume_source_type=None, source_name=None,
                      type=None, volume_size=None, availability_zone=None,
                      fail_ok=False):
        volume_form = self.volumes_table.create_volume()
        volume_form.name.text = volume_name
        if description is not None:
            volume_form.description.text = description
        if volume_source_type is not None:
            volume_form.volume_source_type.text = volume_source_type
            if volume_source_type == 'Image':
                volume_form.image_source.text = source_name
                if type is not None:
                    volume_form.type.text = type
            if volume_source_type == 'Volume':
                volume_form.volume_source.text = source_name
        if volume_size is not None:
            volume_form.size.value = volume_size
        if availability_zone is not None:
            volume_form.availability_zone.text = availability_zone
        volume_form.submit()
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to create volume {}".format(volume_name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "creating volume {}".format(volume_name))
        succ_msg = "Volume {} is successfully created.".format(volume_name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def delete_volume(self, name, fail_ok=False):
        row = self._get_row_with_volume_name(name)
        row.mark()
        confirm_delete_volumes_form = self.volumes_table.delete_volume()
        confirm_delete_volumes_form.submit()
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to delete volume {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No success message found after "
                                              "deleting volume {}".format(name))
        succ_msg = "Volume {} is successfully deleted.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def delete_volume_by_row(self, name):
        row = self._get_row_with_volume_name(name)
        confirm_delete_volumes_form = self.volumes_table.delete_volume_by_row(row)
        confirm_delete_volumes_form.submit()

    def delete_volumes(self, volumes_names):
        for volume_name in volumes_names:
            self._get_row_with_volume_name(volume_name).mark()
        confirm_delete_volumes_form = self.volumes_table.delete_volume()
        confirm_delete_volumes_form.submit()

    def edit_volume(self, name, new_name=None, description=None, bootable=None,
                    fail_ok=False):
        row = self._get_row_with_volume_name(name)
        volume_edit_form = self.volumes_table.edit_volume(row)
        if new_name is not None:
            volume_edit_form.name.text = new_name
        if description is not None:
            volume_edit_form.description.text = description
        if bootable is True:
            volume_edit_form.bootable.mark()
        if bootable is False:
            volume_edit_form.bootable.unmark()
        volume_edit_form.submit()
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to edit volume {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "editing volume {}".format(name))
        succ_msg = "Volume {} is successfully edited.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def is_volume_present(self, name):
        return bool(self._get_row_with_volume_name(name))

    def is_volume_status(self, name, status, timeout=VolumeTimeout.STATUS_CHANGE):
        def cell_getter():
            row = self._get_row_with_volume_name(name)
            return row and row.cells[self.VOLUMES_TABLE_STATUS_COLUMN]
        return bool(self.volumes_table.wait_cell_status(cell_getter, status, timeout=timeout))

    def is_volume_deleted(self, name):
        return self.volumes_table.is_row_deleted(
            lambda: self._get_row_with_volume_name(name))

    def are_volumes_deleted(self, volumes_names):
        return self.volumes_table.are_rows_deleted(
            lambda: self._get_rows_with_volumes_names(volumes_names))

    def create_volume_snapshot(self, volume_name, snapshot_name, description=None):
        from utils.horizon.pages.project.volumes.shotspage import VolumesnapshotsPage
        row = self._get_row_with_volume_name(volume_name)
        snapshot_form = self.volumes_table.create_snapshot(row)
        snapshot_form.name.text = snapshot_name
        if description is not None:
            snapshot_form.description.text = description
        snapshot_form.submit()
        return VolumesnapshotsPage(self.driver, port=self.port)

    def extend_volume(self, name, new_size, fail_ok=False):
        row = self._get_row_with_volume_name(name)
        extend_volume_form = self.volumes_table.extend_volume(row)
        extend_volume_form.new_size.value = new_size
        extend_volume_form.submit()
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to extend volume {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "extending volume {}".format(name))
        succ_msg = "Volume {} is successfully extended.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def upload_to_image(self, volume_name, image_name, disk_format=None):
        row = self._get_row_with_volume_name(volume_name)
        upload_volume_form = self.volumes_table.upload_to_image(row)
        upload_volume_form.image_name.text = image_name
        if disk_format is not None:
            upload_volume_form.disk_format.value = disk_format
        upload_volume_form.submit()

    def change_volume_type(self, volume_name, type=None, migration_policy=None):
        row = self._get_row_with_volume_name(volume_name)
        change_volume_type_form = self.volumes_table.change_volume_type(row)
        if type is not None:
            change_volume_type_form.type.text = type
        if migration_policy is not None:
            change_volume_type_form.migration_policy.text = migration_policy
        change_volume_type_form.submit()

    def launch_as_instance(self, name, instance_name, availability_zone=None, count=None,
                           boot_source_type=None, create_new_volume=None,
                           delete_volume_on_instance_delete=None, volume_size=None,
                           source_name=None, flavor_name=None, network_names=None):
        row = self._get_row_with_volume_name(name)
        instance_form = self.volumes_table.launch_as_instance(row)
        instance_form.fields['name'].text = instance_name
        if availability_zone is not None:
            instance_form.fields['availability-zone'].text = availability_zone
        if count is not None:
            instance_form.fields['instance-count'].value = count
        instance_form.switch_to(1)
        if boot_source_type is not None:
            instance_form.fields['boot-source-type'].text = boot_source_type
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
        if source_name is not None:
            instance_form.addelement('Name', source_name)
        instance_form.switch_to(2)
        instance_form.addelement('Name', flavor_name)
        instance_form.switch_to(3)
        instance_form.addelements('Network', network_names)
        instance_form.submit()

    def attach_volume_to_instance(self, volume, instance, fail_ok=False):
        row = self._get_row_with_volume_name(volume)
        attach_form = self.volumes_table.manage_attachments(row)
        attach_form.attach_instance(instance)
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to attach volume {}".format(volume)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "attaching volume {}".format(volume))
        succ_msg = "Volume {} is successfully attached.".format(volume)
        LOG.info(succ_msg)
        return 0, succ_msg

    def detach_volume_from_instance(self, volume, instance, fail_ok=False):
        row = self._get_row_with_volume_name(volume)
        attachment_form = self.volumes_table.manage_attachments(row)
        detach_form = attachment_form.detach(volume, instance)
        detach_form.submit()
        if not self.find_message_and_dismiss(messages.SUCCESS):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to detach volume {}".format(volume)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "detaching volume {}".format(volume))
        succ_msg = "Volume {} is successfully detached.".format(volume)
        LOG.info(succ_msg)
        return 0, succ_msg

    def get_volume_info(self, volume_name, header):
        row = self._get_row_with_volume_name(volume_name)
        return row.cells[header].text


class VolumeAttachForm(forms.BaseFormRegion):
    _attach_to_instance_selector = (By.CSS_SELECTOR, 'div > .themable-select')
    _attachments_table_selector = (By.CSS_SELECTOR, 'table[id="attachments"]')
    _detach_template = 'tr[data-display="Volume {0} on instance {1}"] button'

    @property
    def attachments_table(self):
        return self._get_element(*self._attachments_table_selector)

    @property
    def instance_selector(self):
        src_elem = self._get_element(*self._attach_to_instance_selector)
        return forms.ThemableSelectFormFieldRegion(
            self.driver, src_elem=src_elem,
            strict_options_match=False)

    def detach(self, volume, instance):
        detach_button = self.attachments_table.find_element(
            By.CSS_SELECTOR, self._detach_template.format(volume, instance))
        detach_button.click()
        sleep(2)
        return forms.BaseFormRegion(self.driver)

    def attach_instance(self, instance_name):
        self.instance_selector.text = instance_name
        self.submit()
