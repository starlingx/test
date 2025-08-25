import redfish

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword


class BiosKeywords(BaseKeyword):
    """Keywords for BIOS operations using Redfish API."""

    def __init__(self, bmc_ip: str, username: str, password: str):
        """Initialize Redfish client for Bios keywords.

        Args:
            bmc_ip (str): BMC IP address.
            username (str): Username for authentication.
            password (str): Password for authentication.
        """
        self.bmc_ip = bmc_ip
        self.username = username
        self.password = password
        self.system_id = None
        self.vendor  = None
        self.model  = None

        self.redfish_client = redfish.redfish_client(
            base_url=f"https://{self.bmc_ip}",
            username=self.username,
            password=self.password,
            timeout=30,
            default_prefix="/redfish/v1"
        )
        self.redfish_client.login(auth='session')
        self.discover_system_info()

    def discover_system_info(self):
        """Discover system ID from Redfish API."""
        # Detect system ID
        systems_resp = self.redfish_client.get("/redfish/v1/Systems")

        if systems_resp.status != 200:
            raise Exception(f"Failed to get systems: {systems_resp.status}")

        members = systems_resp.dict.get("Members", [])
        if not members:
            raise Exception("No system members found in Redfish response")
        self.system_id = list(members[0].values())[0]  # e.g. /redfish/v1/Systems/System.Embedded.1

        # Get system details
        sys_info = self.get_system_info()
        self.vendor = sys_info.get("Manufacturer", "Unknown")
        self.model = sys_info.get("Model", "Unknown")

        get_logger().log_info(f"Connected to {self.vendor} {self.model}, System ID: {self.system_id}")

    def get_system_info(self):
        """Fetch system information"""
        if not self.system_id:
            raise Exception("Not connected to system")

        resp = self.redfish_client.get(self.system_id)
        if resp.status == 200:
            # get_logger().log_info(f"system_info {resp.dict}")
            return resp.dict
        else:
            raise Exception(f"Failed to fetch system info: {resp.status}")

    def get_boot_order(self):
        """Fetch current boot order and override settings"""
        if not self.system_id:
            raise Exception("Not connected to system")

        resp = self.redfish_client.get(self.system_id)
        if resp.status == 200:
            return  resp.dict.get("Boot", {})
        else:
            raise Exception(f"Failed to fetch system info: {resp.status}")

        return self.boot_order

    def set_boot_order(self, device="Pxe", enabled="Once"):
        """Set boot order (override target device).

        :param device (str): Boot device (e.g., "Pxe", "Hdd", "Cd", "Usb", "BiosSetup")
        :param enabled (str): Boot override enabled mode ("Once", "Continuous", "Disabled")
        """
        if not self.system_id:
            raise Exception("Not connected to system")

        payload = {
            "Boot": {
                "BootSourceOverrideTarget": device,
                "BootSourceOverrideEnabled": enabled
            }
        }

        resp = self.redfish_client.patch(self.system_id, body=payload)

        if resp.status in [200, 204]:
            get_logger().log_info(f"Boot device set to {device}, mode={enabled}")
        else:
            raise Exception(f"Failed to set boot order: {resp.status}, {resp.text}")