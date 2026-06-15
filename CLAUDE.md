# Gmail assistant — instructions for Claude Code

This project lets you (Claude Code) help me with my Gmail through a small script,
`gmail.py`. Use it when I say things like "check my email", "any emails I need to
reply to?", "draft a reply to that", "find the email from X", or similar.

## How to run it

Every command is `python3 gmail.py <command>`.

| I want to… | Run |
|---|---|
| See unread / recent mail | `python3 gmail.py search "is:unread newer_than:2d"` |
| See a full back-and-forth | `python3 gmail.py threads "from:someone@example.com"` |
| Read one specific email | `python3 gmail.py read <message_id>` |
| **Draft a reply (no send)** | `python3 gmail.py reply <message_id> "reply text" --draft` |
| Draft a brand-new email | `python3 gmail.py draft "to@x.com" "Subject" "body"` |

## The one hard rule: NEVER send without my explicit OK

1. **Always draft first.** When I ask you to reply to something, create a **draft**
   (`reply ... --draft` or `draft ...`). Then show me the exact text you wrote and
   wait. Do **not** run `send`, and do **not** drop the `--draft` flag, until I
   clearly say "send it" / "yes, send" / "looks good, send."
2. **Never delete or modify emails** unless I explicitly ask.
3. When in doubt, draft and ask. A draft is free; a sent email can't be unsent.

## How to actually do a reply (the normal flow)

1. Find the thread: `python3 gmail.py search "is:unread newer_than:2d"` (or a more
   specific query if I named a sender/subject).
2. Read the latest message in it: `python3 gmail.py read <message_id>` — get the
   full context before writing anything.
3. Write a draft reply: `python3 gmail.py reply <message_id> "your draft" --draft`.
   - Match my voice: casual, concise, gets to the point. Sign off as my name or skip
     the sign-off for quick replies.
   - Don't invent facts, dates, or commitments. If a reply needs info you don't have,
     leave a clearly-marked blank like `[confirm date]` and tell me.
4. Show me the draft text and stop. I'll review it in Gmail and tell you to send (or
   tweak it).

## Gmail search operators (handy)

`from:` `to:` `subject:` `is:unread` `has:attachment` `newer_than:2d` `older_than:7d`
`after:2026/06/01` `before:2026/06/10` — combine them, e.g.
`from:billing@x.com subject:invoice newer_than:30d`.
