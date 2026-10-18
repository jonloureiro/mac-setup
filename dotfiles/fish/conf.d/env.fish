set -g fish_greeting

# Ensure mise, Homebrew, and libpq (psql) binaries are on PATH.
fish_add_path --path --move $HOME/.local/bin
fish_add_path --path /opt/homebrew/opt/libpq/bin /opt/homebrew/bin /opt/homebrew/sbin
