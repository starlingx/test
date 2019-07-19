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
from selenium.common import exceptions
from selenium.webdriver.common import by
from utils.horizon.regions import baseregion
import time


class DropDownMenuRegion(baseregion.BaseRegion):
    """Drop down menu region."""

    _menu_container_locator = (by.By.CSS_SELECTOR, 'ul.dropdown-menu')
    _menu_items_locator = (by.By.CSS_SELECTOR,
                           'ul.dropdown-menu > li > *')
    _dropdown_locator = (by.By.CSS_SELECTOR, '.dropdown')
    _active_cls = 'selenium-active'

    @property
    def menu_items(self):
        self.src_elem.click()
        menu_items = self._get_elements(*self._menu_items_locator)
        return menu_items


class UserDropDownMenuRegion(DropDownMenuRegion):
    """Drop down menu located in the right side of the topbar.

    This menu contains links to settings and help.
    """
    _settings_link_locator = (by.By.CSS_SELECTOR,
                              'a[href*="/settings/"]')
    _help_link_locator = (by.By.CSS_SELECTOR,
                          'ul#editor_list li:nth-of-type(2) > a')
    _logout_link_locator = (by.By.CSS_SELECTOR,
                            'a[href*="/auth/logout/"]')
    _rc_v3_link_locator = (by.By.CSS_SELECTOR,
                           'a[href*="api_access/openrc/"]')

    def _theme_picker_locator(self, theme_name):
        return (by.By.CSS_SELECTOR,
                '.theme-picker-item[data-theme="%s"]' % theme_name)

    @property
    def settings_link(self):
        return self._get_element(*self._settings_link_locator)

    @property
    def help_link(self):
        return self._get_element(*self._help_link_locator)

    @property
    def logout_link(self):
        return self._get_element(*self._logout_link_locator)

    @property
    def rc_v2_link(self):
        return self._get_element(*self._rc_v2_link_locator)

    @property
    def rc_v3_link(self):
        return self._get_element(*self._rc_v3_link_locator)

    def click_on_settings(self):
        self.src_elem.click()
        self.settings_link.click()

    def click_on_help(self):
        self.src_elem.click()
        self.help_link.click()

    def click_on_rc_v2(self):
        self.src_elem.click()
        self.rc_v2_link.click()

    def click_on_rc_v3(self):
        self.src_elem.click()
        self.rc_v3_link.click()

    def choose_theme(self, theme_name):
        self.open()
        self.theme_picker_link(theme_name).click()

    def click_on_logout(self):
        self.src_elem.click()
        self.logout_link.click()


class TabbedMenuRegion(baseregion.BaseRegion):

    _tab_locator = (by.By.CSS_SELECTOR, 'a')
    _default_src_locator = (by.By.XPATH, '//ul[@role="tablist"]')

    def switch_to(self, index=0):
        self._get_elements(*self._tab_locator)[index].click()


class InstancesTabbedMenuRegion(TabbedMenuRegion):

    _tab_locator = (by.By.XPATH, '//li[starts-with(@class,"nav-item ng-scope")]')
    _default_src_locator = (by.By.XPATH, '//ul[@class="nav nav-pills nav-stacked"]')


class ProjectDropDownRegion(DropDownMenuRegion):
    _menu_items_locator = (
        by.By.CSS_SELECTOR, 'ul.context-selection li > a')

    def click_on_project(self, name):
        for item in self.menu_items:
            if item.text == name:
                item.click()
                break
        else:
            raise exceptions.NoSuchElementException(
                "Not found element with text: %s" % name)


class MembershipMenuRegion(baseregion.BaseRegion):
    _available_members_locator = (
        by.By.CSS_SELECTOR, 'ul.available_members > ul.btn-group')

    _allocated_members_locator = (
        by.By.CSS_SELECTOR, 'ul.members > ul.btn-group')

    _add_remove_member_sublocator = (
        by.By.CSS_SELECTOR, 'li > a[href="#add_remove"]')

    _member_name_sublocator = (
        by.By.CSS_SELECTOR, 'li.member > span.display_name')

    _member_roles_widget_sublocator = (by.By.CSS_SELECTOR, 'li.role_options')

    _member_roles_widget_open_subsublocator = (by.By.CSS_SELECTOR, 'a.btn')

    _member_roles_widget_roles_subsublocator = (
        by.By.CSS_SELECTOR, 'ul.role_dropdown > li')

    def _get_member_name(self, element):
        return element.find_element(*self._member_name_sublocator).text

    @property
    def available_members(self):
        return {self._get_member_name(el): el for el in
                self._get_elements(*self._available_members_locator)}

    @property
    def allocated_members(self):
        return {self._get_member_name(el): el for el in
                self._get_elements(*self._allocated_members_locator)}

    def allocate_member(self, name, available_members=None):
        # NOTE(tsufiev): available_members here (and allocated_members below)
        # are meant to be used for performance optimization to reduce the
        # amount of calls to selenium by reusing still valid element reference
        if available_members is None:
            available_members = self.available_members

        available_members[name].find_element(
            *self._add_remove_member_sublocator).click()

    def deallocate_member(self, name, allocated_members=None):
        if allocated_members is None:
            allocated_members = self.allocated_members

        allocated_members[name].find_element(
            *self._add_remove_member_sublocator).click()

    def _get_member_roles_widget(self, name, allocated_members=None):
        if allocated_members is None:
            allocated_members = self.allocated_members

        return allocated_members[name].find_element(
            *self._member_roles_widget_sublocator)

    def _get_member_all_roles(self, name, allocated_members=None):
        roles_widget = self._get_member_roles_widget(name, allocated_members)
        return roles_widget.find_elements(
            *self._member_roles_widget_roles_subsublocator)

    @staticmethod
    def _is_role_selected(role):
        return 'selected' in role.get_attribute('class').split()

    @staticmethod
    def _get_hidden_text(role):
        return role.get_attribute('textContent')

    def get_member_available_roles(self, name, allocated_members=None,
                                   strip=True):
        roles = self._get_member_all_roles(name, allocated_members)
        return [(self._get_hidden_text(role).strip() if strip else role)
                for role in roles if not self._is_role_selected(role)]

    def get_member_allocated_roles(self, name, allocated_members=None,
                                   strip=True):
        roles = self._get_member_all_roles(name, allocated_members)
        return [(self._get_hidden_text(role).strip() if strip else role)
                for role in roles if self._is_role_selected(role)]

    def open_member_roles_dropdown(self, name, allocated_members=None):
        widget = self._get_member_roles_widget(name, allocated_members)
        button = widget.find_element(
            *self._member_roles_widget_open_subsublocator)
        button.click()

    def _switch_member_roles(self, name, roles2toggle, method,
                             allocated_members=None):
        self.open_member_roles_dropdown(name, allocated_members)
        roles = method(name, allocated_members, False)
        roles2toggle = set(roles2toggle)
        for role in roles:
            role_name = role.text.strip()
            if role_name in roles2toggle:
                role.click()
                roles2toggle.remove(role_name)
            if not roles2toggle:
                break

    def allocate_member_roles(self, name, roles2add, allocated_members=None):
        self._switch_member_roles(
            name, roles2add, self.get_member_available_roles,
            allocated_members=allocated_members)

    def deallocate_member_roles(self, name, roles2remove,
                                allocated_members=None):
        self._switch_member_roles(
            name, roles2remove, self.get_member_allocated_roles,
            allocated_members=allocated_members)
