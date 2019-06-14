from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import menus
from utils.horizon.regions import tables

# name link
# view usage
# edit_quotas


class ProjectsTable(tables.TableRegion):
    name = 'tenants'

    MODIFY_PROJECT_FORM_FIELDS = (
        ("domain_id", "domain_name", "name", "description", "enabled"),
        {'members': menus.MembershipMenuRegion},
        {'groups': menus.MembershipMenuRegion},
        ("metadata_items", "cores", "instances",
         "injected_files", "injected_file_content_bytes",
         "key_pairs", "injected_file_path_bytes", "volumes",
         "snapshots", "gigabytes", "ram", "security_group",
         "security_group_rule",
         "floatingip", "network", "port", "router", "subnet"),
        ("mac_filtering",))

    @tables.bind_table_action('create')
    def create_project(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.MODIFY_PROJECT_FORM_FIELDS,
                                      default_tab=0)

    @tables.bind_row_action('users')
    def manage_members(self, manage_button, row):
        manage_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.MODIFY_PROJECT_FORM_FIELDS,
                                      default_tab=1)

    @tables.bind_row_action('groups')
    def modify_groups(self, modify_button, row):
        modify_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.MODIFY_PROJECT_FORM_FIELDS,
                                      default_tab=2)

    @tables.bind_row_action('update')
    def edit_project(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.MODIFY_PROJECT_FORM_FIELDS,
                                      default_tab=3)

    @tables.bind_row_action('quotas')
    def modify_quotas(self, modify_button, row):
        modify_button.click()
        self.wait_till_spinner_disappears()
        return forms.TabbedFormRegion(self.driver,
                                      field_mappings=self.MODIFY_PROJECT_FORM_FIELDS,
                                      default_tab=3)

    @tables.bind_table_action('delete')
    def delete_project(self, delete_button):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('delete')
    def delete_project_by_row(self, delete_button, row):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)


class ProjectsPage(basepage.BasePage):

    PARTIAL_URL = 'identity'
    PROJECTS_TABLE_NAME_COLUMN = 'Name'

    @property
    def projects_table(self):
        return ProjectsTable(self.driver)

    def _get_row_with_project_name(self, name):
        return self.projects_table.get_row(
            self.PROJECTS_TABLE_NAME_COLUMN, name)

    def is_project_present(self, project_name):
        return bool(self._get_row_with_project_name(project_name))

    def get_project_info(self, project_name, header):
        row = self._get_row_with_project_name(project_name)
        return row.cells[header].text

    def create_project(self, project_name, description=None, is_enabled=None):
        create_project_form = self.projects_table.create_project()
        create_project_form.name.text = project_name
        if description is not None:
            create_project_form.description.text = description
        if is_enabled is True:
            create_project_form.enabled.mark()
        if is_enabled is False:
            create_project_form.enabled.unmark()
        create_project_form.submit()

    def delete_project(self, project_name):
        row = self._get_row_with_project_name(project_name)
        row.mark()
        modal_confirmation_form = self.projects_table.delete_project()
        modal_confirmation_form.submit()

    def delete_project_by_row(self, project_name):
        row = self._get_row_with_project_name(project_name)
        confirm_form = self.projects_table.delete_project_by_row(row)
        confirm_form.submit()

    def manage_members(self, project_name, users2allocate=None, members2deallocate=None):
        row = self._get_row_with_project_name(project_name)
        members_form = self.projects_table.manage_members(row)
        if users2allocate is not None:
            for user in users2allocate:
                members_form.members.allocate_member(user)
        if members2deallocate is not None:
            for member in members2deallocate:
                members_form.members.deallocate_member(member)
        members_form.submit()

    def manage_member_roles(self, project_name, member_name=None,
                            roles2allocate=None, roles2deallocate=None):
        row = self._get_row_with_project_name(project_name)
        members_form = self.projects_table.manage_members(row)
        if member_name is not None:
            if roles2allocate is not None:
                for role in roles2allocate:
                    members_form.members.allocate_member_roles(member_name, role)
            if roles2deallocate is not None:
                for role in roles2deallocate:
                    members_form.members.deallocate_member_roles(member_name, role)
        members_form.submit()

    def modify_groups(self, project_name, groups2allocate=None, groups2deallocate=None):
        row = self._get_row_with_project_name(project_name)
        groups_form = self.projects_table.modify_groups(row)
        if groups2allocate is not None:
            for group in groups2allocate:
                groups_form.groups.allocate_member(group)
        if groups2deallocate is not None:
            for group in groups2deallocate:
                groups_form.groups.deallocate_member(group)
        groups_form.submit()

    def modify_group_roles(self, project_name, group_name=None,
                           roles2allocate=None, roles2deallocate=None):
        row = self._get_row_with_project_name(project_name)
        groups_form = self.projects_table.modify_groups(row)
        if group_name is not None:
            if roles2allocate is not None:
                for role in roles2allocate:
                    groups_form.groups.allocate_member_roles(group_name, role)
            if roles2deallocate is not None:
                for role in roles2deallocate:
                    groups_form.groups.deallocate_member_roles(group_name, role)
        groups_form.submit()

    def get_member_roles_at_project(self, project_name, member_name):
        row = self._get_row_with_project_name(project_name)
        members_form = self.projects_table.manage_members(row)
        roles = members_form.members.get_member_allocated_roles(member_name)
        members_form.cancel()
        return set(roles)

    def get_group_roles_at_project(self, project_name, group_name):
        row = self._get_row_with_project_name(project_name)
        groups_form = self.projects_table.modify_groups(row)
        roles = groups_form.groups.get_member_allocated_roles(group_name)
        groups_form.cancel()
        return set(roles)

    def modify_quotas(self, project_name, metadata_items=None, vcpus=None, instances=None,
                      injected_files=None, injected_file_content=None, key_pairs=None,
                      length_of_injected_file_path=None, volumes=None, volume_snapshots=None,
                      total_size_of_volumes_and_snapshots=None, ram=None, security_groups=None,
                      security_group_rules=None, floating_ips=None, networks=None,
                      ports=None, routers=None, subnets=None):
        row = self._get_row_with_project_name(project_name)
        quotas_form = self.projects_table.modify_quotas(row)
        if metadata_items is not None:
            quotas_form.metadata_items.value = metadata_items
        if vcpus is not None:
            quotas_form.cores.value = vcpus
        if instances is not None:
            quotas_form.instances.value = instances
        if injected_files is not None:
            quotas_form.injected_files.value = injected_files
        if injected_file_content is not None:
            quotas_form.injected_file_content_bytes.value = injected_file_content
        if key_pairs is not None:
            quotas_form.key_pairs.value = key_pairs
        if length_of_injected_file_path is not None:
            quotas_form.injected_file_path_bytes.value = length_of_injected_file_path
        if volumes is not None:
            quotas_form.volumes.value = volumes
        if volume_snapshots is not None:
            quotas_form.snapshots.value = volume_snapshots
        if total_size_of_volumes_and_snapshots is not None:
            quotas_form.gigabytes.value = total_size_of_volumes_and_snapshots
        if ram is not None:
            quotas_form.ram.value = ram
        if security_groups is not None:
            quotas_form.security_group.value = security_groups
        if security_group_rules is not None:
            quotas_form.security_group_rule.value = security_group_rules
        if floating_ips is not None:
            quotas_form.floatingip.value = floating_ips
        if networks is not None:
            quotas_form.network.value = networks
        if ports is not None:
            quotas_form.port.value = ports
        if routers is not None:
            quotas_form.router.value = routers
        if subnets is not None:
            quotas_form.subnet.value = subnets
