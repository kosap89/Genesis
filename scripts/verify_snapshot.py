"""Verify the real Genesis checkout through its candidate tools, without AI calls."""
import argparse
import json
import sys
import uuid
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE))
from genesis.toolbox import ToolContext, Toolbox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Authorize real Python execution in the copied candidate.')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Use --execute to authorize real tests in the isolated working directory (not an OS sandbox).')
    workspace = SOURCE / 'data' / 'verification' / uuid.uuid4().hex
    tools = Toolbox(ToolContext(workspace, SOURCE, allow_terminal=True))
    snapshot = tools.execute('self_improvement_snapshot', {})
    tests = tools.execute('run_python_tests', {'path':'source/tests', 'workdir':'source', 'timeout':60})
    diff = tools.execute('self_improvement_diff', {})
    report = {'kind':'actual_source_snapshot_verification', 'live_ai':False,
              'workspace':str(workspace), 'snapshot':snapshot, 'tests':tests,
              'unchanged_candidate':not any(diff[k] for k in ('added','modified','deleted')),
              'patch_artifact':diff.get('artifact')}
    output = SOURCE / 'test-results' / 'source-snapshot-verification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if tests.get('passed') and report['unchanged_candidate'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
