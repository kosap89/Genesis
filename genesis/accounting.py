"""Reporting-only model prices and token estimates; never settles budget reservations."""
from __future__ import annotations

import math
from .models import model_info

PRICE_FIELDS = ('input_cost_per_million', 'cached_input_cost_per_million', 'output_cost_per_million')


def validate_prices(value):
    if not isinstance(value, dict) or set(value) != set(PRICE_FIELDS):
        raise ValueError('Provide input, cached input and output USD prices per million tokens.')
    result = {}
    for name in PRICE_FIELDS:
        rate = value[name]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 <= rate <= 100000:
            raise ValueError('Reporting prices must be finite numbers between 0 and 100000.')
        result[name] = float(rate)
    if result['cached_input_cost_per_million'] > result['input_cost_per_million']:
        raise ValueError('Cached input price cannot exceed uncached input price.')
    return result


def prices_for(provider, model, overrides=None):
    info = model_info(provider, model)
    if not info or not info.get('pricing'):
        return None
    prices = dict(info['pricing'])
    if provider == 'openai' and model in (overrides or {}):
        prices.update((overrides or {})[model])
    return prices


def estimate_cost(provider, model, input_tokens, output_tokens, cached_input_tokens=0, overrides=None):
    prices = prices_for(provider, model, overrides)
    if prices is None:
        return None
    if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens, cached_input_tokens)) or cached_input_tokens > input_tokens:
        return None
    threshold = prices.get('long_context_threshold')
    long = threshold is not None and input_tokens > threshold
    im = prices.get('long_input_multiplier', 1) if long else 1
    om = prices.get('long_output_multiplier', 1) if long else 1
    return (((input_tokens - cached_input_tokens) * prices['input_cost_per_million'] +
             cached_input_tokens * prices['cached_input_cost_per_million']) * im +
            output_tokens * prices['output_cost_per_million'] * om) / 1e6


def conservative_rates(config):
    """Preserve configured guards; raise them when known route prices exceed them.

    Reporting overrides are intentionally not accepted here. Long-context rates
    bound known standard-price routes; byte-based reservation remains unchanged.
    """
    inp, out = config['input_cost_per_million'], config['output_cost_per_million']
    for route in [config, *config.get('fallbacks', [])]:
        info = model_info(route.get('provider'), route.get('model'))
        if info and info.get('pricing'):
            p = info['pricing']
            inp = max(inp, p['input_cost_per_million'] * p.get('long_input_multiplier', 1))
            out = max(out, p['output_cost_per_million'] * p.get('long_output_multiplier', 1))
    return inp, out


def usage_details(metadata):
    """Counts within provider totals; never add reasoning tokens to output again."""
    metadata = metadata or {}
    usage = metadata.get('raw_usage') or metadata.get('usage') or {}
    cached = metadata.get('cached_input_tokens')
    reasoning = metadata.get('reasoning_output_tokens')
    if cached is None and isinstance(usage, dict):
        cached = (usage.get('input_tokens_details') or {}).get('cached_tokens')
    if reasoning is None and isinstance(usage, dict):
        reasoning = (usage.get('output_tokens_details') or {}).get('reasoning_tokens')
    return (cached if type(cached) is int and cached >= 0 else None,
            reasoning if type(reasoning) is int and reasoning >= 0 else None)


def accounting_summary(store):
    """Reconstruct both old and new usage without rewriting historical charges."""
    settings = store.get('settings', 'global')
    overrides = settings.get('pricing_overrides', {})
    events = store.events(limit=10000000)
    responses = [e for e in events if e['action'] == 'model_response']
    requests = [e for e in events if e['action'] == 'model_request']
    report = dict(conservative_charged_usd=settings['spent_usd'], reserved_usd=settings['reserved_usd'],
                  estimated_cost_usd=0.0, estimate_complete=True, input_tokens=0, output_tokens=0,
                  cached_input_tokens=0, reasoning_output_tokens=0, request_count=len(requests),
                  response_count=len(responses), unpriced_responses=0, cache_usage_unknown_responses=0,
                  known_billable_attempt_count=len(responses), unknown_usage_attempts=0,
                  incomplete_usage_responses=0, official_billed_usd=None,
                  pricing_basis='Current standard published prices (or reporting overrides); not an invoice. Unknown caching is estimated as uncached input.')
    # Old response events lack detailed usage but the matching assistant message
    # may contain it. Pair oldest-first within each task, including legacy history.
    metadata = {}
    for task in store.all('tasks'):
        metadata[task['id']] = [m.get('provider_data', {}) for m in store.messages(task['id']) if m['role'] == 'assistant']
    positions = {}
    for e in reversed(responses):
        tid = e.get('task_id')
        pos = positions.get(tid, 0)
        details = metadata.get(tid, [])
        md = details[pos] if pos < len(details) else {}
        positions[tid] = pos + 1
        inp, out = e.get('input_tokens', 0), e.get('output_tokens', 0)
        prior = md.get('_prior_billable_attempts', 0)
        if type(prior) is int and prior > 0:
            report['known_billable_attempt_count'] += prior
            report['unknown_usage_attempts'] += prior
        cached, reasoning = usage_details(md)
        cached = e.get('cached_input_tokens', cached)
        reasoning = e.get('reasoning_output_tokens', reasoning)
        report['input_tokens'] += inp
        report['output_tokens'] += out
        if cached is None:
            report['cache_usage_unknown_responses'] += 1
        else:
            report['cached_input_tokens'] += cached
        if reasoning is not None:
            report['reasoning_output_tokens'] += reasoning
        complete = e.get('usage_complete', md.get('usage_complete', True))
        if not complete:
            report['incomplete_usage_responses'] += 1
        value = estimate_cost(e.get('provider'), e.get('model'), inp, out, cached or 0, overrides)
        if value is None or not complete:
            report['unpriced_responses'] += 1
        else:
            report['estimated_cost_usd'] += value
    for event in events:
        if event['action'] == 'model_error':
            attempts = event.get('billable_attempts')
            if type(attempts) is int and attempts > 0:
                report['known_billable_attempt_count'] += attempts
                report['unknown_usage_attempts'] += attempts
    report['estimate_complete'] = not (report['unpriced_responses'] or report['unknown_usage_attempts'] or report['cache_usage_unknown_responses'] or len(requests) != len(responses))
    return report
