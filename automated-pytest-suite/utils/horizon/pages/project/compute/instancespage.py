import time
import re

from selenium.common import exceptions
from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from utils.horizon.regions import menus
from consts.stx import Networks


class LaunchInstanceForm(forms.TabbedFormRegion):
    _submit_locator = (by.By.XPATH, '//button[@class="btn btn-primary finish"]')
    _fields_locator = (by.By.XPATH, "//div[starts-with(@class,'step ng-scope')]")
    _tables_locator = (by.By.XPATH, ".//table")

    field_mappings = (
        ("name", "availability-zone", "count"),
        ("boot-source-type", "volume-size", "Create New Volume",
         "Delete Volume on Instance Delete"),
        (),
        (),
        (),
        (),
        (),
        ("customization-script", "load-script", "disk-partition", "config-drive"),
        (),
        (),
        (),
        ("min-inst-count",)
    )

    def _init_tab_fields(self, tab_index):
        self.src_elem = self.driver
        fieldsets = self._get_elements(*self._fields_locator)
        self.fields_src_elem = fieldsets[tab_index]
        self.src_elem = fieldsets[tab_index]

    @property
    def tabs(self):
        return menus.InstancesTabbedMenuRegion(self.driver,
                                               src_elem=self.src_elem)

    @property
    def contained_tables(self):
        return self._get_elements(*self._tables_locator)

    class AllocatedTable(tables.TableRegion):
        _rows_locator = (by.By.CSS_SELECTOR, 'tbody>tr[class="ng-scope"]')

    class AvailableTable(tables.TableRegion):
        _rows_locator = (by.By.CSS_SELECTOR, 'tbody>tr[class="ng-scope"]')

    # server group's available table contains a inner table so use a different column names locator
    class ServerGrpAvailableTable(tables.TableRegion):
        _rows_locator = (by.By.CSS_SELECTOR, 'tbody>tr[class="ng-scope"]')
        _columns_names_locator = (by.By.CSS_SELECTOR, 'thead > tr:nth-child(2) > th')

    @property
    def allocated_table(self):
        return self.AllocatedTable(self.driver, self.contained_tables[0])

    @property
    def available_table(self):
        return self.AvailableTable(self.driver, self.contained_tables[1])

    @property
    def server_grp_available_table(self):
        return self.ServerGrpAvailableTable(self.driver, self.contained_tables[1])

    def __init__(self, driver):
        super(LaunchInstanceForm, self).__init__(
            driver, field_mappings=())

    def addservergrp(self, column_name, name):
        self.server_grp_available_table.get_row(column_name, name).add()

    def addelement(self, column_name, name):
        self.available_table.get_row(column_name, name).add()

    def addelements(self, column_name, names):
        for name in names:
            self.available_table.get_row(column_name, name).add()


class InstancesTable(tables.TableRegion):
    name = "instances"

    CREATE_SNAPSHOT_FORM_FIELDS = ("name",)
    ASSOCIATE_FLOATING_IP_FORM_FIELDS = ("ip_id", "instance_id")
    EDIT_INSTANCE_FORM_FIELDS = (("name",),
                                 {"groups": menus.MembershipMenuRegion})
    ATTACH_VOLUME_FORM_FIELDS = ("volume",)
    RESIZE_INSTANCE_FORM_FIELDS = (("old_flavor_name", "flavor"),
                                   ("disk_config", "min_count", "server_group"))
    REBUILD_INSTANCE_FORM_FIELDS = ("image", "disk_config")

    @tables.bind_table_action('launch-ng')
    def launch_instance(self, launch_button):
        launch_button.click()
        self.wait_till_spinner_disappears()
        return LaunchInstanceForm(self.driver)

    @tables.bind_table_action('delete')
    def delete_instance(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_instance_by_row(self, delete_instance, row):
        delete_instance.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('snapshot')
    def create_snapshot(self, create_button, row):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.CREATE_SNAPSHOT_FORM_FIELDS)

    @tables.bind_row_action('associate')
    def associate_floating_ip(self, associate_button, row):
        associate_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.ASSOCIATE_FLOATING_IP_FORM_FIELDS)

    @tables.bind_row_action('edit')
    def edit_instance(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver, field_mappings=self.EDIT_INSTANCE_FORM_FIELDS)

    @tables.bind_row_action('attach_volume')
    def attach_volume(self, attach_button, row):
        attach_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.ATTACH_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('detach_volume')
    def detach_volume(self, detach_button, row):
        detach_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.ATTACH_VOLUME_FORM_FIELDS)

    @tables.bind_row_action('edit')
    def edit_security_groups(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.EDIT_INSTANCE_FORM_FIELDS,
                                      default_tab=1)

    @tables.bind_row_action('pause')
    def pause_instance(self, pause_button, row):
        pause_button.click()

    @tables.bind_row_action('resume')
    def resume_instance(self, resume_button, row):
        resume_button.click()

    @tables.bind_row_action('suspend')
    def suspend_instance(self, suspend_button, row):
        suspend_button.click()

    @tables.bind_row_action('resize')
    def resize_instance(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.RESIZE_INSTANCE_FORM_FIELDS)

    @tables.bind_row_action('lock')
    def lock_instance(self, lock_button, row):
        lock_button.click()

    @tables.bind_row_action('unlock')
    def lock_instance(self, unlock_button, row):
        unlock_button.click()

    @tables.bind_row_action('soft_reboot')
    def soft_reboot_instance(self, soft_reboot_button, row):
        soft_reboot_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('reboot')
    def hard_reboot_instance(self, hard_reboot_button, row):
        hard_reboot_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('stop')
    def shut_off_instance(self, shut_off_button, row):
        shut_off_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('start')
    def start_instance(self, start_button, row):
        start_button.click()

    @tables.bind_row_action('rebuild')
    def rebuild_instance(self, rebuild_button, row):
        rebuild_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.REBUILD_INSTANCE_FORM_FIELDS)


class InstancesPage(basepage.BasePage):
    PARTIAL_URL = 'project/instances'

    INSTANCES_TABLE_NAME_COLUMN = 'Instance Name'
    INSTANCES_TABLE_STATUS_COLUMN = 'Status'
    INSTANCES_TABLE_IP_COLUMN = 'IP Address'

    def _get_row_with_instance_name(self, name):
        return self.instances_table.get_row(self.INSTANCES_TABLE_NAME_COLUMN, name)

    @property
    def instances_table(self):
        return InstancesTable(self.driver)

    def is_instance_present(self, name):
        return bool(self._get_row_with_instance_name(name))

    def create_instance(self, instance_name, availability_zone=None, count=None,
                        boot_source_type='Image', create_new_volume=False,
                        delete_volume_on_instance_delete=None, volume_size=None,
                        source_name=None, flavor_name=None, network_names=None,
                        server_group_name=None):
        instance_form = self.instances_table.launch_instance()
        instance_form.fields['name'].text = instance_name
        if availability_zone is not None:
            instance_form.fields['availability-zone'].text = availability_zone
        if count is not None:
            instance_form.fields['instance-count'].value = count
        instance_form.switch_to(1)
        if boot_source_type is not None:
            instance_form.fields['boot-source-type'].text = boot_source_type
        time.sleep(1)
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

        if isinstance(network_names, str):
            network_names = [network_names]
        instance_form.addelements('Network', network_names)
        if server_group_name is not None:
            instance_form.switch_to(8)
            instance_form.addservergrp('Name', server_group_name)
        instance_form.submit()

    def delete_instance_by_row(self, name):
        row = self._get_row_with_instance_name(name)
        confirm_delete_instances_form = self.instances_table.delete_instance_by_row(row)
        confirm_delete_instances_form.submit()

    def delete_instance(self, name):
        row = self._get_row_with_instance_name(name)
        row.mark()
        confirm_form = self.instances_table.delete_instance()
        confirm_form.submit()

    def is_instance_deleted(self, name):
        return self.instances_table.is_row_deleted(
            lambda: self._get_row_with_instance_name(name))

    def is_instance_active(self, name):
        def cell_getter():
            row = self._get_row_with_instance_name(name)
            try:
                return row and row.cells[self.INSTANCES_TABLE_STATUS_COLUMN]
            except exceptions.StaleElementReferenceException:
                raise

        status = self.instances_table.wait_cell_status(cell_getter,
                                                       ('Active', 'Error'))
        return status == 'Active'

    def get_fixed_ipv4(self, name):
        row = self._get_row_with_instance_name(name)
        ips = row.cells[self.INSTANCES_TABLE_IP_COLUMN].text
        for ip in ips.split():
            if re.match(Networks.IPV4_IP, ip):
                return ip

    def get_instance_info(self, name, header):
        row = self._get_row_with_instance_name(name)
        return row.cells[header].text

    def create_snapshot(self, name, snapshot_name):
        row = self._get_row_with_instance_name(name)
        create_snapshot_form = self.instances_table.create_snapshot(row)
        create_snapshot_form.name.text = snapshot_name
        create_snapshot_form.submit()

    def associate_floating_ip(self, name, ip_address=None, port=None):
        row = self._get_row_with_instance_name(name)
        associate_floating_ip_form = self.instances_table.associate_floating_ip(row)
        if ip_address is not None:
            associate_floating_ip_form.ip_id.text = ip_address
        if port is not None:
            associate_floating_ip_form.instance_id.text = port
        associate_floating_ip_form.submit()

    def edit_instance(self, name, newname=None):
        row = self._get_row_with_instance_name(name)
        edit_instance_form = self.instances_table.edit_instance(row)
        if newname is not None:
            edit_instance_form.name.text = newname
        edit_instance_form.submit()

    def attach_volume(self, name, volume_id):
        row = self._get_row_with_instance_name(name)
        attach_volume_form = self.instances_table.attach_volume(row)
        attach_volume_form.volume.text = volume_id
        attach_volume_form.submit()

    def detach_volume(self, name, volume_id):
        row = self._get_row_with_instance_name(name)
        attach_volume_form = self.instances_table.detach_volume(row)
        attach_volume_form.volume.text = volume_id
        attach_volume_form.submit()

    def edit_security_groups(self, name, security_groups_to_allocate=None,
                             securtiy_groups_to_deallocate=None):
        row = self._get_row_with_instance_name(name)
        edit_form = self.instances_table.edit_security_groups(row)
        if security_groups_to_allocate is not None:
            for security_group in security_groups_to_allocate:
                edit_form.groups.allocate_member(security_group)
        if securtiy_groups_to_deallocate is not None:
            for security_group in securtiy_groups_to_deallocate:
                edit_form.groups.deallocate_member(security_group)
        edit_form.submit()

    def pause_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.pause_instance(row)

    def resume_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.resume_instance(row)

    def suspend_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.suspend_instance(row)

    def resize_instance(self, name, new_flavor, disk_partition=None,
                        min_instance_count=None, server_group=None):
        row = self._get_row_with_instance_name(name)
        resize_instance_form = self.instances_table.resize_instance(row)
        resize_instance_form.flavor.text = new_flavor
        resize_instance_form.switch_to(1)
        if disk_partition is not None:
            resize_instance_form.disk_config.text = disk_partition
        if min_instance_count is not None:
            resize_instance_form.min_count.text = min_instance_count
        if server_group is not None:
            resize_instance_form.server_group.text = server_group
        resize_instance_form.submit()

    def lock_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.lock_instance(row)

    def unlock_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.unlock_instance(row)

    def soft_reboot_instance(self, name):
        row = self._get_row_with_instance_name(name)
        confirm_form = self.instances_table.soft_reboot_instance(row)
        confirm_form.submit()

    def hard_reboot_instance(self, name):
        row = self._get_row_with_instance_name(name)
        confirm_form = self.instances_table.hard_reboot_instance(row)
        confirm_form.submit()

    def shut_off_instance(self, name):
        row = self._get_row_with_instance_name(name)
        confirm_form = self.instances_table.shut_off_instance(row)
        confirm_form.submit()

    def start_instance(self, name):
        row = self._get_row_with_instance_name(name)
        self.instances_table.start_instance(row)

    def rebuild_instance(self, name, image_name, disk_partition=None):
        row = self._get_row_with_instance_name(name)
        rebuild_instance_form = self.instances_table.rebuild_instance(row)
        rebuild_instance_form.image.text = image_name
        if disk_partition is not None:
            rebuild_instance_form.disk_config.text = disk_partition
        rebuild_instance_form.submit()
