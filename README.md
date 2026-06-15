# Claude Gmail — an AI that drafts your email replies

A tiny Python script that gives **Claude Code** access to your Gmail so it can read
your inbox and **draft your replies** for you — right in your terminal. It can send,
too, but the bundled `CLAUDE.md` instructs the AI to **never send anything without
your explicit OK**. Drafts only, until you say go.

No monthly SaaS. No Zapier. You own the script and the credentials.

> Companion to the video: **"I Connected AI to My Email and It Now Drafts My Replies."**

---

## What you need

- **git** and **Python 3.9+** (`git --version` / `python3 --version` to check)
- **[Claude Code](https://claude.com/claude-code)** — install with `curl -fsSL https://claude.ai/install.sh | bash`
  (or `brew install --cask claude-code`). Needs a paid Claude plan (Pro or Max).
- A **Google account** (a throwaway one is perfect for trying this out)
- ~15 minutes

## Setup (one time)

### 1. Get the code + install dependencies

```bash
git clone https://github.com/saadnvd1/claude-gmail.git
cd claude-gmail
./setup.sh
```

`setup.sh` creates an isolated virtual environment in `.venv` and installs the dependencies
into it. This works the same whether your Python came from python.org, Homebrew, or the system.
(Manual equivalent: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.)

> **Why a venv?** On many Macs the Homebrew/system Python is "externally managed" and a plain
> `pip install` fails. The venv sidesteps that entirely — and keeps this project's packages
> separate from everything else. From here on, run the script as **`.venv/bin/python gmail.py …`**.

### 2. Turn on the Gmail API + get your credentials

This is the part most tutorials skip. Do it once and you're done.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a
   new project (top bar → project dropdown → **New Project**).
2. **APIs & Services → Library** → search **Gmail API** → **Enable**.
3. **APIs & Services → OAuth consent screen** → choose **External** → fill in an app
   name + your email → **Save**. Under **Audience / Test users**, add the Gmail
   address you'll use. (Leaving the app in "Testing" is fine — it just means only
   your test users can authorize it, which is exactly what you want.)
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** →
   Application type **Desktop app** → **Create** → **Download JSON**.
5. Save that file as `client_secret.json` inside `~/.config/claude-gmail/`:
   ```bash
   mkdir -p ~/.config/claude-gmail
   mv ~/Downloads/client_secret_*.json ~/.config/claude-gmail/client_secret.json
   ```

### 3. Authorize

```bash
.venv/bin/python gmail.py setup
```

A browser opens. Log in as the Google account you want the assistant to use. You'll
see an **"unverified app"** warning — that's normal, because *you* are the app and
you haven't gone through Google's verification (you don't need to). Click
**Advanced → Go to (your app) → Continue**, then allow access.

Done. Your token is saved to `~/.config/claude-gmail/token.json`.

### 4. (Optional) Set your name

So replies you send have a nice "From" line:

```bash
echo '{"name": "Your Name"}' > ~/.config/claude-gmail/config.json
```

---

## Use it with Claude Code

From inside the repo folder, just run `claude` and talk to it:

```
> any emails I need to reply to?
> draft a reply to the one from Sarah saying I can do Thursday
> actually make it Friday
> send it
```

Claude reads the `CLAUDE.md` in this repo, so it knows to **draft first and wait for
your OK** before sending anything.

## Use it directly (no AI)

The script works on its own, too (use the venv's Python):

```bash
.venv/bin/python gmail.py search "is:unread newer_than:2d"
.venv/bin/python gmail.py read <message_id>
.venv/bin/python gmail.py reply <message_id> "Sounds good, Friday works." --draft
```

| Command | What it does |
|---|---|
| `setup` | One-time OAuth |
| `search "<query>"` | List matching emails (Gmail search syntax) |
| `read <id>` | Print one email in full |
| `threads "<query>"` | Show full back-and-forth threads |
| `draft <to> <subject> <body>` | Create a draft (no send) |
| `reply <id> <body> --draft` | Draft a threaded reply |
| `reply <id> <body>` | Send a threaded reply |
| `send <to> <subject> <body>` | Send a new email |

---

## Safety notes

- **Your credentials never leave your machine.** `client_secret.json` and `token.json`
  live in `~/.config/claude-gmail/` and are git-ignored. Never commit them.
- The `CLAUDE.md` rule is "draft, never send without approval." Keep it that way until
  you trust it.
- Want to revoke access anytime? Delete the project in Google Cloud Console, or remove
  the app at [myaccount.google.com/permissions](https://myaccount.google.com/permissions).
- The OAuth scopes here are read + compose/send. There's **no delete scope** — the
  script can't trash your mail.
