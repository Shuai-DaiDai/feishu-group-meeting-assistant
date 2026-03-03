#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone, timedelta


def post(url: str, token: str, body: dict) -> dict:
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST', url,
         '-H', f'Authorization: Bearer {token}',
         '-H', 'Content-Type: application/json; charset=utf-8',
         '-d', json.dumps(body, ensure_ascii=False)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        return {'code': -1, 'msg': 'invalid_json', 'raw': r.stdout}


def parse_iso(s: str) -> int:
    return int(datetime.fromisoformat(s).timestamp())


def merge_busy(items, start_ts: int, end_ts: int):
    b = []
    for it in items or []:
        a = parse_iso(it['start_time'])
        z = parse_iso(it['end_time'])
        if z <= start_ts or a >= end_ts:
            continue
        b.append((max(a, start_ts), min(z, end_ts)))
    b.sort()
    out = []
    for a, z in b:
        if not out or a > out[-1][1]:
            out.append([a, z])
        else:
            out[-1][1] = max(out[-1][1], z)
    return [(a, z) for a, z in out]


def free_from_busy(busy, start_ts: int, end_ts: int):
    cur = start_ts
    out = []
    for a, z in busy:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, z)
    if cur < end_ts:
        out.append((cur, end_ts))
    return out


def intersect(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if e > s:
            out.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', required=True)
    p.add_argument('--user-id-type', choices=['user_id', 'open_id'], default='user_id')
    p.add_argument('--user-id', action='append', required=True, help='repeat --user-id for each user (max 10)')
    p.add_argument('--time-min', required=True, help='RFC3339, e.g. 2026-03-03T19:00:00+08:00')
    p.add_argument('--time-max', required=True, help='RFC3339, e.g. 2026-03-03T23:59:00+08:00')
    p.add_argument('--min-minutes', type=int, default=30)
    args = p.parse_args()

    url = f'https://open.feishu.cn/open-apis/calendar/v4/freebusy/batch?user_id_type={args.user_id_type}'
    body = {
        'time_min': args.time_min,
        'time_max': args.time_max,
        'user_ids': args.user_id,
        'include_external_calendar': True,
        'only_busy': True,
        'need_rsvp_status': True,
    }
    resp = post(url, args.token, body)
    if resp.get('code') != 0:
        print(json.dumps({'ok': False, 'error': resp}, ensure_ascii=False))
        return

    start_ts = parse_iso(args.time_min)
    end_ts = parse_iso(args.time_max)
    data = resp.get('data', {})
    lists = data.get('freebusy_lists', []) or []

    busy_map = {}
    for it in lists:
        uid = it.get('user_id')
        busy_map[uid] = merge_busy(it.get('freebusy_items', []), start_ts, end_ts)

    missing = [u for u in args.user_id if u not in busy_map]

    tz = timezone(timedelta(hours=8))
    fmt = lambda ts: datetime.fromtimestamp(ts, tz).strftime('%H:%M')

    free_common = []
    if len(args.user_id) >= 2 and all(u in busy_map for u in args.user_id[:2]):
        f1 = free_from_busy(busy_map[args.user_id[0]], start_ts, end_ts)
        f2 = free_from_busy(busy_map[args.user_id[1]], start_ts, end_ts)
        inter = intersect(f1, f2)
        min_sec = args.min_minutes * 60
        free_common = [
            {'start': fmt(a), 'end': fmt(z), 'minutes': int((z - a) / 60)}
            for a, z in inter if z - a >= min_sec
        ]

    print(json.dumps({
        'ok': True,
        'id_source': 'input_user_ids',
        'missing_user_ids': missing,
        'busy': {
            uid: [[fmt(a), fmt(z)] for a, z in busy_map.get(uid, [])]
            for uid in args.user_id
        },
        'common_free': free_common,
        'raw_count': len(lists),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
