"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from widgetastic.utils import partial_match
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream('5.8', '5.9')]


@pytest.fixture
def vm_list():
    # TODO: Remove vm_list hardcoding with pr7327's solution
    return ['ytale-v2v-ubuntu1']


@pytest.fixture
def infra_map(appliance):
    # TODO: kk is going to convert this hardcoding code to .yaml
    form_data = {
        'general':
            {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': fauxfactory.gen_string("alphanumeric", length=50)
            },
        'cluster':
            {
                'mappings': [
                    {
                        'sources': ['Datacenter \ Cluster'],
                        'target': ['Default \ Default']
                    }
                ]
            },
        'datastore':
            {
                'Cluster (Default)': {
                    'mappings': [
                        {
                            'sources': [partial_match('NFS_Datastore_1')],
                            'target': [partial_match('hosted_storage')]
                        },
                        {
                            'sources': [partial_match('h01-Local_Datastore-8GB')],
                            'target': [partial_match('env-rhv41-01-nfs-data')]
                        }
                    ]
                }
            },
        'network':
            {
                'Cluster (Default)': {
                    'mappings': [
                        {
                            'sources': ['VM Network', 'VMkernel'],
                            'target': ['ovirtmgmt']

                        },
                        {
                            'sources': ['DPortGroup'],
                            'target': ['Storage - VLAN 33']
                        }
                    ]
                }
            }
    }

    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    add_infrastucture_mapping = infrastructure_mapping_collection.create(form_data)
    return add_infrastucture_mapping


@pytest.mark.tier(0)
def test_compute_migration_modal(appliance):
    """Test takes an appliance and tries to navigate to migration page and open mapping wizard.

    This is a dummy test just to check navigation.
    # TODO : Replace this test with actual test.
    """
    infra_mapping_collection = appliance.collections.v2v_mappings
    view = navigate_to(infra_mapping_collection, 'All')
    assert view.is_displayed
    view = navigate_to(infra_mapping_collection, 'Add')
    assert view.is_displayed


@pytest.mark.parametrize('migration_flag', [True, False], ids=['start_migration', 'save_migration'])
@pytest.mark.parametrize('method', ['via_csv', 'via_discovery'])
def test_migration_plan_modal(appliance, infra_map, vm_list, method, migration_flag):
    if method == 'csv':
        csv_import = True
    else:
        csv_import = False
    coll = appliance.collections.v2v_plans
    coll.create(name="plan_{}".format(fauxfactory.gen_alphanumeric()),
                description="desc_{}".format(fauxfactory.gen_alphanumeric()),
                infra_map=infra_map.name,
                vm_names=vm_list,
                csv_import=csv_import,
                start_migration=migration_flag)
