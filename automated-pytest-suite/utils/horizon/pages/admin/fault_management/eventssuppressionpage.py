from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from selenium.webdriver.common import by


class EventsSuppressionTable(tables.TableRegion):
    name = "OS::StarlingX::EventsSuppression"

    @tables.bind_row_action('danger', attribute_search='class')
    def suppress_event(self, suppress_button, row):
        suppress_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('danger', attribute_search='class')
    def unsuppress_event(self, unsuppress_button, row):
        unsuppress_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    def _table_locator(self, table_name):
        return by.By.CSS_SELECTOR, \
               'hz-resource-table[resource-type-name="%s"]' % table_name


class EventsSuppressionPage(basepage.BasePage):

    PARTIAL_URL = 'admin/events_suppression'
    EVENTS_SUPPRESSION_TABLE_NAME_COLUMN = 'Event ID'
    # EVENTS_SUPPRESSION_TAB = 2

    @property
    def events_suppression_table(self):
        return EventsSuppressionTable(self.driver)

    def _get_row_with_event_id(self, event_id):
        return self.events_suppression_table.get_row(
            self.EVENTS_SUPPRESSION_TABLE_NAME_COLUMN, event_id)

    def suppress_event(self, event_id):
        row = self._get_row_with_event_id(event_id)
        confirm_form = self.events_suppression_table.suppress_event(row)
        confirm_form.submit()

    def unsuppress_event(self, event_id):
        row = self._get_row_with_event_id(event_id)
        confirm_form = self.events_suppression_table.unsuppress_event(row)
        confirm_form.submit()
