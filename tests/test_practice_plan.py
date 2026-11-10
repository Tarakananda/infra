from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_practice_plan import check_plan


def fixture():
    values = {
        'aws_eks_cluster': {'name': 'pharma-dev-cluster', 'version': '1.36', 'upgrade_policy': [{'support_type': 'STANDARD'}]},
        'aws_eks_node_group': {'instance_types': ['m7i-flex.large'], 'capacity_type': 'ON_DEMAND',
                               'scaling_config': [{'desired_size': 1, 'min_size': 1, 'max_size': 1}],
                               'update_config': [{'update_strategy': 'MINIMAL', 'max_unavailable': 1}]},
        'aws_launch_template': {'credit_specification': [],
                                'block_device_mappings': [{'ebs': [{'volume_size': 20, 'volume_type': 'gp3'}]}]},
        'aws_db_instance': {'identifier': 'pharma-dev-postgres', 'instance_class': 'db.t3.micro', 'multi_az': False,
                            'allocated_storage': 20, 'max_allocated_storage': 0, 'storage_type': 'gp3',
                            'backup_retention_period': 1, 'publicly_accessible': False},
        'aws_nat_gateway': {}, 'aws_eip': {}, 'aws_vpc_endpoint': {'vpc_endpoint_type': 'Gateway'},
    }
    return {'configuration': {'provider_config': {'aws': {'expressions': {'region': {'constant_value': 'ap-south-1'}}}}},
            'planned_values': {'root_module': {'child_modules': [{'resources': [
                {'type': kind, 'mode': 'managed', 'values': value} for kind, value in values.items()]}]}}}


class PracticePlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = fixture()
        self.items = self.plan['planned_values']['root_module']['child_modules'][0]['resources']

    def check(self, today=date(2026, 11, 8)):
        return check_plan(self.plan, today=today)

    def values(self, kind):
        return next(r['values'] for r in self.items if r['type'] == kind)

    def test_reviewed_profile_passes(self):
        self.assertEqual(self.check(), [])

    def test_extended_support_is_rejected(self):
        self.values('aws_eks_cluster')['upgrade_policy'] = [{'support_type': 'EXTENDED'}]
        self.assertTrue(self.check())

    def test_support_expiry_requires_review(self):
        self.assertTrue(self.check(date(2027, 8, 2)))

    def test_extra_worker_capacity_is_rejected(self):
        self.values('aws_eks_node_group')['scaling_config'][0]['max_size'] = 4
        self.assertTrue(self.check())

    def test_incompatible_cpu_credit_settings_are_rejected(self):
        self.values('aws_launch_template')['credit_specification'] = [{'cpu_credits': 'unlimited'}]
        self.assertTrue(self.check())

    def test_multiple_nat_gateways_are_rejected(self):
        self.items.append({'type': 'aws_nat_gateway', 'mode': 'managed', 'values': {}})
        self.assertTrue(self.check())

    def test_multi_az_database_is_rejected(self):
        self.values('aws_db_instance')['multi_az'] = True
        self.assertTrue(self.check())

    def test_rds_storage_autoscaling_is_rejected(self):
        self.values('aws_db_instance')['max_allocated_storage'] = 1000
        self.assertTrue(self.check())

    def test_paid_interface_endpoint_is_rejected(self):
        self.values('aws_vpc_endpoint')['vpc_endpoint_type'] = 'Interface'
        self.assertTrue(self.check())

    def test_load_balancer_is_rejected(self):
        self.items.append({'type': 'aws_lb', 'mode': 'managed', 'values': {}})
        self.assertTrue(self.check())

    def test_replacement_requires_review(self):
        self.plan['resource_changes'] = [{'type': 'aws_eks_node_group', 'address': 'module.eks.nodes',
                                          'change': {'actions': ['create', 'delete']}}]
        self.assertTrue(self.check())

    def test_recreated_old_cluster_cannot_skip_minor_upgrades(self):
        self.plan['resource_changes'] = [{'type': 'aws_eks_cluster', 'address': 'module.eks.cluster',
                                          'change': {'actions': ['update'], 'before': {'version': '1.33'},
                                                     'after': {'version': '1.36'}}}]
        self.assertTrue(self.check())

    def test_other_environment_or_region_is_rejected(self):
        self.values('aws_eks_cluster')['name'] = 'pharma-prod-cluster'
        self.plan['configuration']['provider_config']['aws']['expressions']['region']['constant_value'] = 'ap-south-1'
        self.assertGreaterEqual(len(self.check()), 2)

    def test_empty_plan_is_not_treated_as_in_budget(self):
        self.plan['planned_values'] = {}
        self.assertTrue(self.check())

    def test_datasources_do_not_count_as_billable_resources(self):
        data = deepcopy(self.items[0])
        data['mode'] = 'data'
        self.items.append(data)
        self.assertEqual(self.check(), [])
