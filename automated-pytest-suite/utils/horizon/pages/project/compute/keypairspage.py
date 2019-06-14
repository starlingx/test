from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class KeypairForm:

    def setname(self, name):
        name_element = self.driver.find_element_by_css_selector("div.modal-body input")
        name_element.send_keys(name)

    def submit(self):
        submit_btn = self.driver.find_elements_by_css_selector("button.btn.btn-primary")[0]
        submit_btn.click()

    def done(self):
        submit_btn = self.driver.find_elements_by_css_selector(
            "button[class='btn btn-primary ng-binding']")
        submit_btn.click()

    def __init__(self, driver):
        self.driver = driver


class KeypairsTable(tables.TableRegion):
    name = "OS::Nova::Keypair"
    CREATE_KEY_PAIR_FORM_FIELDS = 'name'
    _rows_locator = (by.By.CSS_SELECTOR, 'tbody > tr[class="ng-scope"]')

    @tables.bind_table_action('btn-default', attribute_search='class')
    def create_keypair(self, create_button):
        create_button.click()
        return KeypairForm(self.driver)

    @tables.bind_row_action('btn-danger', attribute_search='class')
    def delete_keypair_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_table_action('btn-danger', attribute_search='class')
    def delete_keypair(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    def _table_locator(self, table_name):
        return by.By.CSS_SELECTOR, 'hz-resource-table[resource-type-name="%s"]' % table_name


class KeypairsPage(basepage.BasePage):
    PARTIAL_URL = 'project/key_pairs'

    KEY_PAIRS_TABLE_ACTIONS = ("create", "import", "delete")
    KEY_PAIRS_TABLE_ROW_ACTION = "delete"
    KEY_PAIRS_TABLE_NAME_COLUMN = 'Name'

    def __init__(self, driver, port=None):
        super(KeypairsPage, self).__init__(driver, port=port)
        self._page_title = "Key Pairs"

    def _get_row_with_keypair_name(self, name):
        return self.keypairs_table.get_row(self.KEY_PAIRS_TABLE_NAME_COLUMN, name)

    @property
    def keypairs_table(self):
        return KeypairsTable(self.driver)

    @property
    def delete_keypair_form(self):
        return forms.BaseFormRegion(self.driver)

    def is_keypair_present(self, name):
        return bool(self._get_row_with_keypair_name(name))

    def get_keypair_info(self, name, header):
        row = self._get_row_with_keypair_name(name)
        return row.cells[header].text

    def create_keypair(self, keypair_name):
        create_keypair_form = self.keypairs_table.create_keypair()
        create_keypair_form.setname(keypair_name)
        create_keypair_form.submit()

    def delete_keypair_by_row(self, name):
        row = self._get_row_with_keypair_name(name)
        delete_keypair_form = self.keypairs_table.delete_keypair_by_row(row)
        delete_keypair_form.submit()

    def delete_keypair(self, name):
        row = self._get_row_with_keypair_name(name)
        row.mark()
        delete_keypair_form = self.keypairs_table.delete_keypair()
        delete_keypair_form.submit()
