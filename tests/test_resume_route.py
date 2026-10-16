import tempfile
from pathlib import Path
import unittest
from genesis.engine import Engine
from genesis.providers import DEFAULT_MODELS


class ResumeRouteTests(unittest.TestCase):
    def test_route_change_is_explicit_validated_and_audited(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(Path(folder)/'state',Path(folder))
            task=engine.create_task('Credential setup follow-up', provider='openai')
            engine.store.update('tasks',task['id'],status='blocked_credentials')
            engine.resume(task['id'])
            self.assertEqual(engine.store.get('tasks',task['id'])['provider'],'openai')
            engine.store.update('tasks',task['id'],status='blocked_credentials')
            with self.assertRaises(ValueError):
                engine.resume(task['id'],provider='invalid')
            self.assertEqual(engine.store.get('tasks',task['id'])['status'],'blocked_credentials')
            engine.resume(task['id'],provider='gemini')
            routed=engine.store.get('tasks',task['id'])
            self.assertEqual(routed['provider'],'gemini')
            self.assertEqual(routed['model'],DEFAULT_MODELS['gemini'])
            event=next(e for e in engine.store.events(task['id']) if e['action']=='task_route_changed')
            self.assertEqual(event['previous_provider'],'openai')
            engine.close()
