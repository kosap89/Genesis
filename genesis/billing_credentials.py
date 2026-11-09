"""Configure a separate session-only billing Admin key through hidden local input."""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings


def local_url(value):
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('Use the local Genesis http://127.0.0.1:PORT address.') from None
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost'}
            or parsed.username or parsed.password or parsed.path not in {'', '/'}
            or parsed.query or parsed.fragment or not port or not 1 <= port <= 65535):
        raise argparse.ArgumentTypeError('Use the local Genesis http://127.0.0.1:PORT address.')
    return urllib.parse.urlunsplit(('http', parsed.netloc, '', '', ''))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(opener, request):
    with opener.open(request, timeout=10) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Local response too large.')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid local response.')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description='Set a separate OpenAI billing Admin key with hidden input; never saves it to disk.')
    parser.add_argument('--url', type=local_url, default='http://127.0.0.1:8787')
    parser.add_argument('--clear', action='store_true', help='Clear only the current billing Admin credential.')
    args = parser.parse_args(argv)
    secret = None
    payload = None
    try:
        # Loopback secrets must never follow environment-configured HTTP proxies.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)
        state = request_json(opener, urllib.request.Request(args.url + '/api/state'))
        token = state.get('csrf_token')
        if not isinstance(token, str) or not 1 <= len(token) <= 256:
            raise ValueError('Missing local session token.')
        if args.clear:
            payload = {'clear': True}
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                secret = getpass.getpass('OpenAI Organization Admin key (hidden; this Genesis session only): ')
            if (not secret.startswith('sk-admin-') or len(secret) > 4096
                    or any(ord(c) < 33 or ord(c) > 126 for c in secret)):
                raise ValueError('Use an Organization Admin key.')
            payload = {'admin_api_key': secret}
        request = urllib.request.Request(args.url + '/api/billing/credentials',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-Genesis-CSRF': token}, method='POST')
        result = request_json(opener, request)
        if result.get('credential_configured') is not (not args.clear):
            raise ValueError('Unexpected credential status.')
        print('Billing Admin credential cleared.' if args.clear else
              'Billing Admin credential saved only in the current Genesis server process. Model credentials and budgets are unchanged.')
        return 0
    except (KeyboardInterrupt, EOFError, getpass.GetPassWarning):
        print('Cancelled or hidden input unavailable. Run this command in a local interactive terminal.', file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError):
        # Never echo exception text, response bodies, tokens or supplied secrets.
        print('Billing credential setup failed. Check the local server and use a separate Organization Admin key; no secret was printed or saved by this helper.', file=sys.stderr)
        return 1
    finally:
        secret = None
        payload = None


if __name__ == '__main__':
    raise SystemExit(main())
