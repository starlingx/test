from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class HorizonDCOrchestrationPageLocators:
    """
    Page Elements class that contains elements for the DC Admin Orchestration Page.
    """

    def get_locator_strategy_detail(self) -> WebLocator:
        """
        Locator for the strategy detail section.

        Returns: WebLocator
        """
        return WebLocator("#cloud-strategy-detail", By.CSS_SELECTOR)

    def get_locator_create_strategy_button(self) -> WebLocator:
        """
        Locator for the Create Strategy button.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps__action_createcloudstrategy", By.CSS_SELECTOR)

    def get_locator_apply_strategy_button(self) -> WebLocator:
        """
        Locator for the Apply Strategy button.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps__action_apply_cloud_patch_strategy", By.CSS_SELECTOR)

    def get_locator_abort_strategy_button(self) -> WebLocator:
        """
        Locator for the Abort Strategy button.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps__action_abort_cloud_patch_strategy", By.CSS_SELECTOR)

    def get_locator_delete_strategy_button(self) -> WebLocator:
        """
        Locator for the Delete Strategy button.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps__action_delete_patch_strategy", By.CSS_SELECTOR)

    def get_locator_strategy_type_select(self) -> WebLocator:
        """
        Locator for the Strategy Type dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_type", By.CSS_SELECTOR)

    def get_locator_to_version_select(self) -> WebLocator:
        """
        Locator for the To Version dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_to_version", By.CSS_SELECTOR)

    def get_locator_apply_to_select(self) -> WebLocator:
        """
        Locator for the Apply To dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_target", By.CSS_SELECTOR)

    def get_locator_subcloud_select(self) -> WebLocator:
        """
        Locator for the Subcloud dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_cloud_name", By.CSS_SELECTOR)

    def get_locator_subcloud_group_select(self) -> WebLocator:
        """
        Locator for the Subcloud Group dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_subcloud_group", By.CSS_SELECTOR)

    def get_locator_stop_on_failure_checkbox(self) -> WebLocator:
        """
        Locator for the Stop on Failure checkbox in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_stop_on_failure", By.CSS_SELECTOR)

    def get_locator_subcloud_apply_type_select(self) -> WebLocator:
        """
        Locator for the Subcloud Apply Type dropdown in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_subcloud_apply_type", By.CSS_SELECTOR)

    def get_locator_max_parallel_subclouds_input(self) -> WebLocator:
        """
        Locator for the Maximum Parallel Subclouds input in the Create Strategy modal.

        Returns: WebLocator
        """
        return WebLocator("#id_max_parallel_subclouds", By.CSS_SELECTOR)

    def get_locator_modal_submit_button(self) -> WebLocator:
        """
        Locator for the submit button in the modal dialog.

        Returns: WebLocator
        """
        return WebLocator(".modal-footer .btn:not(.cancel)", By.CSS_SELECTOR)

    def get_locator_modal_delete_confirm_button(self) -> WebLocator:
        """
        Locator for the delete confirmation button in the modal dialog.

        Returns: WebLocator
        """
        return WebLocator(".modal-footer .btn-danger", By.CSS_SELECTOR)

    def get_locator_steps_table(self) -> WebLocator:
        """
        Locator for the orchestration steps table.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps", By.CSS_SELECTOR)

    def get_locator_steps_table_rows(self) -> WebLocator:
        """
        Locator for the non-empty rows in the orchestration steps table.

        Returns: WebLocator
        """
        return WebLocator("#cloudpatchsteps tbody tr:not(.empty)", By.CSS_SELECTOR)
