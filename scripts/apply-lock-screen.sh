#!/usr/bin/env sh
set -eu

BATTERY_MINUTES="${1:?battery display sleep in minutes}"
POWER_MINUTES="${2:?power adapter display sleep in minutes}"
LOCK_DELAY="${3:?screen lock delay: immediate, off, or seconds}"
SHOW_USER="${4:?show user name and photo: true or false}"

# Validate values before embedding them in an administrator shell command.
for minutes in "$BATTERY_MINUTES" "$POWER_MINUTES"; do
  case "$minutes" in
    ''|*[!0-9]*) echo "Display sleep must be an integer number of minutes" >&2; exit 1 ;;
  esac
done
case "$LOCK_DELAY" in
  immediate|off) ;;
  0) echo "Use immediate for a zero screen lock delay" >&2; exit 1 ;;
  *[!0-9]*|'') echo "Invalid screen lock delay" >&2; exit 1 ;;
esac
case "$SHOW_USER" in
  true) HIDE_USER=false; HIDE_USER_VALUE=0 ;;
  false) HIDE_USER=true; HIDE_USER_VALUE=1 ;;
  *) echo "Show user name and photo must be true or false" >&2; exit 1 ;;
esac

# Only change power profiles present on this Mac (desktops have no battery).
POWER_SETTINGS="$(pmset -g custom)"
ADMIN_COMMAND=""
for profile in Battery AC; do
  CURRENT_MINUTES="$(printf '%s\n' "$POWER_SETTINGS" | awk -v profile="$profile" '
    /^[^[:space:]]/ { active = ($1 == profile) }
    active && $1 == "displaysleep" { print $2 }
  ')"
  case "$profile" in
    Battery) TARGET_MINUTES="$BATTERY_MINUTES"; POWER_FLAG=-b ;;
    AC) TARGET_MINUTES="$POWER_MINUTES"; POWER_FLAG=-c ;;
  esac
  if [ -n "$CURRENT_MINUTES" ] && [ "$CURRENT_MINUTES" != "$TARGET_MINUTES" ]; then
    ADMIN_COMMAND="${ADMIN_COMMAND}/usr/bin/pmset $POWER_FLAG displaysleep $TARGET_MINUTES && "
  fi
done

# This is a machine preference, not the user's com.apple.loginwindow domain.
CURRENT_HIDE_USER="$(defaults read /Library/Preferences/com.apple.loginwindow HideUserAvatarAndName 2>/dev/null || true)"
if [ "$CURRENT_HIDE_USER" != "$HIDE_USER_VALUE" ]; then
  ADMIN_COMMAND="${ADMIN_COMMAND}/usr/bin/defaults write /Library/Preferences/com.apple.loginwindow HideUserAvatarAndName -bool $HIDE_USER && "
fi
if [ -n "$ADMIN_COMMAND" ]; then
  osascript -e "do shell script \"${ADMIN_COMMAND}true\" with administrator privileges"
fi

# Modern macOS stores this outside com.apple.screensaver defaults.
lock_matches() {
  case "$(sysadminctl -screenLock status 2>&1)" in
    *"screenLock delay is $LOCK_DELAY"|*"screenLock delay is $LOCK_DELAY seconds"|*"screenLock is $LOCK_DELAY") return 0 ;;
    *) return 1 ;;
  esac
}
if ! lock_matches; then
  echo "Setting screen lock delay; enter your Mac account password in the terminal."
  sysadminctl -screenLock "$LOCK_DELAY" -password -
  if ! lock_matches; then
    echo "Screen lock delay was not applied. Run mise bootstrap --only macos-defaults in an interactive terminal and enter your account password." >&2
    exit 1
  fi
fi
