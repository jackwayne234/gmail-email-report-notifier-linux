#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$HOME/.local/state/gmail-email-report-notifier"
PID_FILE="$STATE_DIR/notifier.pid"
mkdir -p "$STATE_DIR"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  notify-send --app-name='Gmail Report Notifier' --icon=mail-unread 'Gmail Report Notifier' 'Already running. Creating report now...' 2>/dev/null || true
else
  nohup python3 "$HERE/gmail-desktop-notifier.py" --daemon >> "$STATE_DIR/notifier.out" 2>&1 &
  sleep 1
fi
python3 "$HERE/gmail-email-report.py"
