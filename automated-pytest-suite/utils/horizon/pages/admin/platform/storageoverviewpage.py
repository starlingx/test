from selenium.webdriver.common import by
from utils.horizon.pages import basepage
from utils.horizon.regions import tables, forms


class StorageSeviceDescription(forms.ItemTextDescription):
    _separator_locator = (by.By.CSS_SELECTOR, 'div#storageservice')

class MonitorsTable(tables.TableRegion):
    name = "monitors"


class OsdsTable(tables.TableRegion):
    name = "osds"


class UsageTable(tables.TableRegion):
    name = "usage"


class StorageOverviewPage(basepage.BasePage):
    PARTIAL_URL = 'admin/storage_overview'
    SERVICES_TAB_INDEX = 0
    SERVICES_MONITOR_HOST_COL = 'Host'
    SERVICES_OSD_NAME_COL = 'Name'
    USAGE_TAB_INDEX = 1
    USAGE_BACKEND_TYPE_COL = 'Backend type'
    USAGE_BACKEND_SERVICE_NAME_COLUMN = 'Service name'

    usage_headers_map = {
        'Backend type': 'backend type',
        'Backend name': 'backend name',
        'Service name': 'service',
        'Total Capacity (GiB)': 'total capacity (GiB)',
        'Free Capacity (GiB)': 'free capacity (GiB)'
    }

    @property
    def storage_service_info(self):
        return StorageSeviceDescription(self.driver)

    @property
    def monitors_table(self):
        return MonitorsTable(self.driver)

    @property
    def osds_table(self):
        return OsdsTable(self.driver)

    @property
    def usage_table(self):
        return UsageTable(self.driver)

    def _get_row_with_service_name(self, name):
        return self.usage_table.get_row(self.USAGE_BACKEND_SERVICE_NAME_COLUMN, name)

    def get_rows_from_usage_table(self):
        return self.usage_table.rows

    def _get_monitor_table_row_with_host(self, host_name):
        return self.monitors_table.get_row(self.SERVICES_MONITOR_HOST_COL, host_name)

    def _get_osd_table_row_with_osd_name(self, osd_name):
        return self.osds_table.get_row(self. SERVICES_OSD_NAME_COL, osd_name)

    def get_storage_overview_monitor_info(self, host_name, header):
        row = self._get_monitor_table_row_with_host(host_name)
        return row.cells[header].text

    def get_storage_overview_osd_info(self, name, header):
        row = self._get_osd_table_row_with_osd_name(name)
        return row.cells[header].text

    def get_storage_overview_usage_info(self, name, header):
        row = self._get_row_with_service_name(name)
        return row.cells[header].text

    def go_to_services_tab(self):
        self.go_to_tab(self.SERVICES_TAB_INDEX)

    def go_to_usage_tab(self):
        self.go_to_tab(self.USAGE_TAB_INDEX)

