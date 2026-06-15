#!/usr/bin/env bash
# One-command setup: creates an isolated virtual environment and installs deps.
# Works the same whether your Python came from python.org, Homebrew, or the system.
set -e

cd "$(dirname "$0")"

echo "Creating virtual environment in .venv ..."
python3 -m venv .venv

echo "Installing dependencies ..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo
echo "Done. Next:"
echo "  .venv/bin/python gmail.py setup     # one-time Google login"
echo "  then just run 'claude' in this folder and ask it about your email."
