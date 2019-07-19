from selenium.common import exceptions

from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.pages.project.network.routerinterfacespage import RouterInterfacesPage
from utils.horizon.pages.project.network.routeroverviewpage import RouterOverviewPage
from utils.horizon.regions import forms
from utils.horizon.regions import tables
from time import sleep


class RoutersTable(tables.TableRegion):
    name = "routers"
    CREATE_ROUTER_FORM_FIELDS = ("name", "admin_state_up", "external_network", "mode")
    SET_GATEWAY_FORM_FIELDS = ("network_id",)
    EIDT_ROUTER_FORM_FIELDS = ("name", "admin_state", "mode")

    @tables.bind_table_action('create')
    def create_router(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.CREATE_ROUTER_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_router(self, delete_button):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_router_by_row(self, delete_button, row):
        delete_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('clear')
    def clear_gateway(self, clear_gateway_button, row):
        clear_gateway_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('setgateway')
    def set_gateway(self, set_gateway_button, row):
        set_gateway_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.SET_GATEWAY_FORM_FIELDS)

    @tables.bind_row_action('update')
    def edit_router(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EIDT_ROUTER_FORM_FIELDS)


class RoutersPage(basepage.BasePage):

    PARTIAL_URL = 'project/routers'
    ROUTERS_TABLE_NAME_COLUMN = 'Name'

    _interfaces_tab_locator = (by.By.CSS_SELECTOR,
                               'a[href*="tab=router_details__interfaces"]')

    def _get_row_with_router_name(self, name):
        return self.routers_table.get_row(
            self.ROUTERS_TABLE_NAME_COLUMN, name)

    @property
    def routers_table(self):
        return RoutersTable(self.driver)

    def create_router(self, name, admin_state_up=None,
                      external_network=None, router_type=None):
        create_router_form = self.routers_table.create_router()
        create_router_form.name.text = name
        if admin_state_up is True:
            create_router_form.admin_state_up.mark()
        if admin_state_up is False:
            create_router_form.admin_state_up.unmark()
        if external_network is not None:
            create_router_form.external_network.text = external_network
        if router_type is not None:
            create_router_form.mode.text = router_type
        create_router_form.submit()

    def edit_router(self, name, new_name=None,
                    enable_admin_state=None, router_type=None):
        row = self._get_row_with_router_name(name)
        edit_rouer_form = self.routers_table.edit_router(row)
        if new_name is not None:
            edit_rouer_form.name.text = new_name
        if enable_admin_state is True:
            edit_rouer_form.admin_state.mark()
        if enable_admin_state is False:
            edit_rouer_form.admin_state.unmark()
        if router_type is not None:
            edit_rouer_form.mode.text = router_type
        edit_rouer_form.submit()

    def set_gateway(self, router_name, external_network):
        row = self._get_row_with_router_name(router_name)
        set_gateway_form = self.routers_table.set_gateway(row)
        set_gateway_form.network_id.text = external_network
        set_gateway_form.submit()

    def clear_gateway(self, name):
        row = self._get_row_with_router_name(name)
        confirm_clear_gateway_form = self.routers_table.clear_gateway(row)
        confirm_clear_gateway_form.submit()

    def delete_router(self, name):
        row = self._get_row_with_router_name(name)
        row.mark()
        confirm_delete_routers_form = self.routers_table.delete_router()
        confirm_delete_routers_form.submit()

    def delete_router_by_row(self, name):
        row = self._get_row_with_router_name(name)
        confirm_delete_routers_form = self.routers_table.delete_router_by_row(row)
        confirm_delete_routers_form.submit()

    def is_router_present(self, name):
        return bool(self._get_row_with_router_name(name))

    def get_router_info(self, router_name, header):
        row = self._get_row_with_router_name(router_name)
        return row.cells[header].text

    def go_to_interfaces_page(self, name):
        self._get_element(by.By.LINK_TEXT, name).click()
        self._get_element(*self._interfaces_tab_locator).click()
        return RouterInterfacesPage(self.driver)

    def go_to_overview_page(self, name):
        self._get_element(by.By.LINK_TEXT, name).click()
        return RouterOverviewPage(self.driver, name)
