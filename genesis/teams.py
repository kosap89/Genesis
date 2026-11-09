"""Persistent agent instances, reusable role templates and project membership.

Explicit CEO project autonomy grants bounded team/research authorization only;
configuration never increases budgets or rewrites historical ledgers.
"""
from copy import deepcopy
import math

from .models import default_route, validate_model_config
from .store import ident, now

ROUTE_FIELDS = {'provider', 'model', 'reasoning_effort', 'fallbacks',
                'input_cost_per_million', 'output_cost_per_million'}
TEXT_LIMITS = {'name': 300, 'description': 24000, 'system_instructions': 24000,
               'specialization': 2000, 'responsibilities': 24000, 'operating_policy': 24000}
EXECUTION_LIMITS = {'max_concurrency': (1, 16), 'max_steps': (1, 100),
                    'max_output_tokens': (1, 32768), 'max_delegation_depth': (0, 8),
                    'max_delegated_tasks': (1, 100)}
AGENT_FIELDS = ROUTE_FIELDS | {'name', 'description', 'system_instructions',
                             'specialization', 'enabled', 'budget_usd'}


def _object(value):
    if not isinstance(value, dict):
        raise ValueError('Configuration must be an object')
    return deepcopy(value)


def _number(value, field, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1000000:
        raise ValueError(field + ' must be a finite number from 0 to 1000000')
    return value


def _fields(body, allowed):
    body = _object(body)
    unknown = set(body) - allowed
    if unknown:
        raise ValueError('Unsupported configuration fields: ' + ', '.join(sorted(unknown)))
    for field, limit in TEXT_LIMITS.items():
        if field in body and (not isinstance(body[field], str) or len(body[field]) > limit or (field == 'name' and not body[field].strip())):
            raise ValueError('Invalid ' + field)
    if 'model' in body and (not isinstance(body['model'], str) or not 1 <= len(body['model']) <= 200):
        raise ValueError('Model must contain 1 to 200 characters')
    if 'provider' in body and (not isinstance(body['provider'], str) or body['provider'] not in {'openai', 'anthropic', 'gemini'}):
        raise ValueError('Unsupported provider')
    if 'enabled' in body and not isinstance(body['enabled'], bool):
        raise ValueError('enabled must be a boolean')
    if 'budget_usd' in body:
        _number(body['budget_usd'], 'budget_usd', True)
    for field in ('input_cost_per_million', 'output_cost_per_million'):
        if field in body:
            _number(body[field], field)
            if not .001 <= body[field] <= 100000:
                raise ValueError(field + ' must be between 0.001 and 100000')
    return body


def _route(config):
    route = {key: deepcopy(config[key]) for key in ROUTE_FIELDS if key in config}
    fallbacks = route.get('fallbacks', [])
    if not isinstance(fallbacks, list) or len(fallbacks) > 2:
        raise ValueError('Fallbacks must contain at most two routes')
    for fallback in fallbacks:
        _fields(fallback, {'provider', 'model', 'reasoning_effort'})
        if not fallback.get('provider') or not fallback.get('model'):
            raise ValueError('Fallback routes require provider and model')
    # Selection is allowed; the runtime separately requires task-scoped consent.
    normalized = validate_model_config({**route, 'astra_authorized': True})
    normalized.pop('astra_authorized', None)
    for fallback in normalized.get('fallbacks', []):
        fallback.pop('astra_authorized', None)
    return normalized


class TeamManager:
    def __init__(self, store):
        self.store = store

    def _get(self, kind, record_id):
        if not isinstance(record_id, str) or not record_id:
            raise ValueError('Invalid ' + kind + ' ID')
        record = self.store.get(kind, record_id)
        if record is None:
            raise ValueError('Unknown ' + kind + ': ' + str(record_id))
        return record

    def setup(self, roles):
        """Add metadata once while preserving original configs and historical IDs."""
        with self.store.lock:
            if self.store.get('meta', 'dynamic_teams_v1'):
                return
            agents = self.store.all('agents')
            tasks = self.store.all('tasks')
            records = []
            for agent in agents:
                role = agent.get('role', agent['id'])
                template_id = role
                if not self.store.get('role_templates', template_id):
                    template = deepcopy(agent)
                    template.update(id=template_id, role=role)
                    for field in ('spent_usd', 'reserved_usd', 'legacy_default', 'project_ids'):
                        template.pop(field, None)
                    template.setdefault('system_instructions', agent.get('description', ''))
                    template.setdefault('specialization', '')
                    template.setdefault('enabled', True)
                    template.setdefault('budget_usd', None)
                    records.append(('role_templates', template))
                agent.setdefault('template_id', template_id)
                agent.setdefault('legacy_default', agent['id'] in roles)
                agent.setdefault('system_instructions', agent.get('description', ''))
                agent.setdefault('specialization', '')
                agent.setdefault('enabled', True)
                agent.setdefault('budget_usd', None)
                agent.setdefault('spent_usd', sum(t.get('cost_usd', 0) or 0 for t in tasks if t.get('agent_id', t.get('role')) == agent['id']))
                agent.setdefault('reserved_usd', 0.0)
                records.append(('agents', agent))
            ids = {a['id'] for a in agents}
            for task in tasks:
                if not task.get('agent_id') and task.get('role') in ids:
                    records.append(('tasks', {**task, 'agent_id': task['role']}))
            for project in self.store.all('ventures'):
                project.setdefault('budget_usd', None)
                project.setdefault('spent_usd', sum(t.get('cost_usd', 0) or 0 for t in tasks if t.get('venture_id') == project['id']))
                project.setdefault('reserved_usd', 0.0)
                records.append(('ventures', project))
            records.append(('meta', {'id': 'dynamic_teams_v1', 'migrated_at': now()}))
            self.store.batch(records)

    def _project_ids(self, value):
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value) or len(set(value)) != len(value):
            raise ValueError('project_ids must be a list of unique project IDs')
        for project_id in value:
            self._get('ventures', project_id)
        return value

    def _membership(self, venture_id, agent_id, body, existing=None):
        body = _fields(body, {'enabled', 'responsibilities', 'overrides', 'action', 'system_instructions', 'specialization'})
        action = body.pop('action', None)
        if action not in (None, 'remove'):
            raise ValueError('Unsupported membership action')
        overrides = body.get('overrides', (existing or {}).get('overrides', {}))
        overrides = _fields(overrides, ROUTE_FIELDS)
        if ('provider' in overrides or 'model' in overrides) and 'reasoning_effort' not in overrides:
            overrides['reasoning_effort'] = None
        agent = self._get('agents', agent_id) if existing is None else None
        if agent is None:
            agent = self._get('agents', agent_id)
        _route({**agent, **overrides})
        result = dict(existing or {}, id=venture_id + ':' + agent_id, venture_id=venture_id, agent_id=agent_id)
        result.setdefault('enabled', True)
        result.setdefault('responsibilities', '')
        result.update(body, overrides=overrides, status='removed' if action == 'remove' else 'active')
        return result

    def create_template(self, body):
        with self.store.lock:
            body = _fields(body, AGENT_FIELDS | {'role'})
            template_id = ident()
            role = body.pop('role', template_id)
            if not isinstance(role, str) or not role.strip() or len(role) > 300:
                raise ValueError('Invalid role')
            template = dict(default_route(role), id=template_id, role=role, name='Custom role',
                            description='', system_instructions='', specialization='', enabled=True,
                            budget_usd=None, fallbacks=[], input_cost_per_million=10.0, output_cost_per_million=30.0)
            template.update(body)
            template.update(_route(template))
            return self.store.put('role_templates', template)

    def update_template(self, template_id, body):
        with self.store.lock:
            body = _fields(body, AGENT_FIELDS)
            current = self._get('role_templates', template_id)
            if any(k in body and body[k] != current.get(k) for k in ('provider', 'model')) and 'reasoning_effort' not in body:
                body['reasoning_effort'] = None
            template = {**current, **body}
            template.update(_route(template))
            return self.store.put('role_templates', template)

    def create_agent(self, body):
        with self.store.lock:
            body = _fields(body, AGENT_FIELDS | {'template_id', 'project_ids'})
            template_id = body.pop('template_id', None)
            template = self._get('role_templates', template_id)
            projects = self._project_ids(body.pop('project_ids', []))
            agent = deepcopy(template)
            if any(k in body and body[k] != agent.get(k) for k in ('provider', 'model')) and 'reasoning_effort' not in body:
                body['reasoning_effort'] = None
            agent.update(body, id=ident(), template_id=template_id, legacy_default=False,
                         spent_usd=0.0, reserved_usd=0.0, created_at=now())
            agent.update(_route(agent))
            records = [('agents', agent)]
            for project_id in projects:
                records.append(('team_memberships', dict(id=project_id + ':' + agent['id'],
                    venture_id=project_id, agent_id=agent['id'], enabled=True, status='active', responsibilities='', overrides={})))
            self.store.batch(records)
            return agent

    def update_agent(self, agent_id, body):
        with self.store.lock:
            body = _fields(body, AGENT_FIELDS | {'project_ids'})
            projects = self._project_ids(body.pop('project_ids')) if 'project_ids' in body else None
            current_agent = self._get('agents', agent_id)
            if any(k in body and body[k] != current_agent.get(k) for k in ('provider', 'model')) and 'reasoning_effort' not in body:
                body['reasoning_effort'] = None
            agent = {**current_agent, **body}
            agent.update(_route(agent))
            records = [('agents', agent)]
            if projects is not None:
                current = {m['venture_id']: m for m in self.store.all('team_memberships') if m['agent_id'] == agent_id}
                for project_id in set(current) | set(projects):
                    membership = current.get(project_id, dict(id=project_id + ':' + agent_id,
                        venture_id=project_id, agent_id=agent_id, enabled=True, responsibilities='', overrides={}))
                    membership['status'] = 'active' if project_id in projects else 'removed'
                    records.append(('team_memberships', membership))
            self.store.batch(records)
            return agent

    def duplicate_agent(self, agent_id, body=None):
        with self.store.lock:
            body = _fields(body or {}, {'name', 'project_ids'})
            original = self._get('agents', agent_id)
            fields = {k: deepcopy(v) for k, v in original.items() if k in AGENT_FIELDS}
            fields.update(template_id=original['template_id'], name=original['name'] + ' copy')
            fields.update(body)
            return self.create_agent(fields)

    def assign(self, venture_id, agent_id, body=None):
        with self.store.lock:
            self._get('ventures', venture_id)
            self._get('agents', agent_id)
            existing = self.store.get('team_memberships', venture_id + ':' + agent_id)
            membership = self._membership(venture_id, agent_id, body or {}, existing)
            return self.store.put('team_memberships', membership)

    def update_membership(self, venture_id, agent_id, body):
        with self.store.lock:
            self._get('team_memberships', venture_id + ':' + agent_id)
            return self.assign(venture_id, agent_id, body)

    def update_project(self, venture_id, body):
        with self.store.lock:
            body = _fields(body, {'budget_usd', 'operating_policy', 'execution_limits', 'mission_draft', 'autonomy'})
            current = self._get('ventures', venture_id)
            if 'autonomy' in body:
                autonomy = _fields(body['autonomy'], {'delegation', 'research'})
                if any(type(value) is not bool for value in autonomy.values()):
                    raise ValueError('Project autonomy values must be boolean.')
                body['autonomy'] = {**{'delegation': False, 'research': False},
                                    **current.get('autonomy', {}), **autonomy}
            if 'execution_limits' in body:
                limits = _fields(body['execution_limits'], set(EXECUTION_LIMITS))
                for field, value in limits.items():
                    low, high = EXECUTION_LIMITS[field]
                    if type(value) is not int or not low <= value <= high:
                        raise ValueError(field + f' must be an integer from {low} to {high}')
                body['execution_limits'] = limits
            if body.get('mission_draft') is not None:
                draft = _fields(body['mission_draft'], {'objective', 'agent_id', 'work_mode'})
                if (set(draft) != {'objective', 'agent_id', 'work_mode'} or
                        not isinstance(draft['objective'], str) or not draft['objective'].strip() or
                        len(draft['objective']) > 24000):
                    raise ValueError('Mission draft requires objective (1-24000 characters), agent_id and work_mode')
                if draft['work_mode'] not in ('independent', 'collaborative'):
                    raise ValueError('Work mode must be independent or collaborative')
                agent = self.effective_agent(draft['agent_id'], venture_id)
                membership = self.store.get('team_memberships', venture_id + ':' + agent['id'])
                if not membership or membership.get('status') != 'active' or membership.get('enabled') is not True:
                    raise ValueError('Draft lead must be an active project team member')
                draft['objective'] = draft['objective'].strip()
                body['mission_draft'] = draft
            return self.store.put('ventures', {**current, **body})

    def effective_agent(self, agent_id, venture_id=None):
        with self.store.lock:
            agent = self._get('agents', agent_id)
            if agent.get('enabled', True) is not True:
                raise ValueError('Agent is disabled')
            membership = None
            if venture_id is not None:
                self._get('ventures', venture_id)
                membership = self.store.get('team_memberships', venture_id + ':' + agent_id)
            if membership is not None:
                if membership.get('status') != 'active' or membership.get('enabled') is not True:
                    raise ValueError('Agent project membership is inactive')
                agent.update(deepcopy(membership.get('overrides', {})))
                agent['responsibilities'] = membership.get('responsibilities', '')
                for field in ('system_instructions', 'specialization'):
                    if field in membership:
                        agent[field] = membership[field]
            elif not agent.get('legacy_default', False):
                assigned = any(m['agent_id'] == agent_id and m.get('status') == 'active' for m in self.store.all('team_memberships'))
                if venture_id is not None or assigned:
                    raise ValueError('Agent is not assigned to this project')
            return agent

    def resolve_agent(self, agent_id=None, role='coo', venture_id=None):
        return self.effective_agent(agent_id if agent_id is not None else role, venture_id)

    def state(self):
        with self.store.lock:
            memberships = self.store.all('team_memberships')
            tasks = self.store.all('tasks')
            agents = self.store.all('agents')
            for agent in agents:
                own_tasks = [t for t in tasks if t.get('agent_id', t.get('role')) == agent['id'] or agent['id'] in t.get('agent_history', [])]
                agent['project_ids'] = [m['venture_id'] for m in memberships if m['agent_id'] == agent['id'] and m.get('status') == 'active']
                agent['task_count'] = len(own_tasks)
                agent['activity_status'] = 'disabled' if not agent.get('enabled', True) else ('active' if any(t.get('agent_id', t.get('role')) == agent['id'] and t.get('status') in {'running', 'queued', 'waiting_approval'} for t in own_tasks) else 'idle')
            return dict(role_templates=self.store.all('role_templates'), team_memberships=memberships, agents=agents)
