#!/usr/bin/env sh
set -eu

# Install Keka from official DMG (bypasses mise ditto xattr issue)
if [ ! -d "/Applications/Keka.app" ]; then
  DMG="/tmp/Keka.dmg"
  MNT="/tmp/keka-mnt"

  curl -fsSL https://d.keka.io/ -o "$DMG"
  hdiutil attach "$DMG" -nobrowse -quiet -mountpoint "$MNT"
  cp -R "$MNT/Keka.app" /Applications/
  hdiutil detach "$MNT" -quiet || true
  rm -f "$DMG"
fi

# Install herdr equalize-panes plugin
if ! /opt/homebrew/bin/herdr plugin list | grep -q "shibayu36.equalize-panes"; then
  /opt/homebrew/bin/herdr plugin install -y shibayu36/herdr-equalize-panes
fi
