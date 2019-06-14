#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class UsageTable(tables.TableRegion):
    name = 'project_usage'


class OverviewPage(basepage.BasePage):
    _date_form_locator = (by.By.ID, 'date_form')

    USAGE_TABLE_NAME_COLUMN = 'Instance Name'

    @property
    def usage_table(self):
        return UsageTable(self.driver, self)

    def _get_row_with_instance_name(self, name):
        return self.usage_table.get_row(self.USAGE_TABLE_NAME_COLUMN, name)

    def is_instance_present(self, name):
        return bool(self._get_row_with_instance_name(name))

    def get_instance_info(self, instance_name, header):
        row = self._get_row_with_instance_name(instance_name)
        return row.cells[header].text

    @property
    def date_form(self):
        src_elem = self._get_element(*self._date_form_locator)
        return forms.DateFormRegion(self.driver, src_elem)

    def set_usage_query_time_period(self, start_date, end_date):
        self.date_form.query(start_date, end_date)
