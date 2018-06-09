import attr
import csv

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Checkbox, View
from widgetastic_manageiq import (InfraMappingTreeView, MultiSelectList, RadioGroup,
                                  Table, HiddenFileInput, MigrationDropdown, MigrationPlansList)
from widgetastic_patternfly import Text, TextInput, Button, BootstrapSelect

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.wait import wait_for

# Views


class InfraMappingFormControlButtons(View):
    # common footer buttons for first 3 pages
    back_btn = Button('Back')
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')


class InfraMappingWizardCommon(View):

    add_mapping = Button('Add Mapping')
    remove_mapping = Button('Remove Selected')
    remove_all_mappings = Button('Remove All')
    mappings_tree = InfraMappingTreeView(tree_class='treeview')


class InfraMappingWizardGeneralView(View):
    name = TextInput(name='name')
    description = TextInput(name='description')
    include_buttons = View.include(InfraMappingFormControlButtons)

    def after_fill(self, was_change):
        if was_change:
            self.next_btn.click()


class InfraMappingWizardClustersView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_clusters = MultiSelectList('source_clusters')
    target_clusters = MultiSelectList('target_clusters')

    def fill(self, values):
        """Use to add all mappings specified in values.

        Args:
            values:
                format as following:
                    {
                       'mappings': [
                            {
                                'sources':['item1', 'item2'],
                                'target':['item_target']
                            }
                       ]
                       ...
                    }
        """
        source_clusters_filled = []
        target_clusters_filled = []
        for mapping in values['mappings']:
            source_clusters_filled.append(self.source_clusters.fill(mapping['sources']))
            target_clusters_filled.append(self.target_clusters.fill(mapping['target']))
            self.add_mapping.click()
        was_change = any(source_clusters_filled) and any(target_clusters_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardDatastoresView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_datastores = MultiSelectList('source_datastores')
    target_datastores = MultiSelectList('target_datastores')
    cluster_selector = BootstrapSelect(id='cluster_select')

    def fill(self, values):
        """Use to add all mappings specified in values.

        Args:
            values:
                format as following:
                    {
                        'cluster_name': {
                            'mappings': [
                                {
                                    'sources':['item1','item2'],
                                    'target':['item_target']
                                },
                                ...
                            ]
                        },
                        ...
                    }
        """
        source_datastores_filled = []
        target_datastores_filled = []
        for cluster in values:
            self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                source_datastores_filled.append(self.source_datastores.fill(mapping['sources']))
                target_datastores_filled.append(self.target_datastores.fill(mapping['target']))
                self.add_mapping.click()
        was_change = any(source_datastores_filled) and any(target_datastores_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardNetworksView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_networks = MultiSelectList('source_networks')
    target_networks = MultiSelectList('target_networks')
    next_btn = Button("Create")  # overriding, since 'Next' is called 'Create' in this form
    cluster_selector = BootstrapSelect(id='cluster_select')

    def fill(self, values):
        """Use to add all mappings specified in values.

        Args:
            values:
                format as following:
                    {
                        'cluster_name': {
                            'mappings': [
                                {
                                    'sources':['item1','item2'],
                                    'target':['item_target']
                                },
                                ...
                            ]
                        },
                        ...
                    }
        """
        source_networks_filled = []
        target_networks_filled = []
        for cluster in values:
            self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                source_networks_filled.append(self.source_networks.fill(mapping['sources']))
                target_networks_filled.append(self.target_networks.fill(mapping['target']))
                self.add_mapping.click()
        was_change = any(source_networks_filled) and any(target_networks_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardResultsView(View):
    close_btn = Button("Close")
    continue_to_plan_wizard_btn = Button("Continue to the plan wizard")


class InfraMappingWizard(View):
    """Infrastructure Mapping Wizard Modal Widget.

    Usage:
        fill: takes values of following format:
            {
                'general':
                    {
                        'name':'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                        'description':fauxfactory.gen_string("alphanumeric",length=50)
                    },
                'cluster':
                    {
                        'mappings': [
                            {
                                'sources':['Datacenter \ Cluster'],
                                'target':['Default \ Default']
                            }
                        ]
                    },
                'datastore':{
                    'Cluster (Default)': {
                       'mappings':[
                            {
                                'sources':['NFS_Datastore_1','iSCSI_Datastore_1'],
                                'target':['hosted_storage']
                            },
                            {
                                'sources':['h02-Local_Datastore-8GB', 'h01-Local_Datastore-8GB'],
                                'target':['env-rhv41-01-nfs-iso']
                            }
                        ]
                   }
                },
                'network':{
                    'Cluster (Default)': {
                        'mappings': [
                            {
                                'sources':['VM Network','VMkernel'],
                                'target':['ovirtmgmt']
                            },
                            {
                                'sources':['DPortGroup'],
                                'target':['Storage VLAN 33']
                            }
                        ]
                    }
                }
            }
    """

    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    general = View.nested(InfraMappingWizardGeneralView)
    cluster = View.nested(InfraMappingWizardClustersView)
    datastore = View.nested(InfraMappingWizardDatastoresView)
    network = View.nested(InfraMappingWizardNetworksView)
    result = View.nested(InfraMappingWizardResultsView)

    def after_fill(self, was_change):
        if was_change:
            self.result.close_btn.click()


class MigrationDashboardView(BaseLoggedInPage):
    create_infrastructure_mapping = Text(locator='(//a|//button)'
                                                 '[text()="Create Infrastructure Mapping"]')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')
    migr_dropdown = MigrationDropdown(text="Migration Plans Not Started")
    migration_plans_not_started_list = MigrationPlansList("plans-not-started-list")
    migration_plans_completed_list = MigrationPlansList("plans-complete-list")

    # TODO: declare list widget and in-progress widget

    @View.nested
    class plan_not_started(View):
        # TODO: kk is going to add this widget
        """
            In test we can access it as,
                view.migr_dropdown.item_select("Migration Plans Not Started")
                view.plan_not_started.widget.widget_method()
        """
        pass

    @View.nested
    class plan_in_progress(View):
        # TODO: in-progress widget
        """
            In test we can access it as,
                view.migr_dropdown.item_select("Migration Plans in Progress")
                view.plan_in_progress.widget.widget_method()
        """
        pass

    @View.nested
    class plan_completed(View):
        # TODO: kk is going to add this widget
        """
            In test we can access it as,
                view.migr_dropdown.item_select("Migration Plans Completed")
                view.plan_completed.widget.widget_method()
        """
        pass

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Migration']


class AddInfrastructureMappingView(View):
    form = InfraMappingWizard()

    @property
    def is_displayed(self):
        return self.form.title.text == 'Infrastructure Mapping Wizard'


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name='name')
    description = TextInput(name='description')
    back_btn = Button('Back')
    # Since next is a keyword, suffixing it with btn and other two
    # because want to keep it consistent
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')

    @View.nested
    class general(View):
        infra_map = BootstrapSelect('infrastructure_mapping')
        name = TextInput(name='name')
        description = TextInput(name='description')
        select_vm = RadioGroup('.//*[contains(@id,"vm_choice_radio")]')

    @View.nested
    class vms(View):
        import_btn = Button('Import')
        importcsv = Button('Import CSV')
        hidden_field = HiddenFileInput(locator='.//*[contains(@accept,".csv")]')
        table = Table('.//*[contains(@class, "container-fluid")]/table',
                      column_widgets={"Select": Checkbox(locator=".//input")})

    @View.nested
    class options(View):
        create_btn = Button('Create')
        run_migration = RadioGroup('.//*[contains(@id,"migration_plan_choice_radio")]')

    @View.nested
    class results(View):
        close_btn = Button('Close')
        msg = Text('.//*[contains(@id,"migration-plan-results-message")]')

    @property
    def is_displayed(self):
        return self.title.text == 'Migration Plan Wizard'

# Collections Entities


@attr.s
class InfrastructureMapping(BaseEntity):
    """Class representing v2v infrastructure mappings"""
    name = attr.ib()
    description = attr.ib(default=None)
    form_data = attr.ib(default=None)


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""
    ENTITY = InfrastructureMapping

    def create(self, form_data):
        infra_map = self.instantiate(
            name=form_data['general']['name'],
            description=form_data['general'].get('description', ''),
            form_data=form_data
        )
        view = navigate_to(self, 'Add')
        view.form.fill(form_data)
        return infra_map


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v migration plan"""
    name = attr.ib()


@attr.s
class MigrationPlanCollection(BaseCollection):
    """Collection object for migration plan object"""
    ENTITY = MigrationPlan

    def create(self, name, infra_map, vm_names, description=None, csv_import=False,
               start_migration=False):
        """Create new migration plan in UI
        Args:
            name: (string) plan name
            description: (string) plan description
            infra_map: (object) infra map object name
            vm_names: (list) vm names
            csv_import: (bool) flag for importing vms
            start_migration: (bool) flag for start migration
        """
        view = navigate_to(self, 'Add')
        import time
        time.sleep(2)
        view.general.fill({
            'infra_map': infra_map,
            'name': name,
            'description': description
        })

        if csv_import:
            view.general.select_vm.select("Import a CSV file with a list of VMs to be migrated")
            view.next_btn.click()
            with open('v2v_vms.csv', 'w') as file:
                headers = ['Name', 'Provider']
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                for vm in vm_names:
                    writer.writerow({'Name': vm.name, 'Provider': vm.provider.name})
            file.close()
            view.vms.hidden_field.fill('v2v_vms.csv')
        else:
            view.next_btn.click()
        wait_for(lambda: view.vms.table.is_displayed, timeout=60, message='Wait for VMs view',
                 delay=2)

        for row in view.vms.table.rows():
            if row['VM Name'].read() in vm_names:
                row['Select'].fill(True)
        view.next_btn.click()

        if start_migration:
            view.options.run_migration.select("Start migration immediately")
        view.options.create_btn.click()
        wait_for(lambda: view.results.msg.is_displayed, timeout=60, message='Wait for Results view')

        if start_migration:
            base_flash = "Migration Plan: '{}' is in progress".format(name)
        else:
            base_flash = "Migration Plan: '{}' has been saved".format(name)
        assert view.results.msg.read() == base_flash
        view.results.close_btn.click()
        return self.instantiate(name)

# Navigations


@navigator.register(InfrastructureMappingCollection, 'All')
@navigator.register(MigrationPlanCollection, 'All')
class All(CFMENavigateStep):
    VIEW = MigrationDashboardView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Migration')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(InfrastructureMappingCollection, 'Add')
class AddInfrastructureMapping(CFMENavigateStep):
    VIEW = AddInfrastructureMappingView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_infrastructure_mapping.click()


@navigator.register(MigrationPlanCollection, 'Add')
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_migration_plan.click()
