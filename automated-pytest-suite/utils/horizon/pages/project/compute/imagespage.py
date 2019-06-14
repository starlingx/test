from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from utils.horizon.pages.project.compute import instancespage
from utils.horizon.pages.project.volumes.volumespage import VolumesPage


class ImagesForm(forms.FormRegion):
    _fields_locator = (by.By.CSS_SELECTOR, 'ng-include')
    _submit_locator = (by.By.CSS_SELECTOR, '*.btn.btn-primary.finish')


class ImagesClickVisibility(forms.YesOrNoFormFieldRegion):
    _buttons_locator = (by.By.CSS_SELECTOR, 'label')


class ImagesTable(tables.TableRegion):
    name = "OS::Glance::Image"
    _rows_locator = (by.By.CSS_SELECTOR, 'tbody > tr[class="ng-scope"]')
    _search_field_locator = (by.By.CSS_SELECTOR, 'div.search-bar input.search-input')
    _clear_btn_locator = (by.By.CSS_SELECTOR, 'div.search-bar a.magic-search-clear')

    CREATE_IMAGE_FORM_FIELDS = (
        "name", "description", "image_file", "kernel", "ramdisk",
        "format", "architecture", "min_disk", "min_ram",
        "is_public", "protected"
    )

    CREATE_VOLUME_FROM_IMAGE_FORM_FIELDS = (
        "name", "description", "image_source",
        "type", "volume-size", "availability-zone")

    EDIT_IMAGE_FORM_FIELDS = (
        "name", "description", "format", "min_disk",
        "min_ram", "public", "protected"
    )

    def filter(self, value):
        self._set_search_field(value)

    def clear(self):
        btn = self._get_element(*self._clear_btn_locator)
        btn.click()

    @tables.bind_table_action('btn-default', attribute_search='class')
    def create_image(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return ImagesForm(self.driver,
                          field_mappings=self.CREATE_IMAGE_FORM_FIELDS)

    @tables.bind_table_action('btn-danger', attribute_search='class')
    def delete_image(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('text-danger', attribute_search='class')
    def delete_image_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('create_volume_from_image', secondary_locator_index=1)
    def create_volume(self, create_volume, row):
        """
        Create volume must be referenced by index using the secondary_locator_index
        since the a tag does not have defining attributes. The create volume button
        is under the first li tag under ul.dropdown-menu for the specified row.
        The parameter is explained in the tables.bind_row_action docstring.
        """
        create_volume.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(
            self.driver,
            field_mappings=self.CREATE_VOLUME_FROM_IMAGE_FORM_FIELDS)

    @tables.bind_row_action('btn-default', attribute_search='class')
    def launch_instance(self, launch_button, row):
        launch_button.click()
        return instancespage.LaunchInstanceForm(self.driver)

    @tables.bind_row_action('update_metadata', secondary_locator_index=3)
    def update_metadata(self, metadata_button, row):
        """
        Metadata must be referenced by index using the secondary_locator_index
        since the a tag does not have defining attributes. The update metadata
        button is under the third li under ul.dropdown-menu for the specified row.
        The parameter is explained in the tables.bind_row_action docstring.
        """
        metadata_button.click()
        self.wait_till_spinner_disappears()
        return forms.MetadataFormRegion(self.driver)

    @tables.bind_row_action('edit', secondary_locator_index=2)
    def edit_image(self, edit_button, row):
        """
        Edit Image must be referenced by index using the secondary_locator_index
        since the a tag does not have defining attributes. The edit image button
        is under the second li under ul.dropdown-menu for the specified row.
        The parameter is explained in the tables.bind_row_action docstring.
        """
        edit_button.click()
        self.wait_till_spinner_disappears()
        return ImagesForm(self.driver,
                          field_mappings=self.EDIT_IMAGE_FORM_FIELDS)

    @tables.bind_row_anchor_column('Image Name')
    def go_to_image_description_page(self, row_link, row):
        row_link.click()
        return forms.ItemTextDescription(self.driver)

    def _table_locator(self, table_name):
        return by.By.CSS_SELECTOR, 'hz-resource-table[resource-type-name="%s"]' % table_name


class ImagesPage(basepage.BasePage):

    PARTIAL_URL = 'project/images'

    IMAGES_TABLE_NAME_COLUMN = 'Name'
    IMAGES_TABLE_STATUS_COLUMN = 'Status'

    def _get_row_with_image_name(self, name):
        return self.images_table.get_row(self.IMAGES_TABLE_NAME_COLUMN, name)

    @property
    def images_table(self):
        return ImagesTable(self.driver)

    def create_image(self, name, description=None, image_file=None,
                     image_format=None, architecture=None,
                     minimum_disk=None, minimum_ram=None,
                     is_public=None, is_protected=None):
        create_image_form = self.images_table.create_image()
        create_image_form.name.text = name
        if description is not None:
            create_image_form.description.text = description
        create_image_form.image_file.choose(image_file)
        if image_format is not None:
            create_image_form.disk_format.value = image_format
        if architecture is not None:
            create_image_form.architecture.text = architecture
        if minimum_disk is not None:
            create_image_form.minimum_disk.value = minimum_disk
        if minimum_ram is not None:
            create_image_form.minimum_disk.value = minimum_ram
        if is_public is True:
            create_image_form.is_public.mark()
        if is_public is False:
            create_image_form.is_public.unmark()
        if is_protected is True:
            create_image_form.protected.mark()
        if is_protected is False:
            create_image_form.protected.unmark()
        create_image_form.submit()

    def delete_image(self, name):
        row = self._get_row_with_image_name(name)
        row.mark()
        confirm_delete_images_form = self.images_table.delete_image()
        confirm_delete_images_form.submit()

    def delete_image_by_row(self, name):
        row = self._get_row_with_image_name(name)
        delete_image_form = self.images_table.delete_image_by_row(row)
        delete_image_form.submit()

    def add_custom_metadata(self, name, metadata):
        row = self._get_row_with_image_name(name)
        update_metadata_form = self.images_table.update_metadata(row)
        for field_name, value in metadata.items():
            update_metadata_form.add_custom_field(field_name, value)
        update_metadata_form.submit()

    def check_image_details(self, name, dict_with_details):
        row = self._get_row_with_image_name(name)
        matches = []
        description_page = self.images_table.go_to_image_description_page(row)
        content = description_page.get_content()

        for name, value in content.items():
            if name in dict_with_details:
                if dict_with_details[name] in value:
                    matches.append(True)
        return matches

    def edit_image(self, name, new_name=None, description=None,
                   disk_format=None, minimum_disk=None,
                   minimum_ram=None, public=None, protected=None):
        row = self._get_row_with_image_name(name)
        confirm_edit_images_form = self.images_table.edit_image(row)
        if new_name is not None:
            confirm_edit_images_form.name.text = new_name
        if description is not None:
            confirm_edit_images_form.description.text = description
        if disk_format is not None:
            confirm_edit_images_form.disk_format = disk_format
        if minimum_disk is not None:
            confirm_edit_images_form.minimum_disk.value = minimum_disk
        if minimum_ram is not None:
            confirm_edit_images_form.minimum_ram.value = minimum_ram
        if public is True:
            confirm_edit_images_form.public.mark()
        if public is False:
            confirm_edit_images_form.public.unmark()
        if protected is True:
            confirm_edit_images_form.protected.mark()
        if protected is False:
            confirm_edit_images_form.protected.unmark()
        confirm_edit_images_form.submit()

    def is_image_present(self, name):
        return bool(self._get_row_with_image_name(name))

    def is_image_active(self, name):
        def cell_getter():
            row = self._get_row_with_image_name(name)
            return row and row.cells[self.IMAGES_TABLE_STATUS_COLUMN]
        return bool(self.images_table.wait_cell_status(cell_getter, 'Active'))

    def wait_until_image_active(self, name):
        self._wait_until(lambda x: self.is_image_active(name))

    def get_image_info(self, image_name, header):
        row = self._get_row_with_image_name(image_name)
        return row.cells[header].text

    def create_volume_from_image(self, image_name, volume_name=None,
                                 description=None, type=None,
                                 volume_size=None, availability_zone=None):
        row = self._get_row_with_image_name(image_name)
        create_volume_form = self.images_table.create_volume(row)
        if volume_name is not None:
            create_volume_form.name.text = volume_name
        if description is not None:
            create_volume_form.description.text = description
        if type is not None:
            create_volume_form.type.text = type
        if volume_size is not None:
            create_volume_form.size.value = volume_size
        if availability_zone is not None:
            create_volume_form.availability_zone.text = availability_zone
        create_volume_form.submit()
        return VolumesPage(self.driver, self.port)

    def launch_instance_from_image(self, name, instance_name, availability_zone=None, count=None,
                                   boot_source_type=None, create_new_volume=None,
                                   delete_volume_on_instance_delete=None, volume_size=None,
                                   source_name=None, flavor_name=None, network_names=None):
        row = self._get_row_with_image_name(name)
        instance_form = self.images_table.launch_instance(row)
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
