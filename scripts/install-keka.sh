#!/usr/bin/env sh
set -eu

# Install Keka from official DMG (bypasses mise ditto xattr issue)
if [ -d "/Applications/Keka.app" ]; then
  exit 0
fi

DMG="/tmp/Keka.dmg"
MNT="/tmp/keka-mnt"

curl -fsSL https://d.keka.io/ -o "$DMG"
hdiutil attach "$DMG" -nobrowse -quiet -mountpoint "$MNT"
cp -R "$MNT/Keka.app" /Applications/
hdiutil detach "$MNT" -quiet || true
rm -f "$DMG"
