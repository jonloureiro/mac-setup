# mac-setup

Personal machine setup managed with [mise](https://mise.jdx.dev/bootstrap.html).
`mise.toml` configures macOS; `rafiki.toml` configures Linux.

## macOS

From this checkout, after customizing `[vars]` in `mise.toml` or `mise.local.toml`:

```sh
xcode-select --install
curl -fsSL https://mise.run | sh
mkdir -p ~/.config/mise
ln -sfn "$PWD/mise.toml" ~/.config/mise/config.toml
ln -sfn "$PWD/dotfiles" ~/.config/mise/dotfiles
ln -sfn "$PWD/scripts" ~/.config/mise/scripts
~/.local/bin/mise bootstrap
```

## Linux (rafiki)

Run as `bags`, with GitHub SSH access already configured:

```sh
cd "$HOME"
curl -fsSL https://mise.run | sh
mkdir -p ~/workspace ~/.config/mise
git clone git@github.com:jonloureiro/mac-setup.git ~/workspace/mac-setup
ln -sfn "$HOME/workspace/mac-setup/rafiki.toml" ~/.config/mise/config.toml
ln -sfn "$HOME/workspace/mac-setup/dotfiles" ~/.config/mise/dotfiles
ln -sfn "$HOME/workspace/mac-setup/scripts" ~/.config/mise/scripts
~/.local/bin/mise -C "$HOME" bootstrap --upgrade
exec bash -l
```

Update after pushing changes:

```sh
git -C "$HOME/workspace/mac-setup" pull --ff-only &&
mkdir -p "$HOME/.config/mise" &&
{ [ ! -e "$HOME/.config/mise/dotfiles" ] || [ -L "$HOME/.config/mise/dotfiles" ]; } &&
ln -sfn "$HOME/workspace/mac-setup/dotfiles" "$HOME/.config/mise/dotfiles" &&
~/.local/bin/mise -C "$HOME" bootstrap --upgrade
```

Run Linux bootstrap outside the checkout, as shown. Reconcile any real file or
directory at `~/.config/mise/dotfiles` before updating.

## Codex

Both platforms enable local Codex memories through `dotfiles/codex/memories.toml`.
After updating the checkout, apply only the memory settings with:

```sh
~/.local/bin/mise -C "$HOME" dotfiles apply '~/.codex/config.toml/memories' --yes
```

The global `AGENTS.md` and managed skills are symlinks, so prompt edits are
reflected immediately in the installed files without rerunning bootstrap.

After setup or plugin changes, audit integration approvals from this checkout:

```sh
uv run --script scripts/codex-integrations.py --check
```

Review proposed changes before rerunning with `--apply`.

## SSH port forwarding

Use `rafiki-forward` in Fish on the Mac to manage tunnels to `core@rafiki`.
