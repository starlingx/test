from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class HypervisorTable(tables.TableRegion):
    name = "hypervisors"
    pass


class ComputeHostTable(tables.TableRegion):
    name = "compute_host"

    DISABLE_SERVICE_FORM_FIELDS = ('host', 'reason')

    @tables.bind_row_action('disable')
    def disable_service(self, disable_button, row):
        disable_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.DISABLE_SERVICE_FORM_FIELDS)

    @tables.bind_row_action('enable')
    def enable_service(self, enable_button, row):
        enable_button.click()
        self.wait_till_spinner_disappears()


class HypervisorsPage(basepage.BasePage):

    PARTIAL_URL = 'admin/hypervisors'

    HYPERVISOR_TAB_INDEX = 0
    COMPUTEHOST_TAB_INDEX = 1
    HYPERVISOR_TABLE_NAME_COLUMN = 'Hostname'
    COMPUTE_HOST_TABLE_NAME_COLUMN = 'Host'

    @property
    def hypervisor_table(self):
        return HypervisorTable(self.driver)

    @property
    def compute_host_table(self):
        return ComputeHostTable(self.driver)

    def _get_row_with_hypervisor_name(self, name):
        return self.hypervisor_table.get_row(self.HYPERVISOR_TABLE_NAME_COLUMN, name)

    def _get_row_with_compute_host_name(self, name):
        return self.compute_host_table.get_row(self.COMPUTE_HOST_TABLE_NAME_COLUMN, name)

    def is_hypervisor_present(self, name):
        return bool(self._get_row_with_hypervisor_name(name))

    def get_hypervisor_info(self, name, header):
        row = self._get_row_with_hypervisor_name(name)
        return row.cells[header].text

    def is_compute_host_present(self, name):
        return bool(self._get_row_with_compute_host_name(name))

    def get_compute_host_info(self, name, header):
        row = self._get_row_with_compute_host_name(name)
        return row.cells[header].text

    def disable_service(self, name, reason=None):
        row = self._get_row_with_compute_host_name(name)
        disable_service_form = self.compute_host_table.disable_service(row)
        if reason is not None:
            disable_service_form.reason.text = reason
        disable_service_form.submit()

    def enable_service(self, name, reason=None):
        row = self._get_row_with_compute_host_name(name)
        self.compute_host_table.enable_service(row)

    def go_to_hypervisor_tab(self):
        self.go_to_tab(self.HYPERVISOR_TAB_INDEX)

    def go_to_compute_host_tab(self):
        self.go_to_tab(self.COMPUTEHOST_TAB_INDEX)
