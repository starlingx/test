from utils.horizon.pages import basepage
from utils.horizon.regions import tables


class ServicesTable(tables.TableRegion):
    name = "services"
    pass


class ControllerServicesTable(tables.TableRegion):
    name = "controller_services"
    pass


class ComputeServicesTable(tables.TableRegion):
    name = "nova_services"
    pass


class BlockStorageServicesTable(tables.TableRegion):
    name = "cinder_services"
    pass


class NetworkAgentsTable(tables.TableRegion):
    name = "network_agents"
    pass


class OrchestrationServicesTable(tables.TableRegion):
    name = "heat_services"
    pass


class SystemInformationPage(basepage.BasePage):

    PARTIAL_URL = 'admin/info'
    SERVICES_TAB = 0
    CONTROLLER_SERVICES_TAB = 1
    COMPUTE_SERVICES_TAB = 2
    BLOCK_STORAGE_SERVICES_TAB = 3
    NETWORK_AGENTS_TAB = 4
    ORCHESTRATION_SERVICES_TAB = 5

    @property
    def services_table(self):
        return ServicesTable(self.driver)

    @property
    def controller_services_table(self):
        return ControllerServicesTable(self.driver)

    @property
    def compute_services_table(self):
        return ComputeServicesTable(self.driver)

    @property
    def block_torage_services_table(self):
        return BlockStorageServicesTable(self.driver)

    @property
    def network_agents_table(self):
        return NetworkAgentsTable(self.driver)

    @property
    def orchestration_services_table(self):
        return OrchestrationServicesTable(self.driver)

    def go_to_services_tab(self):
        self.go_to_tab(self.SERVICES_TAB)

    def go_to_controller_services_tab(self):
        self.go_to_tab(self.CONTROLLER_SERVICES_TAB)

    def go_to_compute_services_tab(self):
        self.go_to_tab(self.COMPUTE_SERVICES_TAB)

    def go_to_block_storage_services_tab(self):
        self.go_to_tab(self.BLOCK_STORAGE_SERVICES_TAB)

    def go_to_network_agents_tab(self):
        self.go_to_tab(self.NETWORK_AGENTS_TAB)

    def go_to_orchestration_services_tab(self):
        self.go_to_tab(self.ORCHESTRATION_SERVICES_TAB)


