# Gmail Email Report / Notifier for Linux

Read-only Gmail inbox report and desktop notification helper for Linux users who already use the Himalaya email CLI.

## Public-readiness note

This public version is sanitized: it does **not** include a personal Gmail address, password, OAuth token, or private email data.

## What it does

- Uses the local `himalaya` email CLI to read Gmail/IMAP message headers
- Creates a human-readable inbox report
- Highlights likely important messages using local keyword rules
- Can run a simple desktop notifier for new inbox messages
- Does not open, move, delete, or mark emails read

## What it does not do

- Does not include Gmail credentials
- Does not configure OAuth for you
- Does not upload email data anywhere
- Does not send email
- Does not read full message bodies; it uses message headers from Himalaya output

## Requirements

- Linux desktop with `notify-send`
- Python 3
- Himalaya CLI installed and configured for your Gmail/IMAP account

## Configure

Set these environment variables or edit the script constants:

```bash
export GMAIL_REPORT_ACCOUNT="gmail"
export GMAIL_REPORT_EMAIL="you@example.com"
export GMAIL_REPORT_FOLDER="INBOX"
```

The scripts default to:

- account: `gmail`
- email label: `(configured Gmail account)`
- folder: `INBOX`

## Run report

```bash
python3 gmail-email-report.py
```

Default output:

```text
~/Desktop/Gmail_Email_Report.txt
```

## Run notifier once

```bash
python3 gmail-desktop-notifier.py --check-now
```

## Run notifier as daemon

```bash
python3 gmail-desktop-notifier.py --daemon
```

## Privacy / safety

This is a local read-only helper. It depends on your existing Himalaya configuration. Do not commit your Himalaya config, OAuth tokens, app passwords, or generated email reports.

## First-time prerequisite setup

Run:

```bash
./Setup_Prerequisites.sh
```

The setup script checks for Python, desktop notifications, and whether Himalaya appears to be installed. It can try to install common system packages, but it does not configure Gmail credentials for you.

You must install/configure Himalaya for your own Gmail/IMAP account before this tool can read inbox headers.

## Support development

These apps are free/pay-what-you-want so people can actually use them.

If this app helped you, a small tip helps me keep building and improving them.

- Cash App: $jaydubgtfo

## License

No open-source license has been selected yet. Unless a license is added later, all rights are reserved by the author.
