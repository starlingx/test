from utils.horizon.pages.project.compute import instancespage


class InstancesPage(instancespage.InstancesPage):
    PARTIAL_URL = 'admin/instances'
    pass
