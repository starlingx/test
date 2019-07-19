from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import menus
from utils.horizon.regions import tables
from time import sleep


class FlavorsTable(tables.TableRegion):
    name = "flavors"

    CREATE_FLAVOR_FORM_FIELDS = (("name", "flavor_id", "vcpus", "memory_mb",
                                  "disk_gb", "eph_gb",
                                  "swap_mb",
                                  "rxtx_factor"),
                                 {"members": menus.MembershipMenuRegion})

    EDIT_FLAVOR_FORM_FIELDS = (("name", "vcpus", "memory_mb",
                                "disk_gb", "eph_gb", "swap_mb",
                                "rxtx_factor"),
                               {"members": menus.MembershipMenuRegion})
    UPDATE_METADATA_FORM_FIELD = "customItem"

    @tables.bind_table_action('create')
    def create_flavor(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver,
            field_mappings=self.CREATE_FLAVOR_FORM_FIELDS
        )

    @tables.bind_row_action('update')
    def edit_flavor(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver,
            field_mappings=self.EDIT_FLAVOR_FORM_FIELDS
        )

    @tables.bind_row_action('update_metadata')
    def update_metadata(self, metadata_button, row):
        metadata_button.click()
        return forms.MetadataFormRegion(self.driver)

    @tables.bind_row_action('projects')
    def modify_access(self, modify_button, row):
        modify_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver,
            field_mappings=self.EDIT_FLAVOR_FORM_FIELDS,
            default_tab=1
        )

    @tables.bind_row_action('delete')
    def delete_flavor_by_row(self, delete_button, row):
        delete_button.click()
        sleep(0.5)
        return forms.BaseFormRegion(self.driver)

    @tables.bind_table_action('delete')
    def delete_flavor(self, delete_button):
        delete_button.click()
        sleep(0.5)
        return forms.BaseFormRegion(self.driver)


class FlavorsPage(basepage.BasePage):
    PARTIAL_URL = 'admin/flavors'

    FLAVOR_INFORMATION_TAB_INDEX = 0
    FLAVOR_ACCESS_TAB_INDEX = 1
    FLAVORS_TABLE_NAME_COLUMN = 'Flavor Name'

    @property
    def flavors_table(self):
        return FlavorsTable(self.driver)

    def _get_row_by_flavor_name(self, name):
        return self.flavors_table.get_row(self.FLAVORS_TABLE_NAME_COLUMN, name)

    def create_flavor(self, name, flavor_id=None, vcpus=1, ram=1024,
                      root_disk=20, ephemeral_disk=None,
                      swap_disk=None, rxtx_factor=None,
                      allocate_projects=None):
        create_flavor_form = self.flavors_table.create_flavor()
        create_flavor_form.name.text = name
        if flavor_id is not None:
            create_flavor_form.flavor_id.text = flavor_id
        if vcpus is not None:
            create_flavor_form.vcpus.value = vcpus
        if ram is not None:
            create_flavor_form.memory_mb.value = ram
        if root_disk is not None:
            create_flavor_form.disk_gb.value = root_disk
        if ephemeral_disk is not None:
            create_flavor_form.eph_gb.value = ephemeral_disk
        if swap_disk is not None:
            create_flavor_form.swap_mb.value = swap_disk
        if rxtx_factor is not None:
            create_flavor_form.rxtx_factor = rxtx_factor
        create_flavor_form.switch_to(self.FLAVOR_ACCESS_TAB_INDEX)
        if allocate_projects is not None:
            for project in allocate_projects:
                create_flavor_form.members.allocate_member(project)
        create_flavor_form.submit()

    def is_flavor_present(self, name):
        return bool(self._get_row_by_flavor_name(name))

    def get_flavor_info(self, name, header):
        row = self._get_row_by_flavor_name(name)
        return row.cells[header].text

    def edit_flavor(self, name, newname=None, flavor_id=None, vcpus=None, ram=None,
                    root_disk=None, ephemeral_disk=None,
                    swap_disk=None, rxtx_factor=None,
                    allocate_projects=None, deallocate_projects=None):
        row = self._get_row_by_flavor_name(name)
        edit_flavor_form = self.flavors_table.edit_flavor(row)
        if newname is not None:
            edit_flavor_form.name.text = newname
        if flavor_id is not None:
            edit_flavor_form.flavor_id.text = flavor_id
        if vcpus is not None:
            edit_flavor_form.vcpus.value = vcpus
        if ram is not None:
            edit_flavor_form.memory_mb.value = ram
        if root_disk is not None:
            edit_flavor_form.disk_gb.value = root_disk
        if ephemeral_disk is not None:
            edit_flavor_form.eph_gb.value = ephemeral_disk
        if swap_disk is not None:
            edit_flavor_form.swap_mb.value = swap_disk
        if rxtx_factor is not None:
            edit_flavor_form.rxtx_factor = rxtx_factor
        edit_flavor_form.switch_to(self.FLAVOR_ACCESS_TAB_INDEX)
        if allocate_projects is not None:
            for project in allocate_projects:
                edit_flavor_form.members.allocate_member(project)
        if deallocate_projects is not None:
            for project in deallocate_projects:
                edit_flavor_form.members.deallocate_member(project)
        edit_flavor_form.submit()

    def modify_access(self, name, allocate_projects=None, deallocate_projects=None):
        row = self._get_row_by_flavor_name(name)
        edit_flavor_form = self.flavors_table.modify_access(row)
        if allocate_projects is not None:
            for project in allocate_projects:
                edit_flavor_form.members.allocate_member(project)
        if deallocate_projects is not None:
            for project in deallocate_projects:
                edit_flavor_form.members.deallocate_member(project)
        edit_flavor_form.submit()

    def add_custom_metadata(self, name, metadata):
        row = self._get_row_by_flavor_name(name)
        update_metadata_form = self.flavors_table.update_metadata(row)
        for field_name, value in metadata.items():
            update_metadata_form.add_custom_field(field_name, value)
        update_metadata_form.submit()

    def delete_flavor_by_row(self, name):
        row = self._get_row_by_flavor_name(name)
        confirm_delete_form = self.flavors_table.delete_flavor_by_row(row)
        confirm_delete_form.submit()

    def delete_flavor(self, name):
        row = self._get_row_by_flavor_name(name)
        row.mark()
        confirm_delete_form = self.flavors_table.delete_flavor()
        confirm_delete_form.submit()
