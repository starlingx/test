import re
import copy

from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms, tables
from utils.horizon.helper import HorizonDriver
from keywords import system_helper


class HostsTable(tables.TableRegion):
    _cli_horizon_fields_map = {
        'hostname': 'Host Name',
        'personality': 'Personality',
        'administrative': 'Admin State',
        'operational': 'Operational State',
        'availability': 'Availability State',
        'uptime': 'Uptime',
        'task': 'Status'
    }

    def get_cli_horizon_mapping(self):
        return self._cli_horizon_fields_map

    @tables.bind_row_action('update')
    def edit_host(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.EDIT_HOST_FORM_FIELDS)

    @tables.bind_row_action('lock')
    def lock_host(self, lock_button, row):
        lock_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('unlock')
    def unlock_host(self, unlock_button, row):
        unlock_button.click()

    @tables.bind_row_anchor_column('Host Name')
    def go_to_host_detail_page(self, row_link, row):
        row_link.click()

    @tables.bind_row_anchor_column('Host Name')
    def host_detail_overview_description(self):
        self.go_to_host_detail_page()
        return HostDetailOverviewDescription(self.driver)


class ControllerHostsTable(HostsTable):
    name = 'hostscontroller'
    EDIT_HOST_FORM_FIELDS = (
        ("personality", "subfunctions", "hostname", "location", "cpuProfile",
         "interfaceProfile", "diskProfile", "memoryProfile", "ttys_dcd"),
        ("boot_device", "rootfs_device", "install_output", "console"),
        ("bm_type", "bm_ip", "bm_username", "bm_password", "bm_confirm_password"))

    @tables.bind_row_action('swact')
    def swact_host(self, swact_button, row):
        swact_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_table_action('create')
    def add_host(self, add_button):
        add_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.ADD_HOST_FORM_FIELDS)


class StorageHostsTable(HostsTable):
    name = 'hostsstorage'

    def get_cli_horizon_mapping(self):
        map_ = copy.deepcopy(self._cli_horizon_fields_map)
        map_.pop('personality')
        return map_

    @tables.bind_table_action('install-async')
    def install_paches(self, install_button):
        install_button.click()


class ComputeHostsTable(HostsTable):
    name = 'hostsworker'

    EDIT_HOST_FORM_FIELDS = (
        ("personality", "location", "cpuProfile", "interfaceProfile", "ttys_dcd"),
        ("boot_device", "rootfs_device", "install_output", "console"),
        ("bm_type", "bm_ip", "bm_username", "bm_password", "bm_confirm_password"))

    @tables.bind_table_action('install-async')
    def install_paches(self, install_button):
        install_button.click()


class HostInventoryPage(basepage.BasePage):

    PARTIAL_URL = 'admin'

    HOSTS_TABLE_NAME_COLUMN = 'Host Name'
    HOSTS_TABLE_ADMIN_STATE_COLUMN = 'Admin State'
    HOSTS_TABLE_AVAILABILITY_STATE_COLUMN = 'Availability State'
    HOSTS_TAB_INDEX = 0
    DEVICE_USAGE_TAB_INDEX = 5

    def _get_row_with_host_name(self, name):
        return self.hosts_table(name).get_row(
            self.HOSTS_TABLE_NAME_COLUMN, name)

    def hosts_table(self, name):
        if 'controller' in name:
            return ControllerHostsTable(self.driver)
        elif 'storage' in name:
            return StorageHostsTable(self.driver)
        elif re.search('compute|worker', name):
            return ComputeHostsTable(self.driver)

    def edit_host(self, name):
        row = self._get_row_with_host_name(name)
        host_edit_form = self.hosts_table(name).edit_host(row)
        # ...
        host_edit_form.submit()

    def lock_host(self, name):
        row = self._get_row_with_host_name(name)
        confirm_form = self.hosts_table(name).lock_host(row)
        confirm_form.submit()

    def unlock_host(self, name):
        row = self._get_row_with_host_name(name)
        self.hosts_table(name).unlock_host(row)

    def is_host_present(self, name):
        return bool(self._get_row_with_host_name(name))

    def is_host_admin_state(self, name, state):
        def cell_getter():
            row = self._get_row_with_host_name(name)
            return row and row.cells[self.HOSTS_TABLE_ADMIN_STATE_COLUMN]

        return bool(self.hosts_table(name).wait_cell_status(cell_getter, state))

    def is_host_availability_state(self, name, state):
        def cell_getter():
            row = self._get_row_with_host_name(name)
            return row and row.cells[self.HOSTS_TABLE_AVAILABILITY_STATE_COLUMN]

        return bool(self.hosts_table(name).wait_cell_status(cell_getter, state))

    def get_host_info(self, host_name, header):
        row = self._get_row_with_host_name(host_name)
        return row.cells[header].text

    def go_to_hosts_tab(self):
        self.go_to_tab(self.HOSTS_TAB_INDEX)

    def go_to_host_detail_page(self, host_name):
        row = self._get_row_with_host_name(host_name)
        self.hosts_table(host_name).go_to_host_detail_page(row)
        return HostInventoryDetailPage(HorizonDriver.get_driver(), host_name)

    def go_to_device_usage_tab(self):
        if system_helper.is_aio_simplex():
            self.go_to_tab(1)
        else:
            self.go_to_tab(self.DEVICE_USAGE_TAB_INDEX)

    def horizon_vals(self, host_name):
        horizon_headers = self.hosts_table(host_name).\
            get_cli_horizon_mapping().values()
        horizon_vals = {}
        for horizon_header in horizon_headers:
            horizon_val = self.get_host_info(host_name, horizon_header)
            if horizon_val == '' or horizon_val == '-':
                horizon_val = 'None'
            horizon_vals[horizon_header] = horizon_val
        return horizon_vals


class HostDetailOverviewDescription(forms.ItemTextDescription):
    _separator_locator = (by.By.CSS_SELECTOR, 'dl.dl-horizontal-wide')
    OVERVIEW_INFO_HEADERS_MAP = {
        'hostname': 'Host Name',
        'personality': 'Personality',
        'uuid': 'Host UUID',
        'id': 'Host ID',
        'mgmt_mac': 'Management MAC',
        'mgmt_ip': 'Management IP',
        'serialid': 'Serial ID',
        'administrative': 'Administrative State',
        'operational': 'Operational State',
        'availability': 'Availability State',
        'boot_device': 'Boot Device',
        'rootfs_device': 'Rootfs Device',
        'install_output': 'Installation Output',
        'console': 'Console',
        'bm_ip': 'Board Management Controller IP Address',
        'bm_username': 'Board Management Controller User Name'
    }


class HostDetailProcessorDescription(forms.ItemTextDescription):
    name = 'inventory_details__cpufunctions'
    _separator_locator = (by.By.CSS_SELECTOR, 'div#cpufunctions')


class MemoryTable(tables.TableRegion):
    name = "memorys"
    MEMORY_TABLE_HEADERS_MAP = {
        'processor': 'Processor',
        'mem_total(MiB)': 'Memory',
        'mem_avail(MiB)': 'Memory',

    }
    CREATE_MEMORY_PROFILE_FORM_FIELDS = 'profilename'

    @tables.bind_table_action('createMemoryProfile')
    def create_memory_profile(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver, field_mappings=self.CREATE_MEMORY_PROFILE_FORM_FIELDS)


class StorageDisksTable(tables.TableRegion):
    name = "disks"
    HEADERS_MAP = {
        # 'Model' not found from cli table
        'uuid': 'UUID',
        'device_path': 'Disk info',
        'device_type': 'Type',
        'size_gib': 'Size (GiB)',
        'available_gib': 'Available Size (GiB)',
        'rpm': 'RPM',
        'serial_id': 'Serial ID'
    }


class StoragePartitionsTable(tables.TableRegion):
    name = "partitions"
    HEADERS_MAP = {
        'uuid': 'UUID',
        'device_path': 'Partition Device Path',
        'size_gib': 'Size (GiB)',
        'type_name': 'Partition Type',
        'status': 'Status'
    }
    CREATE_PARTITION_FORM_FIELDS = ("hostname", "disks", "size_gib", "type_guid")

    @tables.bind_table_action('createpartition')
    def create_new_partition(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver, field_mappings=self.CREATE_PARTITION_FORM_FIELDS)


class StorageLocalVolumeGroupTable(tables.TableRegion):
    name = "localvolumegroups"
    HEADERS_MAP = {
        'LVG Name': 'Name',
        'State': 'State',
        'Access': 'Access',
        'Total Size (GiB)': 'Size (GiB)',
        'Avail Size (GiB)': 'Avail Size (GiB)',
        'Current PVs': 'Current Physical Volumes',
        'Current LVs': 'Current Logical Volumes'
    }

    CREATE_STORAGE_PROFILE_FORM_FIELDS = "profilename"

    @tables.bind_table_action('creatediskprofile')
    def create_storage_profie(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver, field_mappings=self.CREATE_STORAGE_PROFILE_FORM_FIELDS)

    @tables.bind_table_action('addlocalvolumegroup')
    def add_lvg(self, add_button):
        add_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver)


class StoragePhysicalVolumeTable(tables.TableRegion):
    name = "physicalvolumes"
    HEADERS_MAP = {
        'lvm_pv_name': 'Name',
        'pv_state': 'State',
        'pv_type': 'Type',
        'disk_or_part_uuid': 'Disk or Partition UUID',
        'disk_or_part_device_path': 'Disk or Partition Device Path',
        'lvm_vg_name': 'LVM Volume Group Name'
    }

    ADD_PHYSICL_VOLUME_FORM_FIELDS = ("hostname", 'lvg', 'pv_type', 'disks')

    @tables.bind_table_action('addphysicakvolume')
    def add_physical_volume(self, add_button):
        add_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver, field_mappings=self.ADD_PHYSICL_VOLUME_FORM_FIELDS)


class PortsTable(tables.TableRegion):
    name = "ports"
    HEADERS_MAP = {
        # Accelerate not in the cli table
        'name': 'Name',
        'mac address': 'MAC Address',
        'pci address': 'PCI Address',
        'processor': 'Processor',
        'auto neg': 'Auto Negotiation',
        'boot i/f': 'Boot Interface',
        'device type': 'Device Type',
    }


class InterfaceTable(tables.TableRegion):
    name = "interfaces"

    CREATE_INTERFACE_PROFILE_FORM_FIELDS = "profilename"

    @tables.bind_table_action('createprofile')
    def create_inferface_profile(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver, field_mappings=self.CREATE_INTERFACE_PROFILE_FORM_FIELDS)


class LLDPTable(tables.TableRegion):
    name = "neighbours"
    HEADERS_MAP = {
        'local_port': 'Name',
        'port_identifier': 'Neighbor',
        'port_description': 'Port Description',
        # 'ttl': 'Time To Live (Rx)', This one is dynamic, horizon exists delay
        'system_name': 'System Name',
        'dot3_max_frame': 'Max Frame Size'
    }


class HostInventoryDetailPage(basepage.BasePage):
    OVERVIEW_TAB_INDEX = 0
    PROCESSOR_TAB_INDEX = 1
    MEMORY_TAB_INDEX = 2
    SOTRAGE_TAB_INDEX = 3
    PORTS_TAB_INDEX = 4
    INTEFACES_TAB_INDEX = 5
    LLDP_TAB_INDEX = 6
    SENSORS_TAB_INDEX = 7
    DEVICES_TAB_INDEX = 8
    MEMORYTABLE_PROCESSOR_COL = 'Processor'

    def __init__(self, driver, host_name):
        super(HostInventoryDetailPage, self).__init__(driver)
        self._page_title = 'Host Detail: {}'.format(host_name)

    def _get_memory_table_row_with_processor(self, processor):
        return self.memory_table.get_row(self.MEMORYTABLE_PROCESSOR_COL, processor)

    def get_memory_table_info(self, processor, header):
        row = self._get_memory_table_row_with_processor(processor)
        if row.cells[header].text == '':
            return None
        else:
            return row.cells[header].text

    def get_horizon_row_dict(self, table_, key_header_index):
        """
        In a table, each row as a dict, horizon headers as key, cells as value
        Args:
            table_ (table): table object
            key_header_index(int): The unique column header index of table
        Return:
            A row dict table, the unique column value as a key, usually are
            uuid or name
        Examples:
            {
            '53194b0f-543c-4b33-9b2e-276ab9c70671':
                {'uuid': 53194b0f-543c-4b33-9b2e-276ab9c70671, 'type': 'SSD'...}
            'ea89031c-8f60-41b0-ad14-c5fcf5df96eb':
                {'uuid': ea89031c-8f60-41b0-ad14-c5fcf5df96eb, 'type': 'SSD'...}
            }
        """
        rtn_dict = {}
        keys = table_.HEADERS_MAP.values()
        for row in table_.rows:
            row_dict = {}
            key_header = row.cells[table_.column_names[key_header_index]].text
            for key in keys:
                val = row.cells[key].text
                if val == '' or val == '-':
                    val = 'None'
                row_dict[key] = val
            rtn_dict[key_header] = row_dict
        return rtn_dict

    def get_storage_partitons_table_rows(self):
        return self.storage_partitions_table.rows

    def get_storage_lvg_table_rows(self):
        return self.storage_lvg_table.rows

    def get_storage_pv_table_rows(self):
        return self.storage_pv_table.rows

    def host_detail_overview(self, driver):
        return HostDetailOverviewDescription(driver)

    @property
    def inventory_details_processor_info(self):
        return HostDetailProcessorDescription(self.driver)

    @property
    def memory_table(self):
        return MemoryTable(self.driver)

    @property
    def storage_disks_table(self):
        return StorageDisksTable(self.driver)

    @property
    def storage_partitions_table(self):
        return StoragePartitionsTable(self.driver)

    @property
    def storage_lvg_table(self):
        return StorageLocalVolumeGroupTable(self.driver)

    @property
    def storage_pv_table(self):
        return StoragePhysicalVolumeTable(self.driver)

    def ports_table(self):
        return PortsTable(self.driver)

    def lldp_table(self):
        return LLDPTable(self.driver)

    def go_to_overview_tab(self):
        self.go_to_tab(self.OVERVIEW_TAB_INDEX)

    def go_to_processor_tab(self):
        self.go_to_tab(self.PROCESSOR_TAB_INDEX)

    def go_to_memory_tab(self):
        self.go_to_tab(self.MEMORY_TAB_INDEX)

    def go_to_storage_tab(self):
        self.go_to_tab(self.SOTRAGE_TAB_INDEX)

    def go_to_ports_tab(self):
        self.go_to_tab(self.PORTS_TAB_INDEX)

    def go_to_interfaces_tab(self):
        self.go_to_tab(self.SOTRAGE_TAB_INDEX)

    def go_to_lldp_tab(self):
        self.go_to_tab(self.LLDP_TAB_INDEX)

    def go_to_sensors_tab(self):
        self.go_to_tab(self.SENSORS_TAB_INDEX)

    def go_to_devices_tab(self):
        self.go_to_tab(self.DEVICES_TAB_INDEX)
