#!/usr/bin/env python3
"""
Feishu user token manager
- Exchange auth code to user_access_token + refresh_token
- Auto refresh when token is near expiry

Usage:
  python3 scripts/feishu-token-manager.py exchange --code <CODE>
  python3 scripts/feishu-token-manager.py get

Env required:
  FEISHU_APP_ID
  FEISHU_APP_SECRET
Optional:
  FEISHU_REDIRECT_URI (default: http://47.82.164.74:8787/feishu/oauth/callback)
"""

import argparse
import json
import os
import time
import subprocess
from pathlib import Path

TOKEN_PATH = Path('/root/.openclaw/workspace/output/feishu-user-token.json')
DEFAULT_REDIRECT = 'http://47.82.164.74:8787/feishu/oauth/callback'


def _post(url: str, payload: dict) -> dict:
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST', url, '-H', 'Content-Type: application/json', '-d', json.dumps(payload)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        return {'code': -1, 'msg': 'invalid_json', 'raw': r.stdout}


def _save(data: dict):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _load() -> dict:
    if not TOKEN_PATH.exists():
        return {}
    return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))


def exchange_code(code: str):
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    redirect_uri = os.getenv('FEISHU_REDIRECT_URI', DEFAULT_REDIRECT)
    if not app_id or not app_secret:
        raise SystemExit('Missing FEISHU_APP_ID or FEISHU_APP_SECRET')

    resp = _post(
        'https://open.feishu.cn/open-apis/authen/v2/oauth/token',
        {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
        },
    )
    if resp.get('code') != 0:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    now = int(time.time())
    data = {
        'access_token': resp.get('access_token', ''),
        'refresh_token': resp.get('refresh_token', ''),
        'scope': resp.get('scope', ''),
        'access_expires_at': now + int(resp.get('expires_in', 0)),
        'refresh_expires_at': now + int(resp.get('refresh_token_expires_in', 0)),
        'updated_at': now,
    }
    _save(data)
    print(json.dumps({'ok': True, 'scope': data['scope'], 'has_refresh_token': bool(data['refresh_token'])}, ensure_ascii=False))


def refresh_if_needed(force=False):
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    if not app_id or not app_secret:
        raise SystemExit('Missing FEISHU_APP_ID or FEISHU_APP_SECRET')

    data = _load()
    if not data:
        raise SystemExit('No token file. Run exchange first.')

    now = int(time.time())
    # refresh when <10 min left
    if (not force) and data.get('access_expires_at', 0) - now > 600:
        print(data.get('access_token', ''))
        return

    refresh_token = data.get('refresh_token')
    if not refresh_token:
        raise SystemExit('No refresh_token in store. Re-authorize with offline_access.')

    resp = _post(
        'https://open.feishu.cn/open-apis/authen/v2/oauth/token',
        {
            'grant_type': 'refresh_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'refresh_token': refresh_token,
        },
    )
    if resp.get('code') != 0:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    data.update(
        {
            'access_token': resp.get('access_token', data.get('access_token', '')),
            'refresh_token': resp.get('refresh_token', data.get('refresh_token', '')),
            'scope': resp.get('scope', data.get('scope', '')),
            'access_expires_at': now + int(resp.get('expires_in', 0)),
            'refresh_expires_at': now + int(resp.get('refresh_token_expires_in', 0)),
            'updated_at': now,
        }
    )
    _save(data)
    print(data.get('access_token', ''))


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest='cmd', required=True)

    p1 = sp.add_parser('exchange')
    p1.add_argument('--code', required=True)

    p2 = sp.add_parser('get')
    p2.add_argument('--force-refresh', action='store_true')

    args = p.parse_args()
    if args.cmd == 'exchange':
        exchange_code(args.code)
    elif args.cmd == 'get':
        refresh_if_needed(force=args.force_refresh)


if __name__ == '__main__':
    main()
