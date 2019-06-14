from selenium.webdriver.common import by
from utils.horizon.pages import pageobject
from utils.horizon.regions import bars
from utils.horizon.regions import messages


class BasePage(pageobject.PageObject):
    """Base class for all dashboard page objects."""

    _heading_locator = (by.By.CSS_SELECTOR, 'div.page-header')
    _nav_tabs_locator = (by.By.CSS_SELECTOR, 'ul>li>a[data-toggle="tab"]')

    @property
    def heading(self):
        return self._get_element(*self._heading_locator)

    @property
    def topbar(self):
        return bars.TopBarRegion(self.driver)

    @property
    def tabs(self):
        return self._get_elements(*self._nav_tabs_locator)

    @property
    def is_logged_in(self):
        return self.topbar.is_logged_in

    def go_to_home_page(self):
        self.topbar.brand.click()

    def go_to_tab(self, index):
        self.tabs[index].click()

    def log_out(self):
        self.topbar.user_dropdown_menu.click_on_logout()

    def download_rc_v2(self):
        self.topbar.user_dropdown_menu.click_on_rc_v2()

    def download_rc_v3(self):
        self.topbar.user_dropdown_menu.click_on_rc_v3()

    def go_to_help_page(self):
        self.topbar.user_dropdown_menu.click_on_help()

    def find_message_and_dismiss(self, message_level=messages.SUCCESS):
        message = messages.MessageRegion(self.driver, message_level)
        is_message_present = message.exists()
        if is_message_present:
            message.close()
        return is_message_present

    def change_project(self, name):
        self.topbar.user_dropdown_project.click_on_project(name)
