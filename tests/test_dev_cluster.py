import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dev_cluster


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = str(Path(self.directory.name) / 'config')
        self.cluster = {'name': 'pharma-dev-cluster', 'status': 'ACTIVE',
                        'endpoint': 'https://new.eks.amazonaws.com',
                        'certificateAuthority': {'data': 'new-ca'}}
        self.calls = []
        self.update_failed = False
        self.stale_endpoint = False
        self.stale_ca = False
        self.denied = False
        self.env = patch.dict(os.environ, {'KUBECONFIG': self.config_path}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        tools = patch('dev_cluster.require_tools')
        tools.start()
        self.addCleanup(tools.stop)
        process = patch('dev_cluster.subprocess.run', side_effect=self.fake_run)
        process.start()
        self.addCleanup(process.stop)

    def fake_run(self, command, **kwargs):
        self.calls.append(command)
        if 'describe-cluster' in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({'cluster': self.cluster}), '')
        if 'update-kubeconfig' in command:
            return subprocess.CompletedProcess(command, int(self.update_failed), '', 'AccessDenied' if self.update_failed else '')
        if 'view' in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({'clusters': [{'cluster': {
                'server': 'https://old.eks.amazonaws.com' if self.stale_endpoint else self.cluster['endpoint'],
                'certificate-authority-data': 'old-ca' if self.stale_ca else 'new-ca'}}]}), '')
        return subprocess.CompletedProcess(command, int(self.denied), '', 'Forbidden' if self.denied else '')

    def refresh(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return dev_cluster.refresh_dev_kubeconfig(**kwargs)

    def test_recreation_refreshes_endpoint_and_uses_verified_context(self):
        self.assertEqual(self.refresh()['endpoint'], self.cluster['endpoint'])
        self.assertIn('update-kubeconfig', self.calls[1])
        for command in self.calls[2:]:
            self.assertEqual(command[:3], ['kubectl', '--context', 'pharma-dev'])
        self.assertIn('get', self.calls[-1])
        self.assertIn('nodes', self.calls[-1])

    def test_failed_refresh_never_falls_back_to_old_context(self):
        self.update_failed = True
        with self.assertRaisesRegex(SystemExit, 'AccessDenied'):
            self.refresh()
        self.assertFalse(any(command[0] == 'kubectl' for command in self.calls))

    def test_stale_endpoint_is_rejected_before_connection(self):
        self.stale_endpoint = True
        with self.assertRaisesRegex(SystemExit, 'endpoint/CA'):
            self.refresh()
        self.assertEqual(len(self.calls), 3)

    def test_stale_ca_is_rejected(self):
        self.stale_ca = True
        with self.assertRaisesRegex(SystemExit, 'endpoint/CA'):
            self.refresh()

    def test_wrong_environment_is_rejected_before_any_command(self):
        os.environ['ENV'] = 'prod'
        with self.assertRaisesRegex(SystemExit, 'dev only'):
            self.refresh()
        self.assertFalse(self.calls)

    def test_unrelated_region_default_is_corrected(self):
        os.environ['AWS_REGION'] = 'ap-south-1'
        self.refresh()
        self.assertEqual(os.environ['AWS_REGION'], 'ap-south-1')
        self.assertIn('ap-south-1', self.calls[0])

    def test_inactive_cluster_stops_before_updating_context(self):
        self.cluster['status'] = 'CREATING'
        with self.assertRaisesRegex(SystemExit, 'not ACTIVE'):
            self.refresh()
        self.assertEqual(len(self.calls), 1)

    def test_multiple_kubeconfigs_update_and_verify_first_path(self):
        os.environ['KUBECONFIG'] = self.config_path + os.pathsep + '/other/config'
        self.refresh()
        self.assertEqual(os.environ['KUBECONFIG'], self.config_path)
        self.assertIn(self.config_path, self.calls[1])

    def test_explicit_role_used_for_authentication(self):
        role = 'arn:aws:iam::123456789012:role/dev'
        self.refresh(role_arn=role)
        self.assertEqual(self.calls[1][-2:], ['--role-arn', role])

    def test_authorization_failure_is_not_reported_as_success(self):
        self.denied = True
        with self.assertRaisesRegex(SystemExit, 'Forbidden'):
            self.refresh()

    def test_helm_and_kubectl_cannot_override_context(self):
        for args in (['kubectl', '--context=prod', 'get', 'nodes'],
                     ['helm', '--kube-context', 'prod', 'list'],
                     ['kubectl', '--kubeconfig', '/other', 'get', 'pods']):
            with self.assertRaises(SystemExit):
                dev_cluster.run_process(args)
        self.assertFalse(self.calls)

    def test_helm_is_bound_to_dev(self):
        dev_cluster.run_process(['helm', 'list'])
        self.assertEqual(self.calls, [['helm', '--kube-context', 'pharma-dev', 'list']])

    def test_repository_url_rejects_credentials_and_yaml_injection(self):
        for url in ('https://token@github.com/owner/repo.git', 'https://github.com/owner/repo\nother: value'):
            with self.assertRaises(SystemExit):
                dev_cluster.validate_repo_url(url)
        self.assertEqual(dev_cluster.validate_repo_url('https://github.com/owner/repo.git'), 'https://github.com/owner/repo.git')
