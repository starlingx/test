from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.pages.settings import changepasswordpage
from utils.horizon.regions import forms


class UsersettingsPage(basepage.BasePage):
    PARTIAL_URL = 'settings'
    DEFAULT_LANGUAGE = "en"
    DEFAULT_TIMEZONE = "UTC"
    DEFAULT_PAGESIZE = "20"
    DEFAULT_LOGLINES = "35"
    DEFAULT_SETTINGS = {
        "language": DEFAULT_LANGUAGE,
        "timezone": DEFAULT_TIMEZONE,
        "pagesize": DEFAULT_PAGESIZE,
        "loglines": DEFAULT_LOGLINES
    }

    SETTINGS_FORM_FIELDS = (
        "language", "timezone", "pagesize", "instance_log_length")

    _settings_form_locator = (by.By.ID, 'user_settings_modal')
    _change_password_tab_locator = (by.By.CSS_SELECTOR,
                                    'a[href*="/settings/password/"]')

    def __init__(self, driver, port=None):
        super(UsersettingsPage, self).__init__(driver, port=port)
        self._page_title = "User Settings"

    @property
    def settings_form(self):
        src_elem = self._get_element(*self._settings_form_locator)
        return forms.FormRegion(
            self.driver, src_elem=src_elem,
            field_mappings=self.SETTINGS_FORM_FIELDS)

    @property
    def changepassword(self):
        return changepasswordpage.ChangepasswordPage(self.driver)

    @property
    def change_password_tab(self):
        return self._get_element(*self._change_password_tab_locator)

    def change_language(self, lang=DEFAULT_LANGUAGE):
        self.settings_form.language.value = lang
        self.settings_form.submit()

    def change_timezone(self, timezone=DEFAULT_TIMEZONE):
        self.settings_form.timezone.value = timezone
        self.settings_form.submit()

    def change_pagesize(self, size=DEFAULT_PAGESIZE):
        self.settings_form.pagesize.value = size
        self.settings_form.submit()

    def change_loglines(self, lines=DEFAULT_LOGLINES):
        self.settings_form.instance_log_length.value = lines
        self.settings_form.submit()

    def return_to_default_settings(self):
        self.change_language()
        self.change_timezone()
        self.change_pagesize()
        self.change_loglines()

    def go_to_change_password_page(self):
        self.change_password_tab.click()
        return changepasswordpage.ChangepasswordPage(self.driver)
