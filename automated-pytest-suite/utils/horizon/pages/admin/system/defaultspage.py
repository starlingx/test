from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class DefaultComputeQuotasTable(tables.TableRegion):
    name = "compute_quotas"

    UPDATE_DEFAULTS_FORM_FIELDS = (
        ("instances",
        "cores",
        "ram",
        "metadata_items",
        "key_pairs",
        "server_groups",
        "server_group_members",
        "injected_files",
        "injected_file_content_bytes",
        "injected_file_path_bytes"),
        ("volumes",
        "gigabytes",
        "snapshots")
    )

    @tables.bind_table_action('update_compute_defaults')
    def update(self, update_button):
        update_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver,
            self.UPDATE_DEFAULTS_FORM_FIELDS
        )


class DefaultVolumeQuotasTable(DefaultComputeQuotasTable):
    name = "volume_quotas"

    @tables.bind_table_action('update_volume_defaults')
    def update(self, update_button):
        update_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(
            self.driver,
            self.UPDATE_DEFAULTS_FORM_FIELDS
        )


class DefaultNetworkQuotasTable(tables.TableRegion):
    name = "network_quotas"


class DefaultsPage(basepage.BasePage):
    PARTIAL_URL = 'admin/defaults'
    COMPUTE_QUOTAS_TAB = 0
    VOLUME_QUOTAS_TAB = 1
    NETWORK_QUOTAS_TAB = 2
    QUOTAS_TABLE_NAME_COLUMN = 'Quota Name'
    QUOTAS_TABLE_LIMIT_COLUMN = 'Limit'
    DEFAULT_COMPUTE_QUOTA_NAMES = [
        'Instances',
        'VCPUs',
        'RAM',
        'Metadata Items',
        'Key Pairs',
        'Server Groups',
        'Server Group Members',
        'Injected Files',
        'Injected File Content Bytes',
        'Length of Injected File Path'
    ]
    DEFAULT_VOLUME_QUOTA_NAMES = [
        'Volumes',
        'Total Size of Volumes and Snapshots (GiB)',
        'Volume Snapshots'
    ]

    def _get_compute_quota_row(self, name):
        return self.default_compute_quotas_table.get_row(
            self.QUOTAS_TABLE_NAME_COLUMN, name)

    def _get_volume_quota_row(self, name):
        return self.default_volume_quotas_table.get_row(
            self.QUOTAS_TABLE_NAME_COLUMN, name)

    @property
    def default_compute_quotas_table(self):
        return DefaultComputeQuotasTable(self.driver)

    @property
    def default_volume_quotas_table(self):
        return DefaultVolumeQuotasTable(self.driver)

    @property
    def default_network_quotas_table(self):
        return DefaultNetworkQuotasTable(self.driver)

    @property
    def compute_quota_values(self):
        quota_dict = {}
        for row in self.default_compute_quotas_table.rows:
            if row.cells[self.QUOTAS_TABLE_NAME_COLUMN].text in \
                    self.DEFAULT_COMPUTE_QUOTA_NAMES:
                quota_dict[row.cells[self.QUOTAS_TABLE_NAME_COLUMN].text] = \
                    int(row.cells[self.QUOTAS_TABLE_LIMIT_COLUMN].text)
        return quota_dict

    @property
    def volume_quota_values(self):
        quota_dict = {}
        for row in self.default_volume_quotas_table.rows:
            if row.cells[self.QUOTAS_TABLE_NAME_COLUMN].text in \
                    self.DEFAULT_VOLUME_QUOTA_NAMES:
                quota_dict[row.cells[self.QUOTAS_TABLE_NAME_COLUMN].text] = \
                    int(row.cells[self.QUOTAS_TABLE_LIMIT_COLUMN].text)
        return quota_dict

    def update_compute_defaults(self, add_up):
        update_form = self.default_compute_quotas_table.update()
        update_form.instances.value = int(update_form.instances.value) + add_up
        update_form.cores.value = int(update_form.cores.value) + add_up
        update_form.ram.value = int(update_form.ram.value) + add_up
        update_form.metadata_items.value = \
            int(update_form.metadata_items.value) + add_up
        update_form.key_pairs.value = int(update_form.key_pairs.value) + add_up
        update_form.server_groups.value = int(update_form.server_groups.value) + add_up
        update_form.server_group_members.value = int(update_form.server_group_members.value) + add_up
        update_form.injected_files.value = int(
            update_form.injected_files.value) + add_up
        update_form.injected_file_content_bytes.value = \
            int(update_form.injected_file_content_bytes.value) + add_up
        update_form.injected_file_path_bytes.value = \
            int(update_form.injected_file_path_bytes.value) + add_up
        update_form.submit()

    def update_volume_defaults(self, add_up):
        update_form = self.default_volume_quotas_table.update()
        update_form.switch_to(self.VOLUME_QUOTAS_TAB)
        update_form.volumes.value = int(update_form.volumes.value) + add_up
        update_form.gigabytes.value = int(update_form.gigabytes.value) + add_up
        update_form.snapshots.value = int(update_form.snapshots.value) + add_up
        update_form.submit()

    def is_compute_quota_a_match(self, quota_name, limit):
        row = self._get_compute_quota_row(quota_name)
        return row.cells[self.QUOTAS_TABLE_LIMIT_COLUMN].text == str(limit)

    def is_volume_quota_a_match(self, quota_name, limit):
        row = self._get_volume_quota_row(quota_name)
        return row.cells[self.QUOTAS_TABLE_LIMIT_COLUMN].text == str(limit)

    def go_to_compute_quotas_tab(self):
        self.go_to_tab(self.COMPUTE_QUOTAS_TAB)

    def go_to_volume_quotas_tab(self):
        self.go_to_tab(self.VOLUME_QUOTAS_TAB)

    def go_to_network_quotas_tab(self):
        self.go_to_tab(self.NETWORK_QUOTAS_TAB)
