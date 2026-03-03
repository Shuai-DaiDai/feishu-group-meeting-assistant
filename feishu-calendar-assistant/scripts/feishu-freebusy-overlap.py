#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
from typing import List, Tuple


def run_curl(url: str, token: str):
    r = subprocess.run(['curl', '-s', url, '-H', f'Authorization: Bearer {token}'], capture_output=True, text=True)
    return json.loads(r.stdout or '{}')


def list_events(calendar_id: str, token: str, start_ts: int, end_ts: int) -> list:
    page = ''
    items = []
    while True:
        url = f'https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events?start_time={start_ts}&end_time={end_ts}&page_size=50'
        if page:
            url += f'&page_token={page}'
        d = run_curl(url, token)
        data = d.get('data', {})
        items.extend(data.get('items', []) or [])
        if not data.get('has_more'):
            break
        page = data.get('page_token', '')
        if not page:
            break
    return items


def merge_busy(events: list, start_ts: int, end_ts: int) -> List[Tuple[int, int]]:
    busy = []
    for it in events:
        if it.get('status') == 'cancelled':
            continue
        st = int((it.get('start_time', {}) or {}).get('timestamp', '0') or 0)
        ed = int((it.get('end_time', {}) or {}).get('timestamp', '0') or 0)
        if ed <= start_ts or st >= end_ts:
            continue
        busy.append((max(st, start_ts), min(ed, end_ts)))
    busy.sort()
    merged = []
    for a, b in busy:
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    return [(a, b) for a, b in merged]


def free_from_busy(merged_busy, start_ts, end_ts):
    cur = start_ts
    out = []
    for a, b in merged_busy:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
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
    p.add_argument('--calendar-a', required=True)
    p.add_argument('--calendar-b', required=True)
    p.add_argument('--date', required=True, help='YYYY-MM-DD in Asia/Shanghai')
    p.add_argument('--start', default='16:00')
    p.add_argument('--end', default='23:59')
    p.add_argument('--min-minutes', type=int, default=60)
    args = p.parse_args()

    tz = dt.timezone(dt.timedelta(hours=8))
    y, m, d = map(int, args.date.split('-'))
    sh, sm = map(int, args.start.split(':'))
    eh, em = map(int, args.end.split(':'))
    start_ts = int(dt.datetime(y, m, d, sh, sm, tzinfo=tz).timestamp())
    end_ts = int(dt.datetime(y, m, d, eh, em, tzinfo=tz).timestamp())

    ea = list_events(args.calendar_a, args.token, start_ts, end_ts)
    eb = list_events(args.calendar_b, args.token, start_ts, end_ts)
    ba = merge_busy(ea, start_ts, end_ts)
    bb = merge_busy(eb, start_ts, end_ts)
    fa = free_from_busy(ba, start_ts, end_ts)
    fb = free_from_busy(bb, start_ts, end_ts)
    inter = intersect(fa, fb)
    min_s = args.min_minutes * 60

    def fmt(ts):
        return dt.datetime.fromtimestamp(ts, tz).strftime('%H:%M')

    slots = [
        {'start': fmt(a), 'end': fmt(b), 'minutes': int((b - a) / 60)}
        for a, b in inter if b - a >= min_s
    ]
    print(json.dumps({'slots': slots, 'busy_a': [[fmt(a), fmt(b)] for a, b in ba], 'busy_b': [[fmt(a), fmt(b)] for a, b in bb]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
