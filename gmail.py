#!/usr/bin/env python3
"""
Gmail assistant for Claude Code.

A tiny command-line tool that lets an AI agent (Claude Code) search, read,
and DRAFT replies to your Gmail. It can also send — but the included CLAUDE.md
tells the agent to NEVER send without your explicit approval.

Usage:
  python3 gmail.py setup                          # One-time OAuth setup
  python3 gmail.py search "is:unread newer_than:2d"# Search emails
  python3 gmail.py read <message_id>              # Read a specific email
  python3 gmail.py threads "from:someone@x.com"   # Show full threads
  python3 gmail.py draft <to> <subject> <body>    # Create a draft (no send)
  python3 gmail.py reply <message_id> <body> --draft  # Draft a threaded reply
  python3 gmail.py reply <message_id> <body>      # Send a threaded reply
  python3 gmail.py send <to> <subject> <body>     # Send a new email

Credentials + config are stored in ~/.config/claude-gmail/
(override with the CLAUDE_GMAIL_HOME environment variable).
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]

DAILY_SEND_LIMIT = 500
RATE_LIMIT_DELAY = 0.25

CONFIG_DIR = Path(os.environ.get("CLAUDE_GMAIL_HOME", Path.home() / ".config" / "claude-gmail"))
SEND_LOG_PATH = CONFIG_DIR / "send_log.json"
CONFIG_PATH = CONFIG_DIR / "config.json"


# ---------------------------------------------------------------------------
# Config (your name — used in the "From" line on replies you send)
# ---------------------------------------------------------------------------
def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def _get_sender_name() -> str:
    return _load_config().get("name", "")


def _get_profile_email(service) -> str:
    """The authenticated account's address — always matches who you logged in as."""
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


# ---------------------------------------------------------------------------
# Send-rate safety
# ---------------------------------------------------------------------------
def _load_send_log() -> dict:
    if SEND_LOG_PATH.exists():
        with open(SEND_LOG_PATH) as f:
            return json.load(f)
    return {}


def _save_send_log(log: dict):
    SEND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEND_LOG_PATH, "w") as f:
        json.dump(log, f)


def _get_today_send_count() -> int:
    return _load_send_log().get(date.today().isoformat(), 0)


def _increment_send_count():
    log = _load_send_log()
    today = date.today().isoformat()
    log[today] = log.get(today, 0) + 1
    _save_send_log(log)


def _check_send_limit():
    count = _get_today_send_count()
    if count >= DAILY_SEND_LIMIT:
        print(f"ERROR: Daily send limit reached ({count}/{DAILY_SEND_LIMIT}).")
        sys.exit(1)


def _rate_limit():
    time.sleep(RATE_LIMIT_DELAY)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def setup():
    """Run the one-time OAuth flow."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    creds_path = CONFIG_DIR / "client_secret.json"
    if not creds_path.exists():
        print(f"No credentials found at {creds_path}")
        print()
        print("Setup steps:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Enable the Gmail API in APIs & Services > Library")
        print("3. Create an OAuth 2.0 Client ID (Application type: Desktop app)")
        print("4. Download the JSON file")
        print(f"5. Save it to: {creds_path}")
        print("6. Re-run: python3 gmail.py setup")
        sys.exit(1)

    print("Starting OAuth flow — a browser window will open.")
    print("Log in as the Gmail account you want the assistant to use.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = CONFIG_DIR / "token.json"
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    # Stamp the authenticated address into config for reference.
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    email = _get_profile_email(service)
    config = _load_config()
    config.setdefault("email", email)
    config.setdefault("name", "")
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Authenticated as {email}")
    print(f"Token saved to {token_path}")
    print(f"Optional: set your display name in {CONFIG_PATH} (\"name\": \"...\")")


def get_service():
    """Get an authenticated Gmail API service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_path = CONFIG_DIR / "token.json"
    if not token_path.exists():
        print("No token found. Run: python3 gmail.py setup")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"ERROR: Token refresh failed: {e}")
            print("Re-run: python3 gmail.py setup")
            sys.exit(1)

    if not creds or not creds.valid:
        print("ERROR: Token is invalid. Re-run: python3 gmail.py setup")
        sys.exit(1)

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def extract_body(payload: dict) -> str:
    """Extract plain-text body from an email payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            if "parts" in part:
                result = extract_body(part)
                if result and result != "(no body)":
                    return result

    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return "[HTML content]\n" + base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return "(no body)"


def search_emails(query: str, max_results: int = 10):
    service = get_service()
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No messages found.")
        return

    print(f"Found {len(messages)} message(s):\n")
    for msg_info in messages:
        _rate_limit()
        msg = service.users().messages().get(
            userId="me", id=msg_info["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        print(f"  ID: {msg_info['id']}")
        print(f"  Date: {headers.get('Date', 'unknown')}")
        print(f"  From: {headers.get('From', 'unknown')}")
        print(f"  Subject: {headers.get('Subject', '(no subject)')}")
        print(f"  Preview: {msg.get('snippet', '')[:100]}...")
        print()


def read_email(message_id: str):
    service = get_service()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

    print(f"From: {headers.get('From', 'unknown')}")
    print(f"To: {headers.get('To', 'unknown')}")
    print(f"Date: {headers.get('Date', 'unknown')}")
    print(f"Subject: {headers.get('Subject', '(no subject)')}")
    print(f"Message-ID: {headers.get('Message-ID', '')}")
    print(f"Thread ID: {msg.get('threadId', '')}")
    print("---\n")
    print(extract_body(msg["payload"]))


def show_threads(query: str, max_results: int = 5):
    service = get_service()
    results = service.users().threads().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    threads = results.get("threads", [])
    if not threads:
        print("No threads found.")
        return

    for thread_info in threads:
        _rate_limit()
        thread = service.users().threads().get(
            userId="me", id=thread_info["id"], format="full"
        ).execute()
        messages = thread.get("messages", [])
        first = {h["name"]: h["value"] for h in messages[0]["payload"]["headers"]}
        print(f"=== Thread: {first.get('Subject', '(no subject)')} ({len(messages)} messages) ===")
        print(f"    Thread ID: {thread_info['id']}\n")
        for msg in messages:
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = extract_body(msg["payload"])
            print(f"  [{headers.get('Date', '')}]  From: {headers.get('From', '')}")
            print(f"  ---")
            print(f"  {body[:500]}{'...' if len(body) > 500 else ''}\n")
        print()


# ---------------------------------------------------------------------------
# Compose (draft / send / reply)
# ---------------------------------------------------------------------------
def _build_message(service, to: str, subject: str, body: str, reply_to_id: str = None):
    """Build a MIME message; if reply_to_id is set, thread + auto-fill recipients."""
    email = _get_profile_email(service)
    name = _get_sender_name()
    sender = f"{name} <{email}>" if name else email

    message = MIMEMultipart("alternative")
    message["From"] = sender
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    thread_id = None
    if reply_to_id:
        original = service.users().messages().get(
            userId="me", id=reply_to_id, format="metadata",
            metadataHeaders=["Message-ID", "Subject", "From", "To", "Cc"]
        ).execute()
        oh = {h["name"]: h["value"] for h in original["payload"]["headers"]}

        if not to:
            recipients = set()
            if oh.get("From"):
                recipients.add(oh["From"])
            for key in ("To", "Cc"):
                for addr in oh.get(key, "").split(","):
                    addr = addr.strip()
                    if addr and email.lower() not in addr.lower():
                        recipients.add(addr)
            to = ", ".join(recipients)

        message["In-Reply-To"] = oh.get("Message-ID", "")
        message["References"] = oh.get("Message-ID", "")
        thread_id = original.get("threadId")

        orig_subject = oh.get("Subject", "")
        if not subject.lower().startswith("re:"):
            message.replace_header("Subject", f"Re: {orig_subject}")

    message["To"] = to
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return raw, thread_id, to, message["Subject"]


def create_draft(to: str, subject: str, body: str, reply_to_id: str = None):
    service = get_service()
    raw, thread_id, to, subj = _build_message(service, to, subject, body, reply_to_id)
    draft_msg = {"raw": raw}
    if thread_id:
        draft_msg["threadId"] = thread_id
    draft = service.users().drafts().create(
        userId="me", body={"message": draft_msg}
    ).execute()
    print("Draft created.")
    print(f"  Draft ID: {draft['id']}")
    print(f"  To: {to}")
    print(f"  Subject: {subj}")
    print("  Open Gmail to review before sending.")


def send_email(to: str, subject: str, body: str, reply_to_id: str = None):
    _check_send_limit()
    service = get_service()
    raw, thread_id, to, subj = _build_message(service, to, subject, body, reply_to_id)
    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id
    result = service.users().messages().send(userId="me", body=send_body).execute()
    _increment_send_count()
    print("Email sent.")
    print(f"  Message ID: {result['id']}")
    print(f"  To: {to}")
    print(f"  Subject: {subj}")
    print(f"  Daily sends: {_get_today_send_count()}/{DAILY_SEND_LIMIT}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Gmail assistant for Claude Code")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="One-time OAuth setup")

    p = sub.add_parser("search", help="Search emails")
    p.add_argument("query")
    p.add_argument("-n", "--max", type=int, default=10)

    p = sub.add_parser("read", help="Read a specific email")
    p.add_argument("message_id")

    p = sub.add_parser("threads", help="Search and show full threads")
    p.add_argument("query")
    p.add_argument("-n", "--max", type=int, default=5)

    p = sub.add_parser("draft", help="Create a draft (no send)")
    p.add_argument("to")
    p.add_argument("subject")
    p.add_argument("body")

    p = sub.add_parser("reply", help="Reply to an email (threaded)")
    p.add_argument("message_id")
    p.add_argument("body")
    p.add_argument("--draft", action="store_true", help="Create as draft instead of sending")

    p = sub.add_parser("send", help="Send a new email")
    p.add_argument("to")
    p.add_argument("subject")
    p.add_argument("body")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "setup":
        setup()
    elif args.command == "search":
        search_emails(args.query, args.max)
    elif args.command == "read":
        read_email(args.message_id)
    elif args.command == "threads":
        show_threads(args.query, args.max)
    elif args.command == "draft":
        create_draft(args.to, args.subject, args.body)
    elif args.command == "reply":
        if args.draft:
            create_draft("", "", args.body, reply_to_id=args.message_id)
        else:
            send_email("", "", args.body, reply_to_id=args.message_id)
    elif args.command == "send":
        send_email(args.to, args.subject, args.body)


if __name__ == "__main__":
    main()
