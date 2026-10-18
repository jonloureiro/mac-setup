# mac-setup

Declarative macOS setup managed with [mise](https://mise.jdx.dev/bootstrap.html).

## Usage

1. Install Xcode Command Line Tools and `mise`:
   ```sh
   xcode-select --install
   curl https://mise.run | sh
   ```

2. Customize variables in `mise.toml` under `[vars]` (or override them in `mise.local.toml`):
   ```toml
   [vars]
   hostname = "mufasa"
   git_name = "Your Name"
   git_email = "you@example.com"
   docker_host = "ssh://user@host"
   wallpaper_rgb = "247 201 160"
   ```

3. Link config and run bootstrap:
   ```sh
   mkdir -p ~/.config/mise
   ln -sfn "$PWD/mise.toml" ~/.config/mise/config.toml
   ln -sfn "$PWD/dotfiles" ~/.config/mise/dotfiles
   ln -sfn "$PWD/scripts" ~/.config/mise/scripts
   ~/.local/bin/mise bootstrap
   ```
