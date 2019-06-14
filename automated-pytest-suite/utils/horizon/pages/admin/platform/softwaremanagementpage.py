from utils.horizon.pages import basepage
from utils.horizon.regions import tables
from utils.horizon.regions import forms


class PatchesTable(tables.TableRegion):
    name = "patches"

    UPLOAD_PATCHES_FORM_FIELDS = ("patch_files",)

    @tables.bind_table_action('patchupload')
    def upload_patches(self, upload_button):
        upload_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.form_fields)


class PatchStagesTable(tables.TableRegion):
    name = "patchstages"

    CREATE_STRATEGY_FORM_FIELDS = ("controller_apply_type", "compute_apply_type",
                                   "default_instance_action", "alarm_restrictions")

    @tables.bind_table_action('createpatchstrategy')
    def create_strategy(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.CREATE_STRATEGY_FORM_FIELDS)

    @tables.bind_table_action('delete_patch_strategy')
    def delete_strategy(self, delete_button):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)


class UpgradeStagesTable(PatchStagesTable):
    name = "upgradestages"

    CREATE_STRATEGY_FORM_FIELDS = ("compute_apply_type", "alarm_restrictions")


class SoftwareManagementPage(basepage.BasePage):

    PARTIAL_URL = 'admin/software_management'
    PATCHES_TAB_INDEX = 0
    PATCH_ORCHESTRATION_TAB_INDEX = 1
    UPGRADE_ORCHESTRATION_TAB_INDEX = 2

    @property
    def patches_table(self):
        return PatchesTable(self.driver)

    @property
    def patch_stages_table(self):
        return PatchStagesTable(self.driver)

    @property
    def upgrade_stages_table(self):
        return UpgradeStagesTable(self.driver)

    def create_patch_strategy(self, controller_apply_type=None,
                              compute_apply_type=None,
                              default_instance_action=None,
                              alarm_restrictions=None):
        create_strategy_form = self.patch_stages_table.create_strategy()
        if controller_apply_type is not None:
            create_strategy_form.controller_apply_type.text = controller_apply_type
        if compute_apply_type is not None:
            create_strategy_form.compute_apply_type.text = compute_apply_type
        if default_instance_action is not None:
            create_strategy_form.default_instance_action.text = default_instance_action
        if alarm_restrictions is not None:
            create_strategy_form.alarm_restrictions.text = alarm_restrictions
            create_strategy_form.submit()

    def delete_patch_strategy(self):
        confirm_form = self.patch_stages_table.delete_strategy()
        confirm_form.submit()

    def create_upgrade_strategy(self, compute_apply_type=None, alarm_restrictions=None):
        create_strategy_form = self.upgrade_stages_table.create_strategy()
        if compute_apply_type is not None:
            create_strategy_form.compute_apply_type.text = compute_apply_type
        if alarm_restrictions is not None:
            create_strategy_form.alarm_restrictions.text = alarm_restrictions
            create_strategy_form.submit()

    def delete_upgrade_strategy(self):
        confirm_form = self.upgrade_stages_table.delete_strategy()
        confirm_form.submit()

    def go_to_patches_tab(self):
        self.go_to_tab(self.PATCHES_TAB_INDEX)

    def go_to_patch_orchestration_tab(self):
        self.go_to_tab(self.PATCH_ORCHESTRATION_TAB_INDEX)

    def go_to_upgrade_orchestration_tab(self):
        self.go_to_tab(self.UPGRADE_ORCHESTRATION_TAB_INDEX)
