# mac-setup

Personal machine setup managed with [mise](https://mise.jdx.dev/bootstrap.html).
`mise.toml` configures macOS; `rafiki.toml` configures Linux with GitHub CLI,
uv, Codex CLI, Herdr, and Fish at `latest`.

mise installs `brew:` packages directly; Homebrew itself is not required.

## macOS

Install the prerequisites:

```sh
xcode-select --install
curl -fsSL https://mise.run | sh
```

Customize `[vars]` in `mise.toml`, or override them in `mise.local.toml`.
From this checkout:

```sh
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
ln -sfn "$HOME/workspace/mac-setup/scripts" ~/.config/mise/scripts
~/.local/bin/mise -C "$HOME" bootstrap --upgrade
exec bash -l
```

Bash remains the login shell and starts Fish in interactive terminals.
SSH commands keep Bash, with mise tools on `PATH`.

Update after pushing changes:

```sh
git -C "$HOME/workspace/mac-setup" pull --ff-only
~/.local/bin/mise -C "$HOME" bootstrap --upgrade
```

Apply Linux configuration from the home directory, as shown, so mise does
not load the macOS configuration from the checkout.

## SSH port forwarding

From Fish on the Mac, forward ports to `core@rafiki`:

```fish
rafiki-forward                 # Status
rafiki-forward 8080 8000        # Open ports
rafiki-forward stop 8080 8001   # Stop specific ports
rafiki-forward stop all        # Stop all managed tunnels
```
