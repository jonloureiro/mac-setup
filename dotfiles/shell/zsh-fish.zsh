# Keep zsh as login shell and replace interactive sessions with fish.
[[ -o interactive && -t 0 && -t 1 ]] || return
[[ ${MAC_SETUP_NO_FISH:-0} == 1 ]] && return
command -v /opt/homebrew/bin/fish >/dev/null 2>&1 || return

autoload -Uz add-zsh-hook
_mac_setup_exec_fish() {
  add-zsh-hook -d precmd _mac_setup_exec_fish
  export SHELL=/opt/homebrew/bin/fish
  exec /opt/homebrew/bin/fish
}
add-zsh-hook precmd _mac_setup_exec_fish
