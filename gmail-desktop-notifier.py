#!/usr/bin/env python3
"""Generic Gmail/IMAP desktop notifier using Himalaya.

Requires a preconfigured Himalaya account. This script does not include or manage
Gmail credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ACCOUNT = os.environ.get('GMAIL_REPORT_ACCOUNT', 'gmail')
EMAIL = os.environ.get('GMAIL_REPORT_EMAIL', '(configured Gmail account)')
FOLDER = os.environ.get('GMAIL_REPORT_FOLDER', 'INBOX')
PAGE_SIZE = os.environ.get('GMAIL_REPORT_PAGE_SIZE', '15')
INTERVAL_SECONDS = int(os.environ.get('GMAIL_REPORT_INTERVAL_SECONDS', str(15 * 60)))
MAX_NOTIFY_LINES = int(os.environ.get('GMAIL_REPORT_MAX_NOTIFY_LINES', '5'))

HOME = Path.home()
HIMALAYA = Path(os.environ.get('HIMALAYA_BIN', str(HOME / '.local/bin/himalaya')))
STATE_DIR = HOME / '.local/state/gmail-email-report-notifier'
STATE_FILE = STATE_DIR / 'notifier_state.json'
PID_FILE = STATE_DIR / 'notifier.pid'
LOG_FILE = STATE_DIR / 'notifier.log'


def log(msg: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec='seconds')
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f'[{stamp}] {msg}\n')


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {'seen_ids': []}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {'seen_ids': []}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding='utf-8')
    tmp.replace(STATE_FILE)


def notify(title: str, body: str, urgency: str = 'normal') -> None:
    subprocess.run([
        'notify-send', '--app-name=Gmail Report Notifier', '--icon=mail-unread',
        f'--urgency={urgency}', title, body,
    ], check=False, timeout=15)


def fetch_inbox() -> list[dict]:
    cmd = [str(HIMALAYA), 'envelope', 'list', '--account', ACCOUNT, '--folder', FOLDER, '--page-size', PAGE_SIZE, '--output', 'json']
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip())
    out = proc.stdout.strip()
    idx = out.find('[')
    if idx > 0:
        out = out[idx:]
    return json.loads(out or '[]')


def sender_text(item: dict) -> str:
    sender = item.get('from') or {}
    return sender.get('name') or sender.get('addr') or '(unknown sender)'


def format_messages(items: list[dict]) -> str:
    lines = []
    for item in items[:MAX_NOTIFY_LINES]:
        lines.append(f"• {sender_text(item)} — {item.get('subject') or '(no subject)'}")
    if len(items) > MAX_NOTIFY_LINES:
        lines.append(f'…and {len(items) - MAX_NOTIFY_LINES} more')
    return '\n'.join(lines) or 'No messages found.'


def update_seen(inbox: list[dict], state: dict) -> None:
    seen = list(state.get('seen_ids') or [])
    current_ids = [str(item.get('id')) for item in inbox if item.get('id')]
    state['seen_ids'] = list(dict.fromkeys(current_ids + seen))[:300]
    state['last_checked'] = datetime.now().isoformat(timespec='seconds')
    save_state(state)


def check_once(manual: bool = False) -> int:
    state = load_state()
    seen = set(state.get('seen_ids') or [])
    inbox = fetch_inbox()
    if manual:
        update_seen(inbox, state)
        notify(f'Gmail: {len(inbox)} recent inbox message(s)', format_messages(inbox), 'normal' if inbox else 'low')
        return 0
    if not seen:
        update_seen(inbox, state)
        log('Baseline created; no notification sent.')
        return 0
    new_items = [item for item in inbox if str(item.get('id')) not in seen]
    update_seen(inbox, state)
    if new_items:
        notify(f'Gmail: {len(new_items)} new message(s)', format_messages(new_items), 'normal')
        log(f'Notified for {len(new_items)} new message(s).')
    return len(new_items)


def pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ensure_single_instance() -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if old_pid and pid_is_running(old_pid):
                return False
        except Exception:
            pass
    PID_FILE.write_text(str(os.getpid()))
    return True


def daemon() -> int:
    if not ensure_single_instance():
        notify('Gmail Report Notifier is already running', EMAIL, 'low')
        return 0
    notify('Gmail Report Notifier started', 'I will check for new Gmail messages periodically.', 'low')
    log('Daemon started.')
    try:
        while True:
            try:
                check_once(manual=False)
            except Exception as e:
                log(f'Check error: {e}')
                notify('Gmail Report Notifier error', str(e)[:900], 'normal')
            time.sleep(INTERVAL_SECONDS)
    finally:
        try:
            if PID_FILE.read_text().strip() == str(os.getpid()):
                PID_FILE.unlink()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--check-now', action='store_true')
    args = parser.parse_args()
    if args.daemon:
        return daemon()
    return check_once(manual=True)


if __name__ == '__main__':
    sys.exit(main())
