"""Oversized evidence remains recoverable; file ceilings apply to actual reads."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.engine import Engine, TOOL_MESSAGE_LIMIT
from genesis.providers import ProviderResult


class EvidenceRouter:
    def __init__(self):
        self.histories = []

    def generate(self, messages, tools, config):
        self.histories.append(messages)
        if len(self.histories) == 1:
            return ProviderResult('', [{'id':'large-read', 'name':'workspace_read',
                'arguments':{'path':'evidence.txt','limit':100000}}], 1, 1, 'openai', 'test-double')
        return ProviderResult('Evidence retained.', [], 1, 1, 'openai', 'test-double')


class ResultEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.router = EvidenceRouter()
        self.engine = Engine(Path(self.temp.name)/'state', Path(self.temp.name), self.router)
        self.addCleanup(self.engine.close)
        self.task = self.engine.create_task('Inspect real evidence')

    def test_large_tool_result_is_valid_json_and_full_evidence_artifact(self):
        text = ('quotes " \\ Unicode ä 🧬\n') * 2200
        (self.engine.workspace(self.task)/'evidence.txt').write_bytes(text.encode())
        self.engine.run(self.task['id'])
        messages = self.engine.store.messages(self.task['id'])
        tool = next(m for m in messages if m['role']=='tool')
        envelope = json.loads(tool['content'])
        self.assertTrue(envelope['truncated'])
        self.assertLessEqual(len(tool['content']), TOOL_MESSAGE_LIMIT)
        full = self.engine.workspace(self.task)/envelope['full_result_artifact']
        self.assertEqual(json.loads(full.read_text(encoding='utf-8'))['content'], text)
        self.assertTrue(any(a['path']==envelope['full_result_artifact'] for a in self.engine.store.all('artifacts')))
        next_tool = next(m for m in self.router.histories[1] if m['role']=='tool')
        self.assertEqual(next_tool['content'],tool['content'])

    def test_small_tool_result_contract_unchanged(self):
        content = self.engine.tool_result_content(self.task, {'id':'small'}, {'returncode':0,'output':'OK'})
        self.assertEqual(json.loads(content),{'returncode':0,'output':'OK'})

    def test_import_rejects_growth_after_stat_without_creating_destination(self):
        source_task = self.engine.create_task('Source')
        source = self.engine.workspace(source_task)/'source.bin'
        source.write_bytes(b'small')
        self.engine.register_artifacts(source_task)
        artifact = next(a for a in self.engine.store.all('artifacts') if a['task_id']==source_task['id'])
        original_open = Path.open
        def open_growing_file(path, *args, **kwargs):
            if path == source and args and args[0]=='rb':
                return io.BytesIO(b'x'*100001)
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',open_growing_file), self.assertRaisesRegex(ValueError,'byte limit'):
            self.engine._core_tool(self.task,'artifact_import',{'artifact_id':artifact['id']})
        self.assertFalse((self.engine.workspace(self.task)/'source.bin').exists())
