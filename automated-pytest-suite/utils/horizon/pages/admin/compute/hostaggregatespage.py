from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from utils.horizon.regions import menus
from utils.horizon import helper


class HostAggregatesTable(tables.TableRegion):
    name = "host_aggregates"

    CREATE_HOST_AGGREGATE_FORM_FIELDS = (("name", "availability_zone"),
                                         {"members": menus.MembershipMenuRegion})
    MANAGE_HOSTS_FORM_FIELDS = ({"members": menus.MembershipMenuRegion})

    @tables.bind_table_action('create')
    def create_host_aggregate(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.CREATE_HOST_AGGREGATE_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_host_aggregate(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_host_aggregate_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('manage')
    def manage_hosts(self, manage_button, row):
        manage_button.click()
        return forms.FormRegion(self.driver, field_mappings=self.MANAGE_HOSTS_FORM_FIELDS)


class AvilabilityZoneTable(tables.TableRegion):
    name = "availability_zones"
    pass


class HostaggregatesPage(basepage.BasePage):

    PARTIAL_URL = 'admin/aggregates'
    HOST_AGGREGATES_TABLE_NAME_COLUMN = 'Name'
    AVAILABILITY_ZONES_TABLE_NAME_COLUMN = 'Availability Zone Name'

    @property
    def host_aggregates_table(self):
        return HostAggregatesTable(self.driver)

    @property
    def availability_zons_table(self):
        return AvilabilityZoneTable(self.driver)

    def _get_host_aggregate_row_by_name(self, name):
        return self.host_aggregates_table.get_row(
            self.HOST_AGGREGATES_TABLE_NAME_COLUMN, name)

    def _get_availability_zone_row_by_name(self, name):
        return self.availability_zons_table.get_row(
            self.AVAILABILITY_ZONES_TABLE_NAME_COLUMN, name)

    def create_host_aggregate(self, name=None, availability_zone=None):
        create_host_aggregate_form = self.host_aggregates_table.create_host_aggregate()
        if name is None:
            name = helper.gen_resource_name('aggregate')
        create_host_aggregate_form.name.text = name
        if availability_zone is not None:
            create_host_aggregate_form.availability_zone.text = availability_zone
        create_host_aggregate_form.submit()
        return name

    def delete_host_aggregate(self, name):
        row = self._get_host_aggregate_row_by_name(name)
        row.mark()
        confirmation_form = self.host_aggregates_table.delete_host_aggregate()
        confirmation_form.submit()

    def is_host_aggregate_present(self, name):
        return bool(self._get_host_aggregate_row_by_name(name))

    def is_availability_zones_present(self, name):
        return bool(self._get_availability_zone_row_by_name(name))

    def get_host_aggregate_info(self, name, header):
        row = self._get_host_aggregate_row_by_name(name)
        return row.cells[header].text

    def get_availability_zone_info(self, name, header):
        row = self._get_availability_zone_row_by_name(name)
        return row.cells[header].text
