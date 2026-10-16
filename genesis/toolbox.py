"""Real, permission-gated tools. Workspace isolation is not an OS sandbox."""
from __future__ import annotations

import difflib
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin, urlsplit


class PermissionRequired(Exception):
    def __init__(self, action: str, details: str):
        super().__init__(details)
        self.action = action
        self.details = details


@dataclass
class ToolContext:
    root: Path
    source_root: Path
    allow_network: bool = False
    allow_terminal: bool = False


MAX_TEXT = 100_000
MAX_OUTPUT = 32_000
MAX_FETCH = 1_000_000
CHILD_ENVIRONMENT = {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC',
                     'PATHEXT', 'LANG', 'LC_ALL'}
EXCLUDED = {'.git', '.env', '.aws', '.codex', '.agents', 'data', 'node_modules',
            'venv', '.venv', '__pycache__', '.pytest_cache', 'secrets', 'credentials'}


def _is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _safe_path(root: Path, relative: str, *, internal: bool = False) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or raw.drive or '..' in raw.parts or ':' in relative:
        raise ValueError('Path must be relative to the workspace without traversal')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
    for part in raw.parts:
        if not internal and part.lower().startswith('.genesis-'):
            raise ValueError('Genesis internal snapshot metadata is protected')
        if (part.rstrip(' .') != part or any(ord(char) < 32 for char in part)
                or part.split('.')[0].upper() in reserved):
            raise ValueError('Invalid or reserved workspace filename')
    # Check lexical ancestors before resolve(), which would hide symlinks/junctions.
    for part in [root, *root.parents]:
        if part.exists() and _is_link(part):
            raise ValueError('Symlinks and junctions are forbidden')
    candidate = root
    for part in raw.parts:
        candidate = candidate / part
        if candidate.exists() or candidate.is_symlink():
            if _is_link(candidate):
                raise ValueError('Symlinks and junctions are forbidden')
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path leaves the workspace')
    return candidate


def _snapshot_excluded(name: str) -> bool:
    lower = name.lower()
    return (lower in EXCLUDED or lower.startswith(('.env', '.genesis-'))
            or any(word in lower for word in ('secret', 'credential', 'token'))
            or lower.endswith(('.pem', '.key', '.p12', '.db', '.sqlite', '.sqlite3')))


def _snapshot_files(root: Path, excluded_root: Path | None = None):
    """The same exclusion and resource limits apply to snapshots and candidates."""
    _safe_path(root, '.')
    count = 0
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        current = Path(directory)
        dirs[:] = sorted(d for d in dirs if not _snapshot_excluded(d)
                         and not _is_link(current / d)
                         and not (excluded_root and (current / d).resolve().is_relative_to(excluded_root.resolve())))
        for filename in sorted(files):
            path = current / filename
            if _snapshot_excluded(filename) or _is_link(path) or not path.is_file():
                continue
            if path.stat().st_size > 1_000_000:
                continue
            data = path.read_bytes()
            if len(data) > 1_000_000:
                continue
            count += 1
            total += len(data)
            if total > 20_000_000 or count > 2000:
                raise ValueError('Snapshot exceeds 20 MB / 2000 file limit')
            yield path.relative_to(root).as_posix(), data


def _unified_patch(relative: str, before: bytes | None, after: bytes | None) -> str | None:
    try:
        old = (before or b'').decode('utf-8')
        new = (after or b'').decode('utf-8')
    except UnicodeDecodeError:
        return None
    if '\x00' in old or '\x00' in new:
        return None
    # Unified diff line counts use LF only. str.splitlines() also splits form
    # feeds and Unicode separators, producing corrupt hunks for valid text.
    def lines_with_lf(text):
        parts = text.split('\n')
        return [part + '\n' for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])

    lines = difflib.unified_diff(lines_with_lf(old), lines_with_lf(new),
                                fromfile='a/' + relative if before is not None else '/dev/null',
                                tofile='b/' + relative if after is not None else '/dev/null')
    # difflib doesn't emit the standard marker for a missing final newline.
    return ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                   for line in lines)


def _public_addresses(host: str, port: int) -> list:
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError('Host did not resolve')
    for entry in addresses:
        ip = ipaddress.ip_address(entry[4][0].split('%')[0])
        if not ip.is_global:
            raise ValueError('Only public network addresses are permitted')
    return addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    """Connect to already-validated DNS results; retain hostname TLS verification."""
    def __init__(self, host, addresses):
        super().__init__(host, port=443, timeout=15, context=ssl.create_default_context())
        self.addresses = addresses

    def connect(self):
        last_error = None
        for family, kind, proto, _, address in self.addresses:
            connection = socket.socket(family, kind, proto)
            connection.settimeout(self.timeout)
            try:
                connection.connect(address)
                self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
                return
            except OSError as exc:
                last_error = exc
                connection.close()
        raise last_error or OSError('Unable to connect')


def _fetch_public(url: str, headers: dict | None = None) -> dict:
    for _ in range(6):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Only public HTTPS URLs without credentials are permitted')
        if parsed.port not in (None, 443):
            raise ValueError('Only HTTPS port 443 is permitted')
        addresses = _public_addresses(parsed.hostname, 443)
        connection = _PinnedHTTPS(parsed.hostname, addresses)
        try:
            target = parsed.path or '/'
            if parsed.query:
                target += '?' + parsed.query
            connection.request('GET', target, headers={'User-Agent': 'Genesis/1.0', **(headers or {})})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                destination = response.getheader('Location')
                if not destination:
                    raise ValueError('Redirect has no destination')
                next_url = urljoin(url, destination)
                # Never forward API credentials across redirects.
                if urlsplit(next_url).hostname != parsed.hostname:
                    headers = None
                url = next_url
                continue
            data = response.read(MAX_FETCH + 1)
            if len(data) > MAX_FETCH:
                raise ValueError('Response exceeds 1 MB limit')
            return {'url': url, 'status': response.status,
                    'content_type': response.getheader('Content-Type', ''),
                    'text': data.decode('utf-8', errors='replace')}
        finally:
            connection.close()
    raise ValueError('Too many redirects')


class Toolbox:
    def __init__(self, context: ToolContext):
        self.context = context
        self.context.root = Path(context.root).absolute()
        self.context.source_root = Path(context.source_root).absolute()
        _safe_path(self.context.root, '.')
        self.context.root.mkdir(parents=True, exist_ok=True)

    def schemas(self) -> list[dict]:
        entries = [
            ('workspace_read', 'Read a UTF-8 workspace file', {'path': {'type': 'string'}}, ['path']),
            ('workspace_write', 'Write a UTF-8 workspace file', {'path': {'type': 'string'}, 'content': {'type': 'string'}}, ['path', 'content']),
            ('workspace_list', 'List a workspace directory', {'path': {'type': 'string'}}, []),
            ('run_python_tests', 'Run unittest discovery in workspace; requires execution approval', {'path': {'type': 'string'}, 'timeout': {'type': 'integer'}}, []),
            ('terminal', 'Run an allowed command without a shell; requires execution approval', {'command': {'type': 'array', 'items': {'type': 'string'}}, 'timeout': {'type': 'integer'}}, ['command']),
            ('research_fetch_url', 'Fetch a public HTTPS URL; requires network approval', {'url': {'type': 'string'}}, ['url']),
            ('research_search', 'Discover web sources using Brave if configured, otherwise Wikipedia only', {'query': {'type': 'string'}}, ['query']),
            ('self_improvement_snapshot', 'Copy source files into workspace/source for candidate editing', {}, []),
            ('self_improvement_diff', 'Compare candidate source to its persistent snapshot baseline; save a review patch without changing live source', {}, []),
            ('artifact_report', 'Write a report in workspace/artifacts', {'name': {'type': 'string'}, 'content': {'type': 'string'}}, ['name', 'content']),
        ]
        return [{'name': name, 'description': description, 'parameters': {'type': 'object', 'properties': props, 'required': required, 'additionalProperties': False}}
                for name, description, props, required in entries]

    def _permission(self, kind: str, details: str):
        if not getattr(self.context, 'allow_' + kind):
            raise PermissionRequired(kind, details)

    def _run(self, argv: list[str], timeout: int) -> dict:
        self._permission('terminal', 'Execute code in the task workspace: ' + ' '.join(argv))
        timeout = max(1, min(int(timeout), 60))
        # Disk-backed output avoids unbounded in-memory capture. These processes
        # inherit OS access: approval is mandatory, even for Python tests.
        with tempfile.TemporaryFile() as output:
            child_environment = {key: value for key, value in os.environ.items()
                                 if key.upper() in CHILD_ENVIRONMENT}
            process = subprocess.Popen(argv, cwd=self.context.root, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, shell=False,
                                       env=child_environment)
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
            output.seek(0)
            captured = output.read(MAX_OUTPUT + 1)
        return {'returncode': process.returncode, 'timed_out': timed_out,
                'output': captured[:MAX_OUTPUT].decode('utf-8', errors='replace'),
                'truncated': len(captured) > MAX_OUTPUT}

    def execute(self, name: str, arguments: dict) -> dict:
        if name not in {item['name'] for item in self.schemas()}:
            raise ValueError('Unknown tool: ' + name)
        if name == 'workspace_read':
            path = _safe_path(self.context.root, arguments['path'])
            if path.stat().st_size > MAX_TEXT:
                raise ValueError('File exceeds 100 KB limit')
            return {'path': arguments['path'], 'content': path.read_text(encoding='utf-8')}
        if name == 'workspace_write':
            content = arguments['content']
            if len(content.encode('utf-8')) > MAX_TEXT:
                raise ValueError('File exceeds 100 KB limit')
            path = _safe_path(self.context.root, arguments['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return {'path': arguments['path'], 'bytes': len(content.encode('utf-8'))}
        if name == 'workspace_list':
            path = _safe_path(self.context.root, arguments.get('path', '.'))
            children = sorted((entry for entry in path.iterdir() if not entry.name.lower().startswith('.genesis-')), key=lambda entry: entry.name)[:1000]
            return {'entries': [{'name': child.name, 'kind': 'link' if _is_link(child) else 'directory' if child.is_dir() else 'file'} for child in children]}
        if name == 'run_python_tests':
            self._permission('terminal', 'Run Python unittest discovery in the task workspace')
            path = _safe_path(self.context.root, arguments.get('path', '.'))
            return self._run([sys.executable, '-I', '-m', 'unittest', 'discover', '-s', str(path)], arguments.get('timeout', 30))
        if name == 'terminal':
            self._permission('terminal', 'Execute a restricted command in the task workspace')
            argv = arguments['command']
            if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
                raise ValueError('command must be a nonempty array of strings')
            # Python is intentionally capable of arbitrary candidate development,
            # gated by execution approval. No shell or destructive utility exposed.
            if argv[0] not in ('python', 'python3'):
                raise ValueError('Allowed executable: python (execution approval required)')
            return self._run([sys.executable, '-I', *argv[1:]], arguments.get('timeout', 30))
        if name == 'research_fetch_url':
            self._permission('network', 'Fetch public HTTPS URL: ' + arguments['url'])
            return _fetch_public(arguments['url'])
        if name == 'research_search':
            self._permission('network', 'Search public sources: ' + arguments['query'])
            query = arguments['query'][:500]
            key = os.environ.get('BRAVE_SEARCH_API_KEY')
            if key:
                result = _fetch_public('https://api.search.brave.com/res/v1/web/search?' + urlencode({'q': query, 'count': 5}), {'X-Subscription-Token': key})
                data = json.loads(result['text'])
                return {'scope': 'Brave web search', 'results': [{'title': item.get('title'), 'url': item.get('url'), 'description': item.get('description')} for item in data.get('web', {}).get('results', [])[:5]]}
            result = _fetch_public('https://en.wikipedia.org/w/api.php?' + urlencode({'action': 'opensearch', 'search': query, 'limit': 5, 'format': 'json'}))
            data = json.loads(result['text'])
            return {'scope': 'Wikipedia discovery only; not general web search', 'results': [{'title': title, 'url': url} for title, url in zip(data[1], data[3])]}
        if name == 'self_improvement_snapshot':
            source = self.context.source_root
            _safe_path(source, '.')
            destination = _safe_path(self.context.root, 'source')
            baseline = _safe_path(self.context.root, '.genesis-baseline', internal=True)
            manifest_path = _safe_path(self.context.root, '.genesis-snapshot.json', internal=True)
            if destination.exists() or baseline.exists() or manifest_path.exists():
                raise ValueError('source snapshot already exists; use a fresh task workspace')
            copied = 0
            total = 0
            manifest = {'version': 1, 'files': {}}
            for relative, data in _snapshot_files(source, self.context.root):
                target = _safe_path(destination, relative)
                original = _safe_path(baseline, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                original.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                original.write_bytes(data)
                manifest['files'][relative] = hashlib.sha256(data).hexdigest()
                copied += 1
                total += len(data)
            destination.mkdir(parents=True, exist_ok=True)
            baseline.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8')
            return {'path': 'source', 'files': copied, 'bytes': total, 'source_modified': False,
                    'baseline': 'persistent original snapshot; use self_improvement_diff after editing'}
        if name == 'self_improvement_diff':
            return self._self_improvement_diff()
        if name == 'artifact_report':
            filename = arguments['name']
            if not filename or Path(filename).name != filename or '/' in filename or '\\' in filename:
                raise ValueError('Report name must be a filename')
            result = self.execute('workspace_write', {'path': 'artifacts/' + filename, 'content': arguments['content']})
            return {'artifact': result['path'], 'bytes': result['bytes']}
        raise ValueError('Unknown tool')

    def _self_improvement_diff(self) -> dict:
        manifest_path = _safe_path(self.context.root, '.genesis-snapshot.json', internal=True)
        if not manifest_path.is_file():
            raise ValueError('Create a self_improvement_snapshot before requesting a diff')
        if manifest_path.stat().st_size > 1_000_000:
            raise ValueError('Snapshot manifest exceeds limit')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        originals = manifest.get('files')
        if manifest.get('version') != 1 or not isinstance(originals, dict) or len(originals) > 2000:
            raise ValueError('Invalid snapshot manifest')
        baseline = _safe_path(self.context.root, '.genesis-baseline', internal=True)
        candidate = _safe_path(self.context.root, 'source')
        if not candidate.is_dir():
            raise ValueError('Candidate source directory is missing')
        files = dict(_snapshot_files(candidate))
        changed = []
        added = []
        deleted = []
        binary = []
        omitted = []
        skipped = []
        live_changed = []
        chunks = []
        patch_bytes = 0
        for relative in sorted(originals.keys() | files.keys()):
            if not isinstance(relative, str) or any(_snapshot_excluded(part) for part in Path(relative).parts):
                raise ValueError('Invalid path in snapshot manifest')
            before = None
            if relative in originals:
                original = _safe_path(baseline, relative)
                if original.stat().st_size > 1_000_000:
                    raise ValueError('Baseline file exceeds limit')
                before = original.read_bytes()
                if hashlib.sha256(before).hexdigest() != originals[relative]:
                    raise ValueError('Snapshot baseline integrity check failed: ' + relative)
            after = files.get(relative)
            if relative in originals and relative not in files:
                try:
                    missing = _safe_path(candidate, relative)
                    exists_but_excluded = missing.exists() or missing.is_symlink()
                except ValueError:
                    exists_but_excluded = True
                if exists_but_excluded:
                    changed.append(relative)
                    omitted.append(relative)
                    skipped.append(relative)
                    continue
            if before == after:
                continue
            (added if before is None else deleted if after is None else changed).append(relative)
            # Source may have evolved since snapshot creation. Detect conflicts for
            # proposed paths, but never regenerate the baseline from current source.
            try:
                live = _safe_path(self.context.source_root, relative)
                current_hash = (hashlib.sha256(live.read_bytes()).hexdigest()
                                if live.is_file() and live.stat().st_size <= 1_000_000 else None)
                if (current_hash != originals.get(relative)
                        or (before is None and live.exists())):
                    live_changed.append(relative)
            except (OSError, ValueError):
                live_changed.append(relative)
            patch = _unified_patch(relative, before, after)
            if patch is None:
                binary.append(relative)
                omitted.append(relative)
                continue
            size = len(patch.encode('utf-8'))
            if not patch or patch_bytes + size > MAX_TEXT:
                omitted.append(relative)
                continue
            chunks.append(patch)
            patch_bytes += size
        text = ''.join(chunks)
        artifact = _safe_path(self.context.root, 'artifacts/self-improvement.patch')
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(text.encode('utf-8'))
        return {'artifact': 'artifacts/self-improvement.patch', 'comparison': 'original_snapshot_baseline',
                'changed': changed, 'added': added, 'deleted': deleted, 'binary': binary,
                'omitted_patch_files': omitted, 'truncated': bool(omitted), 'patch_bytes': patch_bytes,
                'skipped_candidate_files': skipped,
                'patch': text, 'live_source_changed': live_changed, 'source_modified': False,
                'warning': 'Review only. No changes applied. Omitted files require separate review; live changes may cause conflicts.'}
