#!/usr/bin/env sh
set -eu

cd "$HOME"
perl_bin="$(mise which perl)"
"$perl_bin" -MJSON::PP -MFile::Path -MIO::Socket::UNIX -MList::Util -e 1

plugins="$(mise exec -- herdr plugin list)"
if ! printf '%s\n' "$plugins" | grep -Fq 'shibayu36.equalize-panes'; then
    mise exec -- herdr plugin install --yes shibayu36/herdr-equalize-panes
fi

plugin_root="$(mise exec -- herdr plugin list --plugin shibayu36.equalize-panes --json |
    "$perl_bin" -MJSON::PP -0777 -ne 'print(decode_json($_)->{result}{plugins}[0]{plugin_root} // die "Plugin root missing\n")')"

# The upstream script hardcodes /usr/bin/perl; use the complete mise runtime.
test -x "$plugin_root/equalize-panes"
"$perl_bin" -i -pe 's{\A#![^\r\n]*}{#!$^X} if $. == 1' "$plugin_root/equalize-panes"
mise exec -- herdr plugin enable shibayu36.equalize-panes >/dev/null
