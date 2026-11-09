"""Read-only OpenAI organization reporting. Admin credentials never enter storage."""
from __future__ import annotations

import copy
import hmac
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

DASHBOARD_URL = 'https://platform.openai.com/settings/organization/billing/overview'
BASE = 'https://api.openai.com/v1/organization/'


class BillingError(Exception):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(url, headers, timeout):
    request = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise BillingError('Billing response exceeds size limit.')
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        retry = 900 if exc.code == 429 else 0
        try:
            retry = max(retry, min(86400, int(exc.headers.get('Retry-After', '0'))))
        except (ValueError, TypeError):
            pass
        raise BillingError(f'OpenAI billing request failed (HTTP {exc.code}).', retry) from None


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise BillingError('Invalid monetary amount in provider report.')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise BillingError('Invalid monetary amount in provider report.') from None
    if not result.is_finite() or abs(result) > Decimal('1e15'):
        raise BillingError('Invalid monetary amount in provider report.')
    return result


class BillingService:
    def __init__(self, store, transport=None, clock=None):
        self.store = store
        self.transport = transport or _http
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self._key = None
        self._generation = 0
        self._busy = False
        self._completion = threading.Event()
        self._completion.set()
        self._closed = False
        self._stop = threading.Event()
        self._thread = None
        self._next = 0
        saved = store.get('billing_config', 'openai') or {}
        self.config = {'refresh_interval_seconds': saved.get('refresh_interval_seconds', 0), 'include_usage': saved.get('include_usage', True)}
        self.report = store.get('billing_reports', 'openai')
        if self.report and self.report.get('cleared'):
            self.report = None
        self.last_attempt = None
        self.error = None

    def credential_matches(self, value):
        with self.lock:
            return bool(self._key and isinstance(value, str) and hmac.compare_digest(self._key, value))

    def state(self):
        with self.lock:
            now = self.clock()
            month = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m')
            report = copy.deepcopy(self.report)
            stale = bool(report and (report.get('month') != month or self.error or
                         now - report.get('synced_at_epoch', 0) > 86400))
            return {'credential_configured': bool(self._key), 'config': dict(self.config),
                    'report': report, 'historical_snapshot': bool(report and not self._key), 'last_successful_sync': report.get('last_successful_sync') if report else None,
                    'last_attempt': self.last_attempt, 'error': self.error, 'stale': stale,
                    'in_flight': self._busy, 'next_refresh_at': self._next or None,
                    'prepaid': {'supported': False, 'balance': None, 'dashboard_url': DASHBOARD_URL},
                    'notice': 'Official reporting can be delayed. Costs are organization-wide; usage covers completions only. No documented prepaid balance API is available.'}

    def configure(self, body):
        if set(body) - {'refresh_interval_seconds', 'include_usage'}:
            raise ValueError('Unsupported billing configuration field.')
        interval = body.get('refresh_interval_seconds', self.config['refresh_interval_seconds'])
        if isinstance(interval, bool) or not isinstance(interval, int) or (interval != 0 and not 900 <= interval <= 86400):
            raise ValueError('Refresh interval must be 0 (off) or 900–86400 seconds.')
        include_usage = body.get('include_usage', self.config['include_usage'])
        if not isinstance(include_usage, bool):
            raise ValueError('include_usage must be boolean.')
        with self.lock:
            self.config = {'refresh_interval_seconds': interval, 'include_usage': include_usage}
            self.store.put('billing_config', {'id': 'openai', **self.config})
        return self.state()

    def set_credential(self, key):
        if not isinstance(key, str) or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
            if key != '':
                raise ValueError('Invalid Admin API key format.')
        if key and not key.startswith('sk-admin-'):
            raise ValueError('Use a separate Organization Admin API key (sk-admin-).')
        with self.lock:
            self._key = key or None
            self._generation += 1
            self.report = None
            self.store.put('billing_reports', {'id': 'openai', 'cleared': True})
            self.error = None
            self.last_attempt = None
            self._next = 0
        return self.state()

    def _pages(self, path, params, key, deadline):
        pages = []
        seen = set()
        for _ in range(8):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BillingError('Billing synchronization exceeded time limit.')
            url = BASE + path + '?' + urllib.parse.urlencode(params, doseq=True)
            response = self.transport(url, {'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}, min(10, remaining))
            if isinstance(response, dict) and 'status' in response:
                status = response['status']
                if status != 200:
                    retry = 900 if status == 429 else 0
                    try:
                        retry = max(retry, min(86400, max(0, int(response.get('headers', {}).get('Retry-After', '0')))))
                    except (ValueError, TypeError, AttributeError):
                        pass
                    raise BillingError(f'OpenAI billing request failed (HTTP {int(status)}).', retry)
                response = response.get('body')
            if isinstance(response, (bytes, str)):
                if len(response) > 2 * 1024 * 1024:
                    raise BillingError('Billing response exceeds size limit.')
                response = json.loads(response)
            if not isinstance(response, dict) or not isinstance(response.get('data'), list):
                raise BillingError('Malformed OpenAI billing response.')
            for bucket in response['data']:
                if not isinstance(bucket, dict):
                    raise BillingError('Malformed billing bucket.')
                stamp = bucket.get('start_time')
                if isinstance(stamp, bool) or not isinstance(stamp, int) or not params['start_time'] <= stamp <= params['end_time']:
                    raise BillingError('Billing bucket outside requested period.')
            pages.extend(response['data'])
            if not response.get('has_more', False):
                return pages
            cursor = response.get('next_page')
            if not isinstance(cursor, str) or not cursor or len(cursor) > 4096 or cursor in seen:
                raise BillingError('Invalid or repeated billing pagination cursor.')
            seen.add(cursor)
            params = {**params, 'page': cursor}
        raise BillingError('Billing pagination limit exceeded; report was not published.')

    def _costs(self, buckets):
        total = Decimal(0)
        daily, projects, keys = {}, {}, {}
        currency = None
        missing = 0
        seen = set()
        for bucket in buckets:
            stamp = bucket.get('start_time')
            if isinstance(stamp, bool) or not isinstance(stamp, int):
                raise BillingError('Malformed billing time bucket.')
            day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
            results = bucket.get('results')
            if not isinstance(results, list):
                raise BillingError('Malformed billing results.')
            for row in results:
                if not isinstance(row, dict):
                    raise BillingError('Malformed billing result row.')
                fingerprint = json.dumps([stamp, row], sort_keys=True)
                if fingerprint in seen:
                    raise BillingError('Duplicate billing result; report was not published.')
                seen.add(fingerprint)
                amount = row.get('amount')
                if not isinstance(amount, dict) or amount.get('value') is None:
                    missing += 1
                    continue
                code = amount.get('currency')
                if not isinstance(code, str) or len(code) != 3 or not code.isascii() or not code.isalpha():
                    raise BillingError('Missing billing currency.')
                if currency and code.lower() != currency:
                    raise BillingError('Mixed billing currencies; totals were not combined.')
                currency = code.lower()
                value = _number(amount['value'])
                total += value
                daily[day] = daily.get(day, Decimal(0)) + value
                project = self._dimension(row.get('project_id')) or '(unattributed)'
                api_key = self._dimension(row.get('api_key_id')) or '(unattributed)'
                projects[project] = projects.get(project, Decimal(0)) + value
                keys[api_key] = keys.get(api_key, Decimal(0)) + value
        return {'currency': currency, 'total': float(total) if not missing else None,
                'known_total': float(total), 'complete': missing == 0, 'missing_amount_count': missing,
                'daily': {k: float(v) for k, v in daily.items()},
                'by_project': {k: float(v) for k, v in projects.items()},
                'by_api_key': {k: float(v) for k, v in keys.items()}}

    @staticmethod
    def _dimension(value):
        if value is not None and (not isinstance(value, str) or len(value) > 300 or value.startswith('sk-') or any(ord(c) < 32 for c in value)):
            raise BillingError('Malformed provider grouping identifier.')
        return value

    def _usage(self, buckets):
        totals = {'requests': 0, 'input_tokens': 0, 'output_tokens': 0}
        groups = []
        for bucket in buckets:
            if not isinstance(bucket, dict) or not isinstance(bucket.get('results'), list):
                raise BillingError('Malformed usage results.')
            for row in bucket['results']:
                if not isinstance(row, dict):
                    raise BillingError('Malformed usage result row.')
                group = {k: self._dimension(row.get(k)) for k in ('project_id', 'api_key_id', 'model')}
                for label, field in [('requests', 'num_model_requests'), ('input_tokens', 'input_tokens'), ('output_tokens', 'output_tokens')]:
                    value = row.get(field)
                    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        raise BillingError('Malformed usage count.')
                    totals[label] += value
                    group[label] = value
                group['start_time'] = bucket.get('start_time')
                groups.append(group)
        return {'scope': 'completions only', **totals, 'groups': groups}

    @staticmethod
    def _safe_error(exc, key, fallback):
        message = str(exc) if isinstance(exc, BillingError) else fallback
        if key and key in message:
            return fallback
        return message

    def refresh(self):
        with self.lock:
            if self._closed:
                raise ValueError('Billing service is closed.')
            if not self._key:
                raise ValueError('Configure a separate Organization Admin API key first.')
            if self._busy:
                raise ValueError('Billing synchronization is already running.')
            now = self.clock()
            if now < self._next:
                raise ValueError('Billing synchronization is cooling down.')
            key, generation = self._key, self._generation
            include_usage = self.config['include_usage']
            self._busy = True
            self._completion.clear()
            self.last_attempt = datetime.fromtimestamp(now, timezone.utc).isoformat()
            self._next = now + 30
        try:
            start = datetime.fromtimestamp(now, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            params = {'start_time': int(start.timestamp()), 'end_time': int(now), 'bucket_width': '1d', 'limit': 31,
                      'group_by': ['project_id', 'api_key_id']}
            deadline = time.monotonic() + 30
            costs = self._costs(self._pages('costs', params, key, deadline))
            usage = {'available': False, 'scope': 'completions only', 'error': 'Usage synchronization disabled.'}
            if include_usage:
                try:
                    usage = {'available': True, **self._usage(self._pages('usage/completions', {**params, 'group_by': ['project_id', 'api_key_id', 'model']}, key, deadline))}
                except Exception as exc:
                    usage = {'available': False, 'scope': 'completions only', 'error': self._safe_error(exc, key, 'Usage report unavailable.')}
                    if getattr(exc, 'retry_after', 0):
                        with self.lock:
                            self._next = max(self._next, self.clock() + exc.retry_after)
            report = {'id': 'openai', 'month': start.strftime('%Y-%m'), 'period_start': start.isoformat(),
                      'period_end': datetime.fromtimestamp(now, timezone.utc).isoformat(),
                      'last_successful_sync': datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                      'synced_at_epoch': self.clock(), 'costs': costs, 'usage': usage, 'partial': not costs['complete'] or (include_usage and not usage['available']), 'delayed': True}
            if key in json.dumps(report):
                raise BillingError('Provider report contained credential material and was discarded.')
            with self.lock:
                if generation == self._generation and not self._closed:
                    self.store.put('billing_reports', report)
                    self.report = report
                    self.error = None
        except Exception as exc:
            # Provider bodies, URLs, exception text and credentials are deliberately not emitted.
            safe = self._safe_error(exc, key, 'Billing request failed; check connectivity, permissions and provider status.')
            with self.lock:
                if generation == self._generation and not self._closed:
                    self.error = safe
                    self._next = max(self._next, self.clock() + getattr(exc, 'retry_after', 0))
        finally:
            with self.lock:
                self._busy = False
                self._completion.set()
                interval = self.config['refresh_interval_seconds']
                if generation == self._generation and interval:
                    self._next = max(self._next, self.clock() + interval)
        return self.state()

    def tick(self):
        with self.lock:
            ready = (not self._closed and self._key and self.config['refresh_interval_seconds'] and not self._busy and self.clock() >= self._next)
        if ready:
            return self.refresh()
        return self.state()

    def start(self):
        with self.lock:
            if self._thread or self._closed:
                return
            def loop():
                while not self._stop.wait(1):
                    try:
                        self.tick()
                    except ValueError:
                        pass
            self._thread = threading.Thread(target=loop, name='genesis-billing', daemon=True)
            self._thread.start()

    def close(self):
        with self.lock:
            self._closed = True
            self._generation += 1
            self._key = None
        self._stop.set()
        self._completion.wait(timeout=1)
        if self._thread:
            self._thread.join(timeout=1)
        with self.lock:
            return not self._busy
