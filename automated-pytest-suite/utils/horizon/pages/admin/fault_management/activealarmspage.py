from utils.horizon.pages import basepage
from utils.horizon.regions import tables
from utils.horizon.regions import forms


class AlarmsTable(tables.TableRegion):
    name = "alarms"
    pass


class ActiveAlarmsPage(basepage.BasePage):

    PARTIAL_URL = 'admin/active_alarms'
    ACTIVE_ALARMS_TABLE_NAME_COLUMN = 'Timestamp'

    @property
    def alarms_table(self):
        return AlarmsTable(self.driver)

    def _get_row_with_alarm_timestamp(self, timestamp):
        return self.alarms_table.get_row(self.ACTIVE_ALARMS_TAB, timestamp)

    def is_active_alarm_present(self, timestamp):
        return bool(self._get_row_with_alarm_timestamp(timestamp))
