#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
source ~/.zprofile 2>/dev/null
unset CLAUDECODE
cd /Users/hh/.discord-news-notion || exit 1
exec /opt/homebrew/opt/python@3.14/bin/python3.14 /Users/hh/.discord-news-notion/main.py
