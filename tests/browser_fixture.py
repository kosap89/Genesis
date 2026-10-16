"""Browser-only integration fixture. Scripted AI is NEVER a production feature."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genesis.engine import Engine
from genesis.providers import ProviderResult
from genesis.server import GenesisServer


class BrowserOnlyDouble:
    def generate(self, messages, tools, config):
        if not any(m['role'] == 'assistant' for m in messages):
            calls = [
                {'id':'write-app','name':'workspace_write','arguments':{'path':'calculator.py','content':'def add(a, b):\n    return a + b\n'}},
                {'id':'write-test','name':'workspace_write','arguments':{'path':'test_calculator.py','content':'import unittest\nfrom calculator import add\nclass CalculatorTests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(20, 22), 42)\n'}},
                {'id':'execute-test','name':'run_python_tests','arguments':{}},
            ]
            return ProviderResult('',calls,100,100,'openai','browser-test-double')
        return ProviderResult('BROWSER TEST FIXTURE ONLY. Calculator source and actual Python test output are available. This result was scripted for infrastructure verification; it is not live AI acceptance.',[],100,50,'openai','browser-test-double')


parser = argparse.ArgumentParser()
parser.add_argument('--port',type=int,required=True)
parser.add_argument('--data-dir',required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
engine = Engine(args.data_dir,root,BrowserOnlyDouble())
server = GenesisServer(('127.0.0.1',args.port),engine,root/'web')
engine.start()
print('BROWSER TEST FIXTURE ONLY ready',flush=True)
try:
    server.serve_forever()
finally:
    engine.close()
    server.server_close()
