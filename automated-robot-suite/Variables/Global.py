"""
Library of variables commonly used for Horizon tests.

This library contains global variables and XPATHS needed to get web elements
of Horizon web page to navigate through it and use or modify Controllers and
Computes.

Authors:
    - Juan Carlos Alonso <juan.carlos.alonso@intel.com>
    - Elio Martinez <elio.martinez.monroy@intel.com>
    - Juan Pablo Gomez <juan.p.gomez@intel.com>
"""
import getpass

from Config import config

CURRENT_USER = getpass.getuser()

# Default TIMEOUT variable
TIMEOUT = 10

# Variables from configuration file
IP_CONTROLLER_0 = config.get('general', 'IP_UNIT_0_ADDRESS')
IP_CONTROLLER_1 = config.get('general', 'IP_UNIT_1_ADDRESS')
CIRROS_FILE = config.get('general', 'CIRROS_FILE')
CENTOS_FILE = config.get('general', 'CENTOS_FILE')
UBUNTU_FILE = config.get('general', 'UBUNTU_FILE')
WINDOWS_FILE = config.get('general', 'WINDOWS_FILE')
APP_TARBALL = config.get('general', 'APP_TARBALL')
CONTROLLER_TMP_IP = config.get('iso_installer', 'CONTROLLER_TMP_IP')
CIRROS_IMAGE = (
    '/home/{USER}/{IMAGE}'.format(USER=CURRENT_USER, IMAGE=CIRROS_FILE))
CENTOS_IMAGE = (
    '/home/{USER}/{IMAGE}'.format(USER=CURRENT_USER, IMAGE=CENTOS_FILE))
UBUNTU_IMAGE = (
    '/home/{USER}/{IMAGE}'.format(USER=CURRENT_USER, IMAGE=UBUNTU_FILE))
WINDOWS_IMAGE = (
    '/home/{USER}/{IMAGE}'.format(USER=CURRENT_USER, IMAGE=WINDOWS_FILE))
APP_TARBALL_FILE = ('{FILE}'.format(FILE=APP_TARBALL))
HORIZON_URL = ('http://{IP}/'.format(IP=IP_CONTROLLER_0))
HORIZON_USERNAME = config.get('dashboard', 'HORIZON_USERNAME')
HORIZON_PASSWORD = config.get('dashboard', 'HORIZON_PASSWORD')
FF_BROWSER = config.get('dashboard', 'BROWSER')
PROFILE = config.get('dashboard', 'PROFILE')
FF_PROFILE = (
    '/home/{USER}/.mozilla/firefox/{BROWSER_PROFILE}'
    .format(USER=CURRENT_USER, BROWSER_PROFILE=PROFILE))
CLI_USER_NAME = config.get('credentials', 'STX_DEPLOY_USER_NAME')
CLI_USER_PASS = config.get('credentials', 'STX_DEPLOY_USER_PSWD')
STX_ISO_FILE = config.get('general', 'STX_ISO_FILE')

# Variables for Horizon log in page
USERNAME_ID_FIELD = 'id_username'
PASSWORD_ID_FIELD = 'id_password'
LOGIN_ID_BUTTON = 'loginBtn'
HORIZON_PAGE_TITLE = 'Instance Overview - Akraino Edge Stack'
HOST_INV_PAGE_TITLE = 'Host Inventory - Akraino Edge Stack'

# XPATHS for PROJECT Menu

XPATH_PROJECT = (
    '//*[@class="nav nav-pills nav-stacked"]//a[contains(., \'Project\')]')
XPATH_PROJECT_API = (
    '//*[@id="sidebar-accordion-project-default"]'
    '//a[contains(., \'API Access\')]')
XPATH_PROJECT_COMPUTE = (
    '//*[@id="sidebar-accordion-project"]//a[contains(., \'Compute\')]')
XPATH_PROJECT_COMPUTE_OVERVIEW = (
    '//*[@id="sidebar-accordion-project-compute"]'
    '//a[contains(., \'Overview\')]')
XPATH_PROJECT_COMPUTE_INSTANCES = (
    '//*[@id="sidebar-accordion-project-compute"]'
    '//a[contains(., \'Instances\')]')
XPATH_PROJECT_COMPUTE_SERVER_GROUPS = (
    '//*[@id="sidebar-accordion-project-compute"]'
    '//a[contains(., \'Server Groups\')]')
XPATH_PROJECT_COMPUTE_IMAGES = (
    '//*[@id="sidebar-accordion-project-compute"]//a[contains(., \'Images\')]')
XPATH_PROJECT_COMPUTE_KEYPARS = (
    '//*[@id="sidebar-accordion-project-compute"]'
    '//a[contains(., \'Key Pairs\')]')
XPATH_PROJECT_NETWORK = (
    '//*[@id="sidebar-accordion-project"]//a[contains(., \'Network\')]')
XPATH_PROJECT_NETWORK_TOPOLOGY = (
    '//*[@id="sidebar-accordion-project-network"]'
    '//a[contains(., \'Network Topology\')]')
XPATH_PROJECT_NETWORK_NETWORKS = (
    '//*[@id="sidebar-accordion-project-network"]'
    '//a[contains(., \'Networks\')]')
XPATH_PROJECT_NETWORK_ROUTERS = (
    '//*[@id="sidebar-accordion-project-network"]'
    '//a[contains(., \'Routers\')]')
XPATH_PROJECT_NETWORK_SECURITY = (
    '//*[@id="sidebar-accordion-project-network"]'
    '//a[contains(., \'Security Groups\')]')
XPATH_PROJECT_NETWORK_FLOATING = (
    '//*[@id="sidebar-accordion-project-network"]'
    '//a[contains(., \'Floating IPs\')]')
XPATH_PROJECT_ORCHESTRATION = (
    '//*[@id="sidebar-accordion-project"]//a[contains(., \'Orchestration\')]')
XPATH_PROJECT_ORCHESTRATION_STACKS = (
    '//*[@id="sidebar-accordion-project-orchestration"]'
    '//a[contains(., \'Stacks\')]')
XPATH_PROJECT_ORCHESTRATION_RESOURCES = (
    '//*[@id="sidebar-accordion-project-orchestration"]'
    '//a[contains(., \'Resource Types\')]')
XPATH_PROJECT_ORCHESTRATION_TEMPLATE = (
    '//*[@id="sidebar-accordion-project-orchestration"]'
    '//a[contains(., \'Template Versions\')]')

# XPATHS for ADMIN Menu

XPATH_ADMIN = (
    '//*[@class="nav nav-pills nav-stacked"]//a[contains(., \'Admin\')]')
XPATH_ADMIN_OVERVIEW = (
    '//*[@id="sidebar-accordion-admin-default"]//a[contains(., \'Overview\')]')
XPATH_ADMIN_PLATFORM = (
    '//*[@id="sidebar-accordion-admin"]//a[contains(., \'Platform\')]')
XPATH_ADMIN_PLATFORM_FAULT = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Fault Management\')]')
XPATH_ADMIN_PLATFORM_SOFTWARE = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Software Management\')]')
XPATH_ADMIN_PLATFORM_HOST = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Host Inventory\')]')
XPATH_ADMIN_PLATFORM_PROVIDER = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Provider Networks\')]')
XPATH_ADMIN_PLATFORM_TOPOLOGY = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Provider Network Topology\')]')
XPATH_ADMIN_PLATFORM_STORAGE = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'Storage Overview\')]')
XPATH_ADMIN_PLATFORM_SYSTEM = (
    '//*[@id="sidebar-accordion-admin-platform"]'
    '//a[contains(., \'System Configuration\')]')
XPATH_ADMIN_COMPUTE = (
    '//*[@id="sidebar-accordion-admin"]//a[contains(., \'Compute\')]')
XPATH_ADMIN_COMPUTE_SERVER = (
    '//*[@id="sidebar-accordion-admin-compute"]'
    '//a[contains(., \'Server Groups\')]')
XPATH_ADMIN_COMPUTE_HYPERVISORS = (
    '//*[@id="sidebar-accordion-admin-compute"]'
    '//a[contains(., \'Hypervisors\')]')
XPATH_ADMIN_COMPUTE_HOST = (
    '//*[@id="sidebar-accordion-admin-compute"]'
    '//a[contains(., \'Host Aggregates\')]')
XPATH_ADMIN_COMPUTE_INSTANCES = (
    '//*[@id="sidebar-accordion-admin-compute"]'
    '//a[contains(., \'Instances\')]')
XPATH_ADMIN_COMPUTE_FLAVORS = (
    '//*[@id="sidebar-accordion-admin-compute"]//a[contains(., \'Flavors\')]')
XPATH_ADMIN_COMPUTE_IMAGES = (
    '//*[@id="sidebar-accordion-admin-compute"]//a[contains(., \'Images\')]')
XPATH_ADMIN_NETWORK = '{0}admin/networks/'.format(HORIZON_URL)
XPATH_ADMIN_NETWORK_NETWORKS = (
    '//*[@id="sidebar-accordion-admin-network"]//a[contains(., \'Networks\')]')
XPATH_ADMIN_NETWORK_ROUTERS = (
    '//*[@id="sidebar-accordion-admin-network"]//a[contains(., \'Routers\')]')
XPATH_ADMIN_NETWORK_FLOATING = (
    '//*[@id="sidebar-accordion-admin-network"]'
    '//a[contains(., \'Floating IPs\')]')
XPATH_ADMIN_SYSTEM = '{0}admin/defaults/'.format(HORIZON_URL)
XPATH_PROVIDER_NET_TOPOLOGY = '{0}admin/host_topology/'.format(HORIZON_URL)
XPATH_ADMIN_SYSTEM_DEFAULTS = (
    '//*[@id="sidebar-accordion-admin-admin"]//a[contains(., \'Defaults\')]')
XPATH_ADMIN_SYSTEM_METADATA = (
    '//*[@id="sidebar-accordion-admin-admin"]'
    '//a[contains(., \'Metadata Definitions\')]')
XPATH_ADMIN_SYSTEM_SYSTEM = (
    '//*[@id="sidebar-accordion-admin-admin"]'
    '//a[contains(., \'System Information\')]')
XPATH_CHOOSE_IMAGE = '//button[contains(., \'Browse...\')]'

# XPATHS for IDENTITY Menu

XPATH_IDENTITY = (
    '//*[@class="nav nav-pills nav-stacked"]//a[contains(., \'Identity\')]')
XPATH_IDENTITY_PROJECTS = (
    '//*[@id="sidebar-accordion-identity"]//a[contains(., \'Projects\')]')
XPATH_IDENTITY_USERS = (
    '//*[@id="sidebar-accordion-identity"]//a[contains(., \'Users\')]')
XPATH_IDENTITY_GROUPS = (
    '//*[@id="sidebar-accordion-identity"]//a[contains(., \'Groups\')]')
XPATH_IDENTITY_ROLES = (
    '//*[@id="sidebar-accordion-identity"]//a[contains(., \'Roles\')]')
XPATH_FLAVOR_UPDATE_METADATA_CIRROS_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'cirros-generic\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_FLV_SPECIFIC_METADATA_CIRROS_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'cirros-configurable\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_FLAVOR_UPDATE_METADATA_CIRROS = (
    '//table[@id="flavors"]//tr[contains(., \'cirros-generic\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_SPECIFIC_METADATA_CIRROS = (
    '//table[@id="flavors"]//tr[contains(.,\'cirros-configurable\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_UPDATE_METADATA_CENTOS = (
    '//table[@id="flavors"]//tr[contains(., \'centos-generic\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_SPECIFIC_METADATA_CENTOS = (
    '//table[@id="flavors"]//tr[contains(., \'centos-configurable\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_UPDATE_METADATA_UBUNTU = (
    '//table[@id="flavors"]//tr[contains(., \'ubuntu-generic\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_SPECIFIC_METADATA_UBUNTU = (
    '//table[@id="flavors"]//tr[contains(., \'ubuntu-configurable\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_FLAVOR_METADATA_OPTION = (
    '//select[@class="form-control ng-pristine ng-valid ng-scope ng-not-empty '
    'ng-valid-required ng-touched"]')
XPATH_FLAVOR_UPDATE_METADATA_CENTOS_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'centos-generic\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_FLV_SPECIFIC_METADATA_CENTOS_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'centos-configurable\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_FLAVOR_UPDATE_METADATA_UBUNTU_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'ubuntu-generic\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_FLV_SPECIFIC_METADATA_UBUNTU_ACTION = (
    '//table[@id="flavors"]//tr[contains(.,\'ubuntu-configurable\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_INSTANCE_CONSOLE = (
    '//*[@class="dropdown-menu dropdown-menu-right row_actions"]'
    '//a[contains(., \'Console\')]')
XPATH_OPEN_INSTANCE_CONSOLE = (
    '//*[@class="alert alert-info"]'
    '//a[contains(., \'Click here to show only console\')]')
XPATH_VM_ERROR_LOCATOR = (
    '//table[@id="instances"]//tr[contains(., \'vm2\')]'
    '//td[contains(., \'Error\')]')
XPATH_RANGE_CONDITION_HEAT = (
    '//table[@id="provider_networks"]//tr[contains(., \'providernet-b\')]'
    '//td[contains(., \'100-400\')]')
XPATH_GET_VM_COMPUTE = (
    '//*[@id="instances"]/tbody//tr[contains(., \'Heart_beat_disabled\')]'
    '//*[@class="sortable nowrap-col normal_column"]')
XPATH_METADATA_FILTER = '//div[@class="has-feedback"]'
XPATH_PAUSE_UBUNTU = (
    '//table[@id="instances"]//tr[contains(., \'ubuntu-configurable\')]'
    '//td[contains(., \'Paused\')]')
XPATH_ACTIVE_UBUNTU = (
    '//table[@id="instances"]//tr[contains(., \'ubuntu-configurable\')]'
    '//td[contains(., \'Active\')]')
XPATH_ACTION_UBUNTU_CHOOSE = (
    '//table[@id="instances"]//tr[contains(., \'ubuntu-configurable\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
XPATH_ACTION_VM3_PAUSE = (
    '//table[@id="instances"]//tr[contains(., \'centos-configurable\')]'
    '//li[contains(., \'Pause Instance\')]')
XPATH_ACTION_VM3_RESUME = (
    '//table[@id="instances"]//tr[contains(., \'centos-configurable\')]'
    '//li[contains(., \'Resume Instance\')]')
XPATH_ACTION_UBUNTU_RESUME = (
    '//table[@id="instances"]//tr[contains(., \'ubuntu-configurable\')]'
    '//li[contains(., \'Resume Instance\')]')
XPATH_IMG_SPECIFIC_METADATA_CIRROS_ACTION = (
    '//table[@id="images"]//tr[contains(., \'cirros-configurable\')]'
    '//li[contains(., \'Update Metadata\')]')
XPATH_IMAGE_SHARED_POLICY_DELETE_DESC1 = (
    '//*[@class="fa fa-minus"]')
XPATH_IMAGE_SHARED_POLICY_DELETE_DESC2 = (
    '//*[@class="list-group-item ng-scope light-stripe"]'
    '//*[@class="fa fa-minus"]')
XPATH_IMAGE_SHARED_POLICY_SELECT = (
    '//*[@class="input-group input-group-sm ng-scope"]'
    '//option[@label=\'shared\']')
XPATH_IMAGE_SPECIFIC_METADATA_CIRROS = (
    '//table[@id="images"]//tr[contains(., \'cirros-configurable\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')

ADDR_HOST_INVENTORY = '{0}admin/inventory/'.format(HORIZON_URL)

# BUTTONS for static Id's

BUTTON_PROVIDER_NET_TYPE = '//select[@id="id_type"]/option[@value=\'vlan\']'
BUTTON_CREATE_PROVIDER_NET_LAST = '//*[@class="btn btn-primary pull-right"]'
BUTTON_SEGMENTATION_RANGE = (
    '//*[@class="btn data-table-action ajax-modal btn-edit"]')
BUTTON_SEGMENTATION_RANGE_2 = (
    '//*[@class="sortable anchor normal_column"]'
    '//*[contains(., \'providernet-b\')]')
BUTTON_PROJECT_RANGE = (
    '//select[@id="id_tenant_id"]//option[contains(., \'admin\')]')
BUTTON_SEGMENTATION_RANGE_ACCEPT = '//*[@class="btn btn-primary pull-right"]'
BUTTON_CREATE_FLAVOR_ACCEPT = '//*[@value="Create Flavor"]'
BUTTON_UNLOCK_COMPUTE0 = (
    '//table[@id="hostscompute"]//tr[contains(., \'compute-0\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
BUTTON_UNLOCK_COMPUTE0_ACTION = 'hostscompute__row_3__action_unlock'
BUTTON_LOCK_COMPUTE0 = (
    '//table[@id="hostscompute"]//tr[contains(., \'compute-0\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
BUTTON_LOCK_COMPUTE0_ACTION = 'hostscompute__row_3__action_lock'
XPATH_COMPUTE_0_LOCKED = (
    '//table[@id="hostscompute"]//tr[contains(., \'compute-0\')]'
    '//td[contains(., \'Locked\')]')
XPATH_COMPUTE_0_STATE = (
    '//table[@id="hostscompute"]//tr[contains(., \'compute-0\')]'
    '//td[contains(., \'Available\')]')
BUTTON_CTRL_ALT_DEL = '//*[@id="sendCtrlAltDelButton"]'
BUTTON_RANGE_HEAT = (
    '//table[@id="provider_networks"]//tr[contains(., \'providernet-b\')]'
    '//*[@class="btn btn-default btn-sm dropdown-toggle"]')
BUTTON_RANGE_CREATE = (
    '//*[@class="table_actions clearfix"]//*[contains(., \'Create Range\')]')
BUTTON_SECOND_FLAVOR = (
    '//tr[contains(., \'m2.sanity\')]//*[@class="btn btn-sm btn-default"]')
BUTTON_IMAGE_UPDATE_METADATA = (
    '//table[@class="table table-striped table-rsp table-detail modern'
    ' ng-scope"]//tr[contains(., \'cirros_sharedpolicy\')]'
    '//*[@class="btn btn-default"]')
BUTTON_CIRROS_FLV_HEARTBEAT_ARROW = (
    '//tr[contains(., \'cirros-heartbeat\')]//*[@class="btn btn-sm '
    'btn-default"]')

# ADDR field for specific uses in go to function

ADDR_PROVIDERNETS_PATH = '{0}admin/providernets/'.format(HORIZON_URL)
ADDR_HOST_COMPUTE_DETAIL_0 = (
    '{0}admin/inventory/3/detail/'.format(HORIZON_URL))
ADDR_HOST_COMPUTE_DETAIL_1 = (
    '{0}admin/inventory/2/detail/'.format(HORIZON_URL))
ADDR_ADMIN_FLAVORS = '{0}admin/flavors/'.format(HORIZON_URL)
ADDR_ADMIN_IMAGES = '{0}admin/images/'.format(HORIZON_URL)
ADDR_PROJECT_NETWORK = '{0}project/networks/'.format(HORIZON_URL)
ADDR_PROJECT_INSTANCES = '{0}project/instances/'.format(HORIZON_URL)
ADDR_ADMIN_INSTANCES = '{0}admin/instances/'.format(HORIZON_URL)

# EDIT text parameters for special fields

EDIT_NOVA_LOCAL_PARAMETERS = (
    '//*[@class="sortable anchor normal_column"]'
    '//a[contains(., \'nova-local\')]')
EDIT_LOCAL_VOLUME_GROUP_PARAMETER = (
    '//select[@id="id_instance_backing"]'
    '/option[contains(., \'Local RAW LVM backed\')]')
PROGRESS_BAR = '//*[@class="progress-text horizon-loading-bar"]'
LOADING_ICON = '//*[@class="modal loading in"]'

# CSS Selectors for specific cases

CSS_CTRL_ALT_DEL = 'sendCtrlAltDelButton'

# CLI Variables

VM_SET_ERROR_FLAG = 'openstack server set --state error'
NOVA_ACTION_SET_ERROR_FLAG2 = (
    'openstack server set --state error vm-cirros-configurable-0')
VM_SET_ACTIVE_FLAG = 'openstack server set --state active'
SUSPEND_INSTANCE = 'openstack server suspend vm-cirros-configurable-0'
RESUME_INSTANCE = 'openstack server resume vm-cirros-configurable-0'
CEILOMETER_IMAGE_COMMAND = 'ceilometer statistics -m image.size'
