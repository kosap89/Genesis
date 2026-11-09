"""Loopback-only HTTP API and static application; no external Python dependencies."""
from __future__ import annotations

import argparse
import hmac
import io
import json
import math
import mimetypes
import os
import secrets
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .engine import Engine, ROLES, read_limited
from .store import now
from .toolbox import _safe_path
from .lease import DataLease
from .providers import KEY_NAMES, provider_status, DEFAULT_MODELS, openai_model_availability
from .models import default_route, model_info
from .accounting import validate_prices
from .billing import BillingService

MAX_BODY = 128 * 1024


def number(value, minimum, maximum, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f'Expected a number between {minimum} and {maximum}.')
    if integer and int(value) != value:
        raise ValueError('Expected an integer.')
    return int(value) if integer else float(value)


class GenesisServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, engine, web_root, billing=None):
        if address[0] not in {'127.0.0.1', 'localhost'}:
            raise ValueError('Genesis must listen on loopback only.')
        self.engine = engine
        self.web_root = Path(web_root).resolve()
        self.csrf = secrets.token_urlsafe(32)
        self.billing = billing if billing is not None else BillingService(engine.store)
        super().__init__(address, Handler)

    def server_close(self):
        # Keep the data lease until any bounded billing fetch has stopped too.
        while not self.billing.close():
            threading.Event().wait(0.05)
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Genesis/0.1'

    def log_message(self, fmt, *args):
        # Avoid logging CEO objectives, URLs, credentials or request bodies.
        pass

    def _headers(self, status, content_type='application/json; charset=utf-8', length=0, attachment=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if attachment:
            self.send_header('Content-Disposition', 'attachment; filename="' + attachment + '"')
        self.end_headers()

    def _json(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self._headers(status, length=len(raw))
        self.wfile.write(raw)

    def _trusted_host(self):
        port = self.server.server_address[1]
        return self.headers.get('Host') in {f'localhost:{port}', f'127.0.0.1:{port}'}

    def _guard(self, mutation=False):
        if not self._trusted_host():
            self._json(403, {'error':'Untrusted Host header.'})
            return False
        origin = self.headers.get('Origin')
        port = self.server.server_address[1]
        if origin and origin not in {f'http://localhost:{port}', f'http://127.0.0.1:{port}'}:
            self._json(403, {'error':'Cross-origin requests are forbidden.'})
            return False
        if mutation and not hmac.compare_digest(self.headers.get('X-Genesis-CSRF', ''), self.server.csrf):
            self._json(403, {'error':'Missing or invalid CSRF token. Refresh the page.'})
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        path = unquote(urlsplit(self.path).path)
        engine = self.server.engine
        try:
            if path == '/api/health':
                return self._json(200, {'status':'ok', 'service':'genesis', 'worker_alive':bool(engine.thread and engine.thread.is_alive())})
            if path == '/api/state':
                return self._json(200, {**engine.state(), 'billing':self.server.billing.state(), 'csrf_token':self.server.csrf})
            if path == '/api/billing':
                return self._json(200, self.server.billing.state())
            parts = path.strip('/').split('/')
            if len(parts) >= 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'documents':
                venture_id = parts[2]
                if len(parts) == 4:
                    return self._json(200, {'documents': engine.documents.list(venture_id)})
                if len(parts) == 5:
                    return self._json(200, engine.documents.get(venture_id, parts[4]))
                if len(parts) == 6 and parts[5] == 'revisions':
                    return self._json(200, {'revisions': engine.documents.revisions(venture_id, parts[4])})
                if len(parts) == 6 and parts[5] == 'download':
                    document = engine.documents.get(venture_id, parts[4])
                    raw = document['content'].encode('utf-8')
                    filename = ''.join(c for c in document['name'] if c.isascii() and (c.isalnum() or c in '._-')) or 'document.md'
                    self._headers(200, 'text/plain; charset=utf-8', len(raw), filename)
                    return self.wfile.write(raw)
                return self._json(404, {'error':'Endpoint not found.'})
            if path.startswith('/api/tasks/') and path.endswith('/bundle'):
                task_id = path.split('/')[-2]
                task = engine.store.get('tasks', task_id)
                if not task:
                    return self._json(404, {'error':'Task not found.'})
                records = [a for a in engine.store.all('artifacts') if a['task_id'] == task_id]
                buffer = io.BytesIO()
                total = 0
                with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for artifact in records:
                        relative = artifact['path']
                        if any(p.startswith('.genesis-') for p in Path(relative).parts):
                            continue
                        file = _safe_path(engine.workspace(task), relative)
                        if not file.is_file():
                            continue
                        remaining = 50 * 1024 * 1024 - total
                        if file.stat().st_size > remaining:
                            return self._json(413, {'error':'Task bundle exceeds 50 MB. Download individual artifacts.'})
                        try:
                            data = read_limited(file, remaining)
                        except ValueError:
                            return self._json(413, {'error':'Task bundle exceeds 50 MB. Download individual artifacts.'})
                        total += len(data)
                        archive.writestr(relative, data)
                raw = buffer.getvalue()
                self._headers(200, 'application/zip', len(raw), 'genesis-' + task_id[:12] + '.zip')
                return self.wfile.write(raw)
            if path.startswith('/api/tasks/'):
                task_id = path.split('/')[-1]
                task = engine.store.get('tasks', task_id)
                if not task:
                    return self._json(404, {'error':'Task not found.'})
                return self._json(200, dict(task=task, messages=engine.store.messages(task_id), events=engine.store.events(task_id), artifacts=[a for a in engine.store.all('artifacts') if a['task_id']==task_id]))
            if path.startswith('/api/artifacts/'):
                artifact = engine.store.get('artifacts', path.split('/')[-1])
                if not artifact:
                    return self._json(404, {'error':'Artifact not found.'})
                task = engine.store.get('tasks', artifact['task_id'])
                file = _safe_path(engine.workspace(task), artifact['path'])
                if not file.is_file() or file.stat().st_size > 20 * 1024 * 1024:
                    return self._json(404, {'error':'Artifact missing or exceeds 20 MB download limit.'})
                raw = read_limited(file, 20 * 1024 * 1024)
                filename = ''.join(c for c in file.name if c.isascii() and (c.isalnum() or c in '._-')) or 'artifact'
                self._headers(200, 'application/octet-stream', len(raw), filename)
                return self.wfile.write(raw)
            if path.startswith('/api/'):
                return self._json(404, {'error':'Endpoint not found.'})
            relative = 'index.html' if path == '/' else path.lstrip('/')
            if relative not in {'index.html', 'app.js', 'styles.css'}:
                return self._json(404, {'error':'File not found.'})
            file = self.server.web_root / relative
            raw = file.read_bytes()
            mime = {'js':'text/javascript', 'css':'text/css', 'html':'text/html'}[file.suffix.lstrip('.')]
            self._headers(200, mime + '; charset=utf-8', len(raw))
            self.wfile.write(raw)
        except (ValueError, KeyError, OSError):
            self._json(404, {'error':'Resource is unavailable.'})

    def do_POST(self):
        if not self._guard(mutation=True):
            return
        engine = self.server.engine
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self._json(413, {'error':'Request body must be 1–131072 bytes.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self._json(415, {'error':'Use application/json.'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Expected an object.')
            path = unquote(urlsplit(self.path).path)
            parts = path.strip('/').split('/')
            if path == '/api/billing/credentials':
                if body == {'clear': True}:
                    self.server.billing.set_credential('')
                elif set(body) == {'admin_api_key'}:
                    key = body['admin_api_key']
                    if not isinstance(key, str) or not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
                        raise ValueError('Admin key must be printable text without whitespace, up to 4096 characters.')
                    model_keys = [os.environ.get(name, '') for names in KEY_NAMES.values() for name in names]
                    if key.startswith('sk-proj-') or any(hmac.compare_digest(key, value) for value in model_keys if value):
                        raise ValueError('Use a separate Organization Admin API key, not a model credential.')
                    self.server.billing.set_credential(key)
                else:
                    raise ValueError('Use the local hidden-input billing credential helper or clear the session credential.')
                engine.store.event('billing_credentials_changed', configured=self.server.billing.state()['credential_configured'])
                return self._json(200, self.server.billing.state())
            if path == '/api/billing/settings':
                self.server.billing.configure(body)
                if self.server.billing.state()['config']['refresh_interval_seconds']:
                    self.server.billing.start()
                engine.store.event('billing_settings_changed')
                return self._json(200, self.server.billing.state())
            if path == '/api/billing/refresh':
                if body:
                    raise ValueError('Billing refresh accepts an empty object only.')
                return self._json(200, self.server.billing.refresh())
            if path == '/api/providers/openai/check':
                if set(body) - {'venture_id'}:
                    raise ValueError('Unsupported availability fields')
                venture_id = body.get('venture_id')
                if 'venture_id' in body and (not isinstance(venture_id, str) or not engine.store.get('ventures', venture_id)):
                    raise ValueError('Unknown venture')
                models = []
                for agent in engine.store.all('agents'):
                    if venture_id:
                        try:
                            agent = engine.teams.effective_agent(agent['id'], venture_id)
                        except ValueError:
                            continue
                    if not agent.get('enabled', True):
                        continue
                    for route in [agent] + agent.get('fallbacks', []):
                        if route.get('provider') == 'openai' and route.get('model') not in models:
                            models.append(route['model'])
                result = openai_model_availability(models)
                engine.store.event('provider_availability_checked', provider='openai',
                    venture_id=venture_id, status=result['status'], models=[entry['id'] for entry in result['models']])
                return self._json(200, result)
            if path == '/api/credentials':
                provider = body.get('provider')
                key = body.get('api_key')
                configure_agents = body.get('configure_agents', False)
                if not isinstance(provider, str) or provider not in KEY_NAMES:
                    raise ValueError('Unknown provider.')
                if not isinstance(key, str) or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
                    raise ValueError('API key must be printable text without whitespace, up to 4096 characters. An empty key clears the process override.')
                if not isinstance(configure_agents, bool):
                    raise ValueError('configure_agents must be a boolean.')
                if key and (key.startswith('sk-admin-') or self.server.billing.credential_matches(key)):
                    raise ValueError('An Organization Admin key cannot be configured as a model credential.')
                # Only this service process is changed. No secret enters SQLite,
                # logs, command arguments, browser storage, or API responses.
                with engine.guard:
                    variable = KEY_NAMES[provider][0]
                    if key:
                        os.environ[variable] = key
                    else:
                        os.environ.pop(variable, None)
                    configured = next(p['configured'] for p in provider_status() if p['provider'] == provider)
                    if configure_agents and key:
                        for role in ROLES:
                            route = default_route(role) if provider == 'openai' else dict(provider=provider, model=DEFAULT_MODELS[provider], reasoning_effort=None)
                            engine.store.update('agents', role, **route)
                        engine.store.event('agents_default_route_changed', provider=provider, model=DEFAULT_MODELS[provider])
                    engine.store.event('provider_credentials_changed', provider=provider, configured=configured)
                return self._json(200, {'provider':provider, 'configured':configured, 'storage':'process_memory'})
            if path == '/api/tasks/estimate':
                return self._json(200, engine.estimate_task(body.get('objective'), body.get('venture_id') or None,
                    body.get('role') or 'coo', body.get('astra_authorized', False),
                    agent_id=body.get('agent_id'), work_mode=body.get('work_mode', 'independent')))
            if path == '/api/pricing':
                model = body.get('model')
                if not isinstance(model, str) or not model_info('openai', model):
                    raise ValueError('Choose a known OpenAI catalog model.')
                prices = validate_prices({k:v for k,v in body.items() if k != 'model'})
                with engine.guard:
                    overrides = dict(engine.settings().get('pricing_overrides', {}))
                    overrides[model] = prices
                    engine.store.update('settings', 'global', pricing_overrides=overrides)
                engine.store.event('reporting_prices_changed', model=model, prices=prices, budget_enforcement_unchanged=True)
                return self._json(200, dict(model=model, **prices))
            if path == '/api/tasks':
                value = engine.create_task(body.get('objective'), body.get('venture_id') or None,
                    body.get('role') or 'coo', body.get('provider') or None, body.get('model') or None,
                    reasoning_effort=body.get('reasoning_effort'), astra_authorized=body.get('astra_authorized', False),
                    agent_id=body.get('agent_id'), work_mode=body.get('work_mode', 'independent'),
                    depends_on=body.get('depends_on'), review_of=body.get('review_of'), file_claims=body.get('file_claims'))
                return self._json(201, value)
            if path in {'/api/ventures','/api/memories','/api/opportunities'}:
                kind = parts[1]
                required = {'ventures':['name'], 'memories':['title','content'], 'opportunities':['title','summary']}[kind]
                for field in required:
                    if not isinstance(body.get(field), str) or not body[field].strip() or len(body[field]) > 100000:
                        raise ValueError(f'{field} is required and must be text.')
                venture = body.get('venture_id') or None
                if venture and not engine.store.get('ventures', venture):
                    raise ValueError('Unknown venture.')
                fields = {'ventures':['name','description'], 'memories':['title','content','venture_id'], 'opportunities':['title','summary','venture_id']}[kind]
                extra = {}
                if kind == 'ventures':
                    extra = dict(budget_usd=None if body.get('budget_usd') is None else number(body['budget_usd'], 0, 1000000), spent_usd=0.0, reserved_usd=0.0)
                value = engine.store.put(kind, {**extra, **{k:body[k] for k in fields if k in body}, 'created_at':now(), 'status':'active' if kind=='ventures' else 'proposed'})
                engine.store.event(kind + '_created', record_id=value['id'])
                return self._json(201, value)
            if len(parts) == 4 and parts[:2] == ['api','tasks']:
                if parts[3] == 'cancel':
                    engine.cancel(parts[2])
                elif parts[3] == 'resume':
                    engine.resume(parts[2], body.get('provider'), body.get('model'),
                        reasoning_effort=body.get('reasoning_effort'), astra_authorized=body.get('astra_authorized', False),
                        agent_id=body.get('agent_id'))
                else:
                    return self._json(404, {'error':'Unknown task action.'})
                return self._json(200, engine.store.get('tasks', parts[2]))
            if len(parts) == 3 and parts[:2] == ['api','approvals']:
                engine.decide(parts[2], body.get('decision'))
                return self._json(200, engine.store.get('approvals', parts[2]))
            if path == '/api/settings':
                updates = {}
                if 'budget_usd' in body:
                    updates['budget_usd'] = number(body['budget_usd'], 0, 1000000)
                for field in ['allow_network','allow_terminal']:
                    if field in body:
                        if not isinstance(body[field], bool):
                            raise ValueError(field + ' must be a boolean.')
                        updates[field] = body[field]
                for field, maximum in [('max_steps',100), ('max_output_tokens',32768), ('max_concurrency',16), ('max_delegated_tasks',100)]:
                    if field in body:
                        updates[field] = number(body[field], 1, maximum, integer=True)
                if 'max_delegation_depth' in body:
                    updates['max_delegation_depth'] = number(body['max_delegation_depth'], 0, 8, integer=True)
                with engine.guard:
                    value = engine.store.update('settings', 'global', **updates)
                engine.store.event('settings_changed', updates=updates)
                return self._json(200, value)
            if len(parts) in {4, 5} and parts[:2] == ['api', 'projects'] and parts[3] == 'documents':
                if len(parts) == 4:
                    return self._json(201, engine.documents.create(parts[2], body, actor='ceo'))
                return self._json(200, engine.documents.update(parts[2], parts[4], body, actor='ceo'))
            teams = engine.teams
            value = None
            status = 200
            action = None
            if path == '/api/role-templates':
                value, status, action = teams.create_template(body), 201, 'role_template_created'
            elif len(parts) == 3 and parts[:2] == ['api', 'role-templates']:
                value, action = teams.update_template(parts[2], body), 'role_template_updated'
            elif path == '/api/agents':
                value, status, action = teams.create_agent(body), 201, 'agent_created'
            elif len(parts) == 3 and parts[:2] == ['api', 'agents']:
                value, action = teams.update_agent(parts[2], body), 'agent_configured'
            elif len(parts) == 4 and parts[:2] == ['api', 'agents'] and parts[3] == 'duplicate':
                value, status, action = teams.duplicate_agent(parts[2], body), 201, 'agent_duplicated'
            elif len(parts) == 3 and parts[:2] == ['api', 'projects']:
                value, action = teams.update_project(parts[2], body), 'project_configured'
            elif len(parts) == 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'team':
                member_body = {k: v for k, v in body.items() if k != 'agent_id'}
                value, action = teams.assign(parts[2], body.get('agent_id'), member_body), 'team_member_assigned'
            elif len(parts) == 5 and parts[:2] == ['api', 'projects'] and parts[3] == 'team':
                value, action = teams.update_membership(parts[2], parts[4], body), 'team_member_updated'
            if action:
                engine.store.event(action, record_id=value['id'])
                return self._json(status, value)
            return self._json(404, {'error':'Endpoint not found.'})
        except (ValueError, KeyError, TypeError) as exc:
            self._json(400, {'error':str(exc)[:1000]})
        except Exception:
            engine.store.event('http_error')
            self._json(500, {'error':'Internal error. See the audit trail.'})


def main():
    parser = argparse.ArgumentParser(description='Run the local Genesis company OS.')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--data-dir', default=os.environ.get('GENESIS_DATA_DIR', 'data'))
    args = parser.parse_args()
    source = Path(__file__).resolve().parent.parent
    try:
        with DataLease(args.data_dir):
            engine = Engine(args.data_dir, source)
            server = GenesisServer(('127.0.0.1', args.port), engine, source / 'web')
            engine.start()
            server.billing.start()
            print(f'Genesis listening at http://127.0.0.1:{server.server_address[1]}', flush=True)
            print('Local only. Credentials are read from environment. Ctrl+C stops the service.', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                if not engine.close():
                    print('Waiting for the in-flight request/tool before releasing the data directory...', flush=True)
                    while not engine.close():
                        pass
                server.server_close()
    except (RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')

