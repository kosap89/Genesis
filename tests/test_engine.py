"""Offline runtime contract tests. Scripted responses are test doubles only."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.engine import Engine
from genesis.providers import ProviderError, ProviderResult


def response(text='', calls=None, metadata=None):
    return ProviderResult(text, calls or [], 30, 15, 'openai', 'test-model', metadata or {})


def call(name, arguments, call_id='test-call'):
    return {'id': call_id, 'name': name, 'arguments': arguments}


class ScriptedRouter:
    """Deterministic tests only; no fake provider path in the actual application."""
    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def generate(self, messages, tools, config):
        self.requests.append(copy.deepcopy({'messages': messages, 'tools': tools, 'config': config}))
        if not self.script:
            raise AssertionError('Engine made an unexpected extra model request')
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            item = item(messages, tools, config)
        return copy.deepcopy(item)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.engines = []

    def engine(self, router):
        engine = Engine(self.root / 'state', self.source, router)
        self.engines.append(engine)
        self.addCleanup(engine.close)
        return engine

    def task(self, engine, task_id):
        return engine.store.get('tasks', task_id)

    def test_real_workspace_test_execution_after_durable_approval(self):
        test_code = ('import unittest\nclass Check(unittest.TestCase):\n'
                     ' def test_arithmetic(self): self.assertEqual(sum([2, 3]), 5)\n')
        router = ScriptedRouter(response(calls=[
            call('workspace_write', {'path': 'test_candidate.py', 'content': test_code}, 'write'),
            call('run_python_tests', {}, 'execute')]), response('Tests verified; candidate ready.'))
        engine = self.engine(router)
        task = engine.create_task('Create and test a candidate', role='engineering')
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'waiting_approval')
        self.assertEqual((engine.workspace(task) / 'test_candidate.py').read_text(encoding='utf-8'), test_code)
        approval = engine.state()['approvals'][0]
        self.assertEqual(approval['action'], 'terminal')
        self.assertEqual(len(router.requests), 1)

        # Reopening the durable database must preserve the waiting invocation.
        restarted = self.engine(router)
        restarted.decide(approval['id'], 'approved')
        restarted.run(task['id'])
        final = self.task(restarted, task['id'])
        self.assertEqual(final['status'], 'completed')
        outputs = [m for m in restarted.store.messages(task['id']) if m.get('tool_call_id') == 'execute']
        self.assertEqual(len(outputs), 1)
        result = json.loads(outputs[0]['content'])
        self.assertEqual(result['returncode'], 0)
        self.assertIn('Ran 1 test', result['output'])
        self.assertIn('OK', result['output'])
        self.assertEqual(restarted.settings()['reserved_usd'], 0)
        self.assertGreater(final['cost_usd'], 0)
        self.assertTrue(any(a['path'] == 'GENESIS_RESULT.md' for a in restarted.state()['artifacts']))
        # Completed work does not reissue tools or model requests on a tick.
        restarted.tick()
        self.assertEqual(len(router.requests), 2)

    def test_denied_approval_never_executes(self):
        router = ScriptedRouter(response(calls=[call('terminal', {'command': ['python', '-c', 'print("forbidden")']})]),
                                response('Execution was denied; no tests executed.'))
        engine = self.engine(router)
        task = engine.create_task('Run an approved command')
        engine.run(task['id'])
        approval = engine.state()['approvals'][0]
        engine.decide(approval['id'], 'denied')
        with patch('genesis.toolbox.subprocess.Popen', side_effect=AssertionError('Denied command executed')) as process:
            engine.run(task['id'])
        process.assert_not_called()
        self.assertEqual(self.task(engine, task['id'])['status'], 'completed')
        messages = engine.store.messages(task['id'])
        self.assertTrue(any(m['role'] == 'tool' and 'denied' in m['content'] for m in messages))
        with self.assertRaises(ValueError):
            engine.decide(approval['id'], 'approved')

    def test_cancelled_queued_task_never_requests_provider(self):
        router = ScriptedRouter()
        engine = self.engine(router)
        task = engine.create_task('Cancelled before work')
        engine.cancel(task['id'])
        engine.tick()
        engine.run(task['id'])
        self.assertEqual(router.requests, [])
        self.assertEqual(self.task(engine, task['id'])['status'], 'cancelled')
        with self.assertRaises(ValueError):
            engine.resume(task['id'])

    def test_cancelling_waiting_task_invalidates_approval(self):
        router = ScriptedRouter(response(calls=[call('research_fetch_url', {'url': 'https://example.com'})]))
        engine = self.engine(router)
        task = engine.create_task('Research')
        engine.run(task['id'])
        approval = engine.state()['approvals'][0]
        engine.cancel(task['id'])
        with self.assertRaises(ValueError):
            engine.decide(approval['id'], 'approved')
        self.assertEqual(engine.store.get('approvals', approval['id'])['status'], 'denied')

    def test_restart_interrupts_running_and_conservatively_recovers_reservation_once(self):
        router = ScriptedRouter(response('Explicitly resumed after review.'))
        engine = self.engine(router)
        task = engine.create_task('Recover after process failure')
        engine.store.update('tasks', task['id'], status='running')
        engine.store.update('settings', 'global', spent_usd=0.25, reserved_usd=0.4)
        restarted = self.engine(router)
        self.assertEqual(self.task(restarted, task['id'])['status'], 'interrupted')
        self.assertAlmostEqual(restarted.settings()['spent_usd'], 0.65)
        self.assertEqual(restarted.settings()['reserved_usd'], 0)
        restarted.tick()
        self.assertEqual(router.requests, [])
        reopened = self.engine(router)
        self.assertAlmostEqual(reopened.settings()['spent_usd'], 0.65)
        reopened.resume(task['id'])
        reopened.run(task['id'])
        self.assertEqual(self.task(reopened, task['id'])['status'], 'completed')

    def test_crash_after_tool_started_does_not_replay_ambiguous_side_effect(self):
        router = ScriptedRouter(response('Inspected unknown outcome; no duplicate execution.'))
        engine = self.engine(router)
        task = engine.create_task('Recover an interrupted write')
        invocation = call('workspace_write', {'path': 'once.txt', 'content': 'would overwrite'}, 'ambiguous-write')
        engine.store.message(task['id'], {'role': 'assistant', 'content': '', 'tool_calls': [invocation]})
        engine.store.event('tool_started', task['id'], tool='workspace_write', tool_call_id=invocation['id'])
        (engine.workspace(task) / 'once.txt').write_text('original side effect', encoding='utf-8')
        engine.store.update('tasks', task['id'], status='running')
        restarted = self.engine(router)
        restarted.resume(task['id'])
        with patch('genesis.engine.Toolbox.execute', side_effect=AssertionError('Ambiguous invocation replayed')) as execute:
            restarted.run(task['id'])
        execute.assert_not_called()
        self.assertEqual((restarted.workspace(task) / 'once.txt').read_text(encoding='utf-8'), 'original side effect')
        outputs = [m for m in restarted.store.messages(task['id']) if m['role'] == 'tool']
        self.assertEqual(len(outputs), 1)
        self.assertIn('unknown outcome', outputs[0]['content'])
        self.assertTrue(any(e['action'] == 'tool_outcome_unknown' for e in restarted.store.events(task['id'])))

    def test_restart_recovers_decided_approval_before_queue_transition(self):
        for decision in ('approved', 'denied'):
            with self.subTest(decision=decision):
                # Each decision needs an independent durable state directory.
                state = self.root / ('decision-' + decision)
                router = ScriptedRouter(response(calls=[call('terminal', {'command': ['python', '-c', 'print("allowed once")']})]),
                                        response('Recovered approval decision.'))
                engine = Engine(state, self.source, router)
                self.addCleanup(engine.close)
                task = engine.create_task('Recover decision crash')
                engine.run(task['id'])
                approval = engine.state()['approvals'][0]
                # Simulate process termination after approval commit, before task queue commit.
                engine.store.update('approvals', approval['id'], status=decision)
                restarted = Engine(state, self.source, router)
                self.addCleanup(restarted.close)
                self.assertEqual(self.task(restarted, task['id'])['status'], 'interrupted')
                restarted.tick()
                self.assertEqual(len(router.requests), 1)
                restarted.resume(task['id'])
                if decision == 'denied':
                    with patch('genesis.toolbox.subprocess.Popen', side_effect=AssertionError('Denied invocation executed')) as execute:
                        restarted.run(task['id'])
                    execute.assert_not_called()
                else:
                    restarted.run(task['id'])
                self.assertEqual(self.task(restarted, task['id'])['status'], 'completed')
                result = next(m for m in restarted.store.messages(task['id']) if m['role'] == 'tool')
                if decision == 'approved':
                    self.assertIn('allowed once', json.loads(result['content'])['output'])
                else:
                    self.assertIn('denied', result['content'])

    def test_budget_blocks_before_external_request_and_can_resume(self):
        router = ScriptedRouter(response('Within approved budget.'))
        engine = self.engine(router)
        engine.store.update('settings', 'global', budget_usd=0)
        task = engine.create_task('Budget limited task')
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'blocked_budget')
        self.assertEqual(router.requests, [])
        self.assertEqual(engine.settings()['reserved_usd'], 0)
        engine.store.update('settings', 'global', budget_usd=5)
        engine.resume(task['id'])
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'completed')

    def test_missing_credentials_persist_block_and_resume(self):
        router = ScriptedRouter(ProviderError('openai: missing API key'), response('Credentials resolved.'))
        engine = self.engine(router)
        task = engine.create_task('Requires credentials')
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'blocked_credentials')
        self.assertIn('missing API key', self.task(engine, task['id'])['error'])
        self.assertEqual(engine.settings()['reserved_usd'], 0)
        self.assertEqual(engine.settings()['spent_usd'], 0)
        restarted = self.engine(router)
        restarted.tick()
        self.assertEqual(len(router.requests), 1)
        restarted.resume(task['id'])
        restarted.run(task['id'])
        self.assertEqual(self.task(restarted, task['id'])['status'], 'completed')

    def test_step_limit_pauses_before_next_request_and_can_resume(self):
        router = ScriptedRouter(response(calls=[call('workspace_list', {})]), response('Reviewed files.'))
        engine = self.engine(router)
        engine.store.update('settings', 'global', max_steps=1)
        task = engine.create_task('Review workspace')
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'paused_limit')
        self.assertEqual(len(router.requests), 1)
        self.assertTrue(any(m['role'] == 'tool' for m in engine.store.messages(task['id'])))
        engine.store.update('settings', 'global', max_steps=2)
        engine.resume(task['id'])
        engine.run(task['id'])
        self.assertEqual(self.task(engine, task['id'])['status'], 'completed')

    def test_tool_path_violation_returns_error_without_writing_host_file(self):
        router = ScriptedRouter(response(calls=[call('workspace_write', {'path': '../escaped.txt', 'content': 'invalid'})]),
                                response('Path rejected; use workspace paths.'))
        engine = self.engine(router)
        task = engine.create_task('Write candidate')
        engine.run(task['id'])
        self.assertFalse((engine.workspace(task).parent / 'escaped.txt').exists())
        result = next(m for m in engine.store.messages(task['id']) if m['role'] == 'tool')
        self.assertEqual(json.loads(result['content'])['type'], 'ValueError')
        self.assertEqual(self.task(engine, task['id'])['status'], 'completed')

    def test_delegation_waits_then_provides_real_child_result(self):
        router = ScriptedRouter(
            response(calls=[call('delegate_task', {'objective': 'Inspect delivery risks', 'role': 'qa'})]),
            response('QA reviewed actual scope and documented limitations.'),
            response('Integrated the delegated QA findings.'))
        engine = self.engine(router)
        parent = engine.create_task('Plan and independently review', work_mode='collaborative')
        engine.run(parent['id'])
        self.assertEqual(self.task(engine, parent['id'])['status'], 'waiting_approval')
        approval = engine.store.all('approvals')[0]
        self.assertEqual(approval['action'], 'delegation')
        self.assertEqual(len(engine.store.all('tasks')), 1)
        engine.decide(approval['id'], 'approved')
        engine.run(parent['id'])
        self.assertEqual(self.task(engine, parent['id'])['status'], 'waiting_children')
        children = [t for t in engine.state()['tasks'] if t.get('parent_id') == parent['id']]
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]['role'], 'qa')
        engine.run(children[0]['id'])
        engine.tick()
        self.assertEqual(self.task(engine, parent['id'])['status'], 'completed')
        final_history = router.requests[-1]['messages']
        self.assertTrue(any('QA reviewed actual scope' in m.get('content', '') for m in final_history if m['role'] == 'user'))
        self.assertNotIn('delegate_task', {t['name'] for t in router.requests[1]['tools']})

    def test_parent_cancellation_cancels_child(self):
        router = ScriptedRouter(response(calls=[call('delegate_task', {'objective': 'Inspect', 'role': 'qa'})]))
        engine = self.engine(router)
        parent = engine.create_task('Delegate then cancel', work_mode='collaborative')
        engine.run(parent['id'])
        engine.decide(engine.store.all('approvals')[0]['id'], 'approved')
        engine.run(parent['id'])
        engine.cancel(parent['id'])
        self.assertTrue(all(t['status'] == 'cancelled' for t in engine.state()['tasks']))
        engine.tick()
        self.assertEqual(len(router.requests), 1)

    def test_provider_metadata_survives_next_turn(self):
        metadata = {'openai_output': [{'type': 'reasoning', 'encrypted_content': 'test-only-signature'}]}
        router = ScriptedRouter(response(calls=[call('workspace_list', {})], metadata=metadata), response('Done.'))
        engine = self.engine(router)
        task = engine.create_task('Preserve provider state')
        engine.run(task['id'])
        assistant = next(m for m in router.requests[1]['messages'] if m['role'] == 'assistant')
        self.assertEqual(assistant.get('provider_data'), metadata)


if __name__ == '__main__':
    unittest.main()
