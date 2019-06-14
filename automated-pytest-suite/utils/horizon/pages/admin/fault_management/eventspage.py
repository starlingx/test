from utils.horizon.pages import basepage
from utils.horizon.regions import tables
from utils.horizon.regions import forms


class EventLogsTable(tables.TableRegion):
    name = "eventlogs"
    pass


class EventLogsPage(basepage.BasePage):

    PARTIAL_URL = 'admin/events'
    EVENT_LOGS_TABLE_NAME_COLUMN = 'Timestamp'

    @property
    def event_logs_table(self):
        return EventLogsTable(self.driver)

    def _get_row_with_event_log_timestamp(self, timestamp):
        return self.event_logs_table.get_row(self.EVENT_LOGS_TABLE_NAME_COLUMN, timestamp)

    def is_event_log_present(self, timestamp):
        return bool(self._get_row_with_event_log_timestamp(timestamp))
