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

import functools

from selenium.common import exceptions
from selenium.webdriver.common import by

from utils.horizon.regions import baseregion
NORMAL_COLUMN_CLASS = 'normal_column'


class RowRegion(baseregion.BaseRegion):
    """Classic table row."""

    _add_locator = (by.By.XPATH, ".//action-list")
    _cell_locator = (by.By.CSS_SELECTOR, 'td')
    _row_checkbox_locator = (
        by.By.CSS_SELECTOR,
        'td .themable-checkbox [type="checkbox"] + label'
    )

    def __init__(self, driver, src_elem, column_names):
        self.column_names = column_names
        super(RowRegion, self).__init__(driver, src_elem)

    @property
    def cells(self):
        try:
            elements = self._get_elements(*self._cell_locator)
        except exceptions.StaleElementReferenceException:
            raise
        return {column_name: elements[i]
                for i, column_name in enumerate(self.column_names)}

    def mark(self):
        chck_box = self._get_element(*self._row_checkbox_locator)
        chck_box.click()

    def add(self):
        add_btn = self._get_element(*self._add_locator)
        add_btn.click()


class TableRegion(baseregion.BaseRegion):
    """Basic class representing table object."""
    name = None

    _heading_locator = (by.By.CSS_SELECTOR, 'h3.table_title')
    _columns_names_locator = (by.By.CSS_SELECTOR, 'thead > tr > th')
    _footer_locator = (by.By.CSS_SELECTOR, 'tfoot > tr > td > span')
    _rows_locator = (by.By.CSS_SELECTOR, 'tbody > tr')
    _empty_table_locator = (by.By.CSS_SELECTOR, 'tbody > tr.empty')
    _search_field_locator = (by.By.CSS_SELECTOR,
                             'div.table_search input.form-control')
    _search_button_locator = (by.By.CSS_SELECTOR,
                              'div.table_search > button')
    _search_option_locator = (by.By.CSS_SELECTOR,
                              'div.table_search > .themable-select')
    marker_name = 'marker'
    prev_marker_name = 'prev_marker'

    def _table_locator(self, table_name):
        return by.By.CSS_SELECTOR, 'table#%s' % table_name

    @property
    def _next_locator(self):
        return by.By.CSS_SELECTOR, 'a[href^="?%s"]' % self.marker_name

    @property
    def _prev_locator(self):
        return by.By.CSS_SELECTOR, 'a[href^="?%s"]' % self.prev_marker_name

    def _search_menu_value_locator(self, value):
        return (by.By.CSS_SELECTOR,
                'ul.dropdown-menu a[data-select-value="%s"]' % value)

    def __init__(self, driver, src_element=None):
        if not src_element:
            self._default_src_locator = self._table_locator(self.__class__.name)
            super(TableRegion, self).__init__(driver)
        else:
            super(TableRegion, self).__init__(driver, src_elem=src_element)

    @property
    def heading(self):
        return self._get_element(*self._heading_locator)

    @property
    def rows(self):
        if self._is_element_present(*self._empty_table_locator):
            return []
        else:
            return self._get_rows()

    @property
    def column_names(self):
        names = []
        for element in self._get_elements(*self._columns_names_locator):
            names.append(element.text)
        return names

    @property
    def footer(self):
        return self._get_element(*self._footer_locator)

    def filter(self, value):
        self._set_search_field(value)
        self._click_search_btn()

    def set_filter_value(self, value):
        search_menu = self._get_element(*self._search_option_locator)
        search_menu.click()
        item_locator = self._search_menu_value_locator(value)
        search_menu.find_element(*item_locator).click()

    def get_row(self, column_name, text, exact_match=True):
        """Get row that contains specified text in specified column.

        In case exact_match is set to True, text contained in row must equal
        searched text, otherwise occurrence of searched text in the column
        text will result in row match.
        """
        def get_text(element):
            # print(element.text)
            # text = element.text('data-selenium')
            return element.text

        for row in self.rows:
            try:
                cell = row.cells[column_name]
                if exact_match and text == get_text(cell):
                    return row
                if not exact_match and text in get_text(cell):
                    return row
            # NOTE(tsufiev): if a row was deleted during iteration
            except exceptions.StaleElementReferenceException:
                pass
        return None

    def _set_search_field(self, value):
        srch_field = self._get_element(*self._search_field_locator)
        srch_field.clear()
        srch_field.send_keys(value)

    def _click_search_btn(self):
        btn = self._get_element(*self._search_button_locator)
        btn.click()

    def _get_rows(self, *args):
        return [RowRegion(self.driver, elem, self.column_names)
                for elem in self._get_elements(*self._rows_locator)]

    def _is_row_deleted(self, evaluator):
        def predicate(driver):
            if self._is_element_present(*self._empty_table_locator):
                return True
            with self.waits_disabled():
                return evaluator()
        try:
            self._wait_until(predicate)
        except exceptions.TimeoutException:
            return False
        except IndexError:
            return True
        return True

    def is_row_deleted(self, row_getter):
        return self._is_row_deleted(
            lambda: not self._is_element_displayed(row_getter()))

    def are_rows_deleted(self, rows_getter):
        return self._is_row_deleted(
            lambda: all([not self._is_element_displayed(row) for row
                         in rows_getter()]))

    def wait_cell_status(self, cell_getter, statuses, timeout=None):
        if not isinstance(statuses, (list, tuple)):
            statuses = (statuses,)
        try:
            return self._wait_till_text_present_in_element(cell_getter,
                                                           statuses, timeout=timeout)
        except: # exceptions.TimeoutException:
            return False

    def is_next_link_available(self):
        try:
            self._turn_off_implicit_wait()
            return self._is_element_visible(*self._next_locator)
        finally:
            self._turn_on_implicit_wait()

    def is_prev_link_available(self):
        try:
            self._turn_off_implicit_wait()
            return self._is_element_visible(*self._prev_locator)
        finally:
            self._turn_on_implicit_wait()

    def turn_next_page(self):
        if self.is_next_link_available():
            lnk = self._get_element(*self._next_locator)
            lnk.click()

    def turn_prev_page(self):
        if self.is_prev_link_available():
            lnk = self._get_element(*self._prev_locator)
            lnk.click()

    def assert_definition(self, expected_table_definition, sorting=False):
        """Checks that actual table is expected one.

        Items to compare: 'next' and 'prev' links, count of rows and names of
        elements in list
        :param expected_table_definition: expected values (dictionary)
        :param sorting: boolean arg specifying whether to sort actual names
        :return:
        """
        names = [row.cells['name'].text for row in self.rows]
        if sorting:
            names.sort()
        actual_table = {'Next': self.is_next_link_available(),
                        'Prev': self.is_prev_link_available(),
                        'Count': len(self.rows),
                        'Names': names}
        self.assertDictEqual(actual_table, expected_table_definition)


def bind_table_action(action_name, attribute_search='id'):
    """Decorator to bind table region method to an actual table action button.

    Many table actions when started (by clicking a corresponding button
    in UI) lead to some form showing up. To further interact with this form,
    a Python/ Selenium wrapper needs to be created for it. It is very
    convenient to return this newly created wrapper in the same method that
    initiates clicking an actual table action button. Binding the method to a
    button is performed behind the scenes in this decorator.

    .. param:: action_name

        Part of the action button id which is specific to action itself. It
        is safe to use action `name` attribute from the dashboard tables.py
        code.
    """
    _actions_locator = (by.By.CSS_SELECTOR, 'div.table_actions > button,'
                                            'delete-image-selected > button,'
                                            'actions > action-list > button,'
                                            'div.table_actions > a')

    def decorator(method):
        @functools.wraps(method)
        def wrapper(table):
            actions = table._get_elements(*_actions_locator)
            action_element = None
            for action in actions:
                target_action_id = '%s__action_%s' % (table.name, action_name)
                if action.get_attribute(attribute_search).endswith(action_name):
                    action_element = action
                    break
            if action_element is None:
                msg = "Could not bind method '%s' to action control '%s'" % (
                    method.__name__, action_name)
                raise ValueError(msg)
            return method(table, action_element)
        return wrapper
    return decorator


def bind_row_action(action_name, attribute_search='id', secondary_locator_index=None):
    """A decorator to bind table region method to an actual row action button.

    Many table actions when started (by clicking a corresponding button
    in UI) lead to some form showing up. To further interact with this form,
    a Python/ Selenium wrapper needs to be created for it. It is very
    convenient to return this newly created wrapper in the same method that
    initiates clicking an actual action button. Row action could be
    either primary (if its name is written right away on row action
    button) or secondary (if its name is inside of a button drop-down). Binding
    the method to a button and toggling the button drop-down open (in case
    a row action is secondary) is performed behind the scenes in this
    decorator.

    .. param:: action_name

        Part of the action button id which is specific to action itself. It
        is safe to use action `name` attribute from the dashboard tables.py
        code.

    .. param:: attribute_search

        Attribute that is searched for to find action element. By default it
        looks for id but another identifying attribute can be specified.

    .. param:: secondary_locator_index

        Used to look for nth child of 'ul' when all children have the
        identical attributes.
    """
    # NOTE(tsufiev): button tag could be either <a> or <button> - target
    # both with *. Also primary action could be single as well, do not use
    # .btn-group because of that
    primary_action_locator = (
        by.By.CSS_SELECTOR, 'td.actions_column *.btn:nth-child(1)')
    secondary_actions_opener_locator = (
        by.By.CSS_SELECTOR,
        'td.actions_column *.btn-group > *.btn:nth-child(2)')
    secondary_actions_locator = (
        by.By.CSS_SELECTOR,
        'td.actions_column *.btn-group > ul > li > a, button')
    secondary_locator_by_index = (
        by.By.CSS_SELECTOR,
        'td.actions_column *.btn-group > ul > li:nth-child({}) > a'.format(secondary_locator_index))

    def decorator(method):
        @functools.wraps(method)
        def wrapper(table, row):
            def find_action(element):
                pattern = "__action_%s" % action_name
                return element.get_attribute(attribute_search).endswith(action_name)

            action_element = row._get_element(*primary_action_locator)
            if not find_action(action_element):
                action_element = None
                row._get_element(*secondary_actions_opener_locator).click()
                if secondary_locator_index:
                    action_element = row._get_element(*secondary_locator_by_index)
                else:
                    for element in row._get_elements(*secondary_actions_locator):
                        if find_action(element):
                            action_element = element
                            break

            if action_element is None:
                msg = "Could not bind method '%s' to action control '%s'" % (
                    method.__name__, action_name)
                raise ValueError(msg)
            return method(table, action_element, row)
        return wrapper
    return decorator


def bind_row_anchor_column(column_name):
    """A decorator to bind table region method to a anchor in a column.

    Typical examples of such tables are Project -> Compute -> Images, Admin
    -> System -> Flavors, Project -> Compute -> Instancies.
    The method can be used to follow the link in the anchor by the click.
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(table, row):
            cell = row.cells[column_name]
            action_element = cell.find_element(
                by.By.CSS_SELECTOR, 'td.%s > a' % NORMAL_COLUMN_CLASS)
            return method(table, action_element, row)

        return wrapper
    return decorator
