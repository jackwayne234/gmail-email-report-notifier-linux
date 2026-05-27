#!/usr/bin/env python3
"""Create a human-readable Gmail/IMAP inbox report using Himalaya.

Read-only: lists message headers only; does not open, move, delete, or mark
messages read.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

ACCOUNT = os.environ.get('GMAIL_REPORT_ACCOUNT', 'gmail')
EMAIL = os.environ.get('GMAIL_REPORT_EMAIL', '(configured Gmail account)')
FOLDER = os.environ.get('GMAIL_REPORT_FOLDER', 'INBOX')
PAGE_SIZE = os.environ.get('GMAIL_REPORT_PAGE_SIZE', '60')
HIMALAYA = Path(os.environ.get('HIMALAYA_BIN', str(Path.home() / '.local/bin/himalaya')))
REPORT_PATH = Path(os.environ.get('GMAIL_REPORT_OUTPUT', str(Path.home() / 'Desktop' / 'Gmail_Email_Report.txt')))

IMPORTANT_KEYWORDS = [
    'security', 'alert', 'verify', 'verification', 'password', 'login', 'sign-in', 'signin',
    'account', 'suspicious', 'unauthorized', 'fraud', 'charge', 'payment', 'paid', 'due',
    'overdue', 'invoice', 'bill', 'statement', 'bank', 'paypal', 'refund', 'order',
    'delivery', 'appointment', 'calendar', 'meeting', 'interview', 'deadline', 'urgent',
    'action required', 'important', 'document', 'tax', 'insurance', 'medical', 'legal',
    'support',
]
LOW_PRIORITY_KEYWORDS = ['sale', 'deals', 'coupon', 'promo', 'newsletter', 'unsubscribe', 'offer', 'discount']


def fetch_inbox() -> list[dict]:
    cmd = [str(HIMALAYA), 'envelope', 'list', '--account', ACCOUNT, '--folder', FOLDER, '--page-size', PAGE_SIZE, '--output', 'json']
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip())
    out = proc.stdout.strip()
    idx = out.find('[')
    if idx > 0:
        out = out[idx:]
    return json.loads(out or '[]')


def sender_text(item: dict) -> str:
    sender = item.get('from') or {}
    name = sender.get('name') or ''
    addr = sender.get('addr') or ''
    return f'{name} <{addr}>' if name and addr else (name or addr or '(unknown sender)')


def item_text(item: dict) -> str:
    return f"{sender_text(item)} {item.get('subject') or ''}".lower()


def matching_keywords(item: dict, keywords: list[str]) -> list[str]:
    text = item_text(item)
    found = []
    for kw in keywords:
        if ' ' in kw or '-' in kw:
            if kw in text:
                found.append(kw)
        elif re.search(rf'(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])', text):
            found.append(kw)
    return found


def is_unread(item: dict) -> bool:
    flags = [str(f).lower() for f in (item.get('flags') or [])]
    return bool(flags and 'seen' not in flags and '\\seen' not in flags)


def importance(item: dict) -> tuple[int, list[str]]:
    important_hits = matching_keywords(item, IMPORTANT_KEYWORDS)
    low_hits = matching_keywords(item, LOW_PRIORITY_KEYWORDS)
    score = 0
    if important_hits:
        score += 10 + len(important_hits)
    if item.get('has_attachment'):
        score += 2
    if is_unread(item):
        score += 2
    if low_hits and not important_hits:
        score -= 4
    return score, important_hits


def line_for(item: dict) -> str:
    attach = ' +attachment' if item.get('has_attachment') else ''
    return f"ID {item.get('id', '?')} | {item.get('date', '(no date)')}{attach}\nFrom: {sender_text(item)}\nSubject: {item.get('subject') or '(no subject)'}"


def decision_for(item: dict) -> tuple[str, str]:
    text = item_text(item)
    sender = sender_text(item).lower()
    subject = (item.get('subject') or '').lower()
    if 'google' in sender and any(x in subject for x in ['security alert', 'sign-in', 'password']):
        return ('HANDLE TODAY', 'Open directly from Gmail or Google Account; do not click suspicious links.')
    if any(x in sender for x in ['paypal', 'bank']) or any(x in subject for x in ['charge', 'payment', 'invoice', 'bill', 'statement', 'refund']):
        return ('REVIEW TODAY', 'Check whether this is expected money/account activity.')
    if 'calendar' in sender or 'calendar' in subject or 'appointment' in subject or 'meeting' in subject:
        return ('REVIEW SCHEDULE', 'Check whether this affects today or tomorrow.')
    if any(x in subject for x in ['job', 'career', 'application', 'interview', 'hiring']):
        return ('REVIEW WHEN JOB-HUNTING', 'Career-related. Open if actively job searching.')
    if any(x in text for x in LOW_PRIORITY_KEYWORDS):
        return ('SAFE TO SKIM/IGNORE', 'Likely promotion/newsletter. Archive/delete later if desired.')
    return ('QUICK REVIEW', 'No obvious danger, but scan sender/subject and decide if it needs a reply.')


def build_report(inbox: list[dict]) -> str:
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    scored = [(importance(item), item) for item in inbox]
    important = [(score_kw, item) for score_kw, item in scored if score_kw[0] > 0]
    low_priority = [item for score_kw, item in scored if score_kw[0] < 0]
    important.sort(key=lambda pair: pair[0][0], reverse=True)
    decision_order = ['HANDLE TODAY', 'REVIEW TODAY', 'REVIEW SCHEDULE', 'REVIEW WHEN JOB-HUNTING', 'QUICK REVIEW', 'SAFE TO SKIM/IGNORE']
    buckets: dict[str, list[tuple[dict, str]]] = {name: [] for name in decision_order}
    for item in inbox:
        bucket, rec = decision_for(item)
        buckets.setdefault(bucket, []).append((item, rec))
    lines: list[str] = []
    lines.append('GMAIL EMAIL REPORT')
    lines.append('=' * 60)
    lines.append(f'Account: {EMAIL}')
    lines.append(f'Generated: {now}')
    lines.append(f'Inbox messages checked: latest {len(inbox)}')
    lines.append('Read-only report: no emails were opened, moved, deleted, or marked read.')
    lines.append('')
    lines.append('WHAT I WOULD DO FIRST')
    lines.append('-' * 60)
    lines.append('1. Handle account/security items first.')
    lines.append('2. Review money/payment/account items today.')
    lines.append('3. Skip promos/newsletters until later.')
    lines.append('')
    lines.append('DECISION LIST')
    lines.append('-' * 60)
    for bucket in decision_order:
        items = buckets.get(bucket, [])
        if not items:
            continue
        lines.append(f'{bucket} ({len(items)})')
        for item, rec in items[:12]:
            lines.append(f"- {sender_text(item)} — {item.get('subject') or '(no subject)'}")
            lines.append(f'  Decision: {rec}')
        if len(items) > 12:
            lines.append(f'  ...and {len(items) - 12} more in this bucket.')
        lines.append('')
    lines.append('IMPORTANT / DO-NOT-MISS')
    lines.append('-' * 60)
    if important:
        for (score, kws), item in important[:20]:
            lines.append(line_for(item))
            if kws:
                lines.append(f'Matched: {", ".join(kws)}')
            lines.append('')
    else:
        lines.append('No obvious important/urgent messages found in the latest inbox scan.')
        lines.append('')
    lines.append('RECENT INBOX SUMMARY')
    lines.append('-' * 60)
    for item in inbox[:30]:
        tag = 'IMPORTANT' if any(item is imp_item for _, imp_item in important) else 'normal'
        if item in low_priority:
            tag = 'likely promo/newsletter'
        lines.append(f'[{tag}] {line_for(item)}')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    inbox = fetch_inbox()
    report = build_report(inbox)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding='utf-8')
    print(f'Wrote report: {REPORT_PATH}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
