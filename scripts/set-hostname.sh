#!/usr/bin/env sh
set -eu

# Set macOS ComputerName, LocalHostName, and HostName when different from target.
TARGET_HOST="${1:-mufasa}"
CURRENT_LOCAL="$(scutil --get LocalHostName 2>/dev/null || true)"
CURRENT_COMP="$(scutil --get ComputerName 2>/dev/null || true)"

if [ "$CURRENT_LOCAL" != "$TARGET_HOST" ] || [ "$CURRENT_COMP" != "$TARGET_HOST" ]; then
  osascript -e "do shell script \"scutil --set ComputerName $TARGET_HOST && scutil --set LocalHostName $TARGET_HOST && scutil --set HostName $TARGET_HOST\" with administrator privileges"
fi
