# Gmail assistant — instructions for Claude Code

This project lets you (Claude Code) help me with my Gmail through a small script,
`gmail.py`. Use it when I say things like "check my email", "any emails I need to
reply to?", "draft a reply to that", "find the email from X", or similar.

## Before running anything: use the project's virtual environment

This project keeps its Python dependencies in a local virtual environment (`.venv`).
This is required — on many Macs the system/Homebrew Python is "externally managed" and a
plain `pip install` will fail.

1. **If `.venv/` does not exist yet**, create it once:
   ```bash
   ./setup.sh
   ```
   (or, equivalently: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`)

2. **Always run the script with the venv's Python** — never bare `python3`:
   ```bash
   .venv/bin/python gmail.py <command>
   ```
   Bare `python3 gmail.py` uses the global Python, which doesn't have the libraries and will fail.

## How to run it

Every command is `.venv/bin/python gmail.py <command>`.

| I want to… | Run |
|---|---|
| See unread / recent mail | `.venv/bin/python gmail.py search "is:unread newer_than:2d"` |
| See a full back-and-forth | `.venv/bin/python gmail.py threads "from:someone@example.com"` |
| Read one specific email | `.venv/bin/python gmail.py read <message_id>` |
| **Draft a reply (no send)** | `.venv/bin/python gmail.py reply <message_id> "reply text" --draft` |
| Draft a brand-new email | `.venv/bin/python gmail.py draft "to@x.com" "Subject" "body"` |

## The one hard rule: NEVER send without my explicit OK

1. **Always draft first.** When I ask you to reply to something, create a **draft**
   (`reply ... --draft` or `draft ...`). Then show me the exact text you wrote and
   wait. Do **not** run `send`, and do **not** drop the `--draft` flag, until I
   clearly say "send it" / "yes, send" / "looks good, send."
2. **Never delete or modify emails** unless I explicitly ask.
3. When in doubt, draft and ask. A draft is free; a sent email can't be unsent.

## How to actually do a reply (the normal flow)

1. Find the thread: `.venv/bin/python gmail.py search "is:unread newer_than:2d"` (or a more
   specific query if I named a sender/subject).
2. Read the latest message in it: `.venv/bin/python gmail.py read <message_id>` — get the
   full context before writing anything.
3. Write a draft reply: `.venv/bin/python gmail.py reply <message_id> "your draft" --draft`.
   - Match my voice: casual, concise, gets to the point. Sign off as my name or skip
     the sign-off for quick replies.
   - Don't invent facts, dates, or commitments. If a reply needs info you don't have,
     leave a clearly-marked blank like `[confirm date]` and tell me.
4. Show me the draft text and stop. I'll review it in Gmail and tell you to send (or
   tweak it).

## If a command fails

- `the Google API libraries aren't installed` → the venv isn't set up (or you used bare
  `python3`). Run `./setup.sh`, then use `.venv/bin/python`.
- `No token found` / `Token refresh failed` → I need to log in: tell me to run
  `.venv/bin/python gmail.py setup`.

## Gmail search operators (handy)

`from:` `to:` `subject:` `is:unread` `has:attachment` `newer_than:2d` `older_than:7d`
`after:2026/06/01` `before:2026/06/10` — combine them, e.g.
`from:billing@x.com subject:invoice newer_than:30d`.
