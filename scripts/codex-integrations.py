#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Audit existing integration approvals; --apply merges policy keys using mise.

Never launch MCP servers, copy transports/credentials, or enable integrations.
The default check is read-only. Use --apply only as an explicit setup action.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib


class PolicyError(Exception):
    """A diagnostic authored here, safe to display without config payloads."""


def table(data, *parts):
    if not isinstance(data, dict):
        raise PolicyError("An integration setting expected to be a table is invalid.")
    for part in parts:
        data = data.get(part, {})
        if not isinstance(data, dict):
            raise PolicyError("An integration setting expected to be a table is invalid.")
    return data


def plugin_servers(cache, plugin_id):
    """Inspect cached plugin metadata and MCP declarations, or fail closed."""
    name, separator, marketplace = plugin_id.rpartition("@")
    if not separator or not all(p not in (".", "..") and re.fullmatch(r"[A-Za-z0-9_.-]+", p)
                                for p in (name, marketplace)):
        raise PolicyError("Incomplete plugin coverage: unsupported plugin identifier.")
    servers = {}

    def include(content):
        for server, settings in table(content).items():
            servers.setdefault(server, set()).update(table(settings, "tools"))

    def read_object(path):
        return table(json.loads(path.read_text(encoding="utf-8")))

    def declared_file(root, relative):
        if (not isinstance(relative, str) or not relative.startswith("./")
                or ".." in Path(relative).parts):
            raise PolicyError("Unsupported MCP file declaration.")
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise PolicyError("Missing or out-of-package MCP file.")
        return path

    try:
        versions = sorted(p for p in (cache / marketplace / name).iterdir() if p.is_dir())
        if not versions:
            raise PolicyError("No cached plugin version.")
        # Inspect every cached version conservatively; the cache alone does not
        # establish which version every client has loaded.
        for root in versions:
            portable = root / "plugin.json"
            legacy = next((p for p in (root / ".codex-plugin/plugin.json",
                                      root / ".claude-plugin/plugin.json") if p.is_file()), None)
            if portable.is_file():
                metadata = read_object(portable)
                extensions = table(metadata, "extensions")
                overlay = extensions.get("com.openai")
                if "com.openai" in extensions:
                    overlay = table(overlay)
                else:
                    overlay = read_object(legacy) if legacy else {}
            elif legacy:
                metadata = overlay = read_object(legacy)
            else:
                raise PolicyError("Missing plugin metadata.")
            if not isinstance(metadata.get("name"), str) or not metadata["name"]:
                raise PolicyError("Invalid plugin metadata.")

            manifests = {root / filename for filename in ("mcp.json", ".mcp.json")
                         if (root / filename).exists()}
            if "mcpServers" in overlay:
                declaration = overlay["mcpServers"]
                if isinstance(declaration, dict):
                    include(declaration)
                else:
                    paths = declaration if isinstance(declaration, list) else [declaration]
                    manifests.update(declared_file(root, path) for path in paths)
            for manifest in sorted(manifests):
                content = read_object(manifest)
                if "mcpServers" in content:
                    include(content["mcpServers"])
                elif manifest.name != "mcp.json":
                    # Compatibility files also support an unwrapped server map.
                    include(content)
                else:
                    raise PolicyError("Portable MCP file lacks mcpServers.")
    except (PolicyError, ValueError, OSError):
        # Do not print parser exceptions or declarations: they can carry secrets.
        raise PolicyError(
            f"Incomplete plugin coverage for {plugin_id}: missing, unreadable, or unsupported "
            "plugin metadata/MCP declarations. Inspect this plugin's cache privately. "
            "No configuration was written."
        ) from None
    return servers


def approval_updates(data, cache):
    """Return only policy leaves; never include an existing setting's value."""
    updates = {}

    def set_value(path, value):
        if table(data, *path[:-1]).get(path[-1]) != value:
            updates[path] = value

    set_value(("apps", "_default", "default_tools_approval_mode"), "writes")
    set_value(("apps", "_default", "approvals_reviewer"), "auto_review")
    for app, settings in table(data, "apps").items():
        settings = table(settings)
        if app == "_default" or settings.get("enabled") is False:
            continue
        base = ("apps", app)
        if settings.get("default_tools_approval_mode") in ("auto", "approve"):
            set_value(base + ("default_tools_approval_mode",), "writes")
        for tool, policy in table(settings, "tools").items():
            if policy.get("approval_mode") in ("auto", "approve"):
                set_value(base + ("tools", tool, "approval_mode"), "writes")

    def review_server(base, settings, manifest_tools=()):
        settings = table(settings)
        if settings.get("enabled") is False:
            return
        # Interpreters can hide effects behind a read-only tool annotation.
        # Review all calls, including node_repl and browser-scoped runtimes.
        set_value(base + ("default_tools_approval_mode",), "prompt")
        tools = set(table(settings, "tools")) | set(manifest_tools)
        for tool in tools:
            set_value(base + ("tools", tool, "approval_mode"), "prompt")

    for server, settings in table(data, "mcp_servers").items():
        review_server(("mcp_servers", server), settings)

    for plugin, settings in table(data, "plugins").items():
        settings = table(settings)
        if settings.get("enabled") is not True:
            continue
        configured = table(settings, "mcp_servers")
        manifests = plugin_servers(cache, plugin)
        for server in set(configured) | set(manifests):
            review_server(("plugins", plugin, "mcp_servers", server),
                          configured.get(server, {}), manifests.get(server, ()))
    return dict(sorted(updates.items()))


def toml_string(value):
    """Quote a TOML basic string without JSON's UTF-16 surrogate escapes."""
    parts = []
    for character in value:
        code = ord(character)
        if 0xD800 <= code <= 0xDFFF:
            raise PolicyError("A TOML string contains invalid Unicode scalar values.")
        if character in ('"', "\\"):
            parts.append("\\" + character)
        elif code < 0x20 or code == 0x7F:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(character)
    return '"' + "".join(parts) + '"'


def render_fragment(updates):
    sections = {}
    for path, value in updates.items():
        sections.setdefault(path[:-1], {})[path[-1]] = value
    lines = []
    for path, values in sections.items():
        lines.append("[" + ".".join(toml_string(p) for p in path) + "]")
        lines.extend(f"{toml_string(key)} = {toml_string(value)}"
                     for key, value in values.items())
        lines.append("")
    return "\n".join(lines)


def apply_policy(config, original, data, updates):
    mise = shutil.which("mise")
    if not mise:
        raise PolicyError("mise 2026.10.15 or newer is required to apply policy.")
    if config.is_symlink():
        raise PolicyError("Reconcile the config.toml symlink before applying policy.")
    if config.read_bytes() != original:
        raise PolicyError("Configuration changed during the audit; run the check again.")
    expected = copy.deepcopy(data)
    for path, value in updates.items():
        parent = expected
        for part in path[:-1]:
            parent = parent.setdefault(part, {})
        parent[path[-1]] = value
    with tempfile.TemporaryDirectory(prefix="codex-integration-policy-") as tmp:
        root = Path(tmp)
        source = root / "policy.toml"
        source.write_text(render_fragment(updates), encoding="utf-8")
        (root / "empty.toml").write_text("", encoding="utf-8")
        (root / "mise.toml").write_text(
            'min_version = "2026.10.15"\n[settings.history]\nenabled = false\n[dotfiles]\n'
            + toml_string(str(config) + "/integrations")
            + " = { source = " + toml_string(str(source)) + ", merge = true }\n",
            encoding="utf-8",
        )
        env = {k: v for k, v in os.environ.items() if not k.startswith("MISE_")}
        env.update({
            "MISE_CONFIG_DIR": str(root / "config"),
            "MISE_GLOBAL_CONFIG_FILE": str(root / "empty.toml"),
            "MISE_SYSTEM_CONFIG_FILE": str(root / "empty.toml"),
            "MISE_DATA_DIR": str(root / "data"),
            "MISE_CACHE_DIR": str(root / "cache"),
            "MISE_STATE_DIR": str(root / "state"),
        })
        result = subprocess.run(
            [mise, "-C", str(root), "bootstrap", "--only", "dotfiles", "--yes"],
            env=env, text=True, capture_output=True, timeout=60,
        )
        if result.returncode:
            # Native diagnostics can contain credential-bearing TOML lines.
            raise PolicyError("mise refused the merge; configuration details were not printed.")
    if tomllib.loads(config.read_text(encoding="utf-8")) != expected:
        raise PolicyError("Configuration differs from the planned result; inspect it locally. No automatic rollback was attempted.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser.add_argument("--config", type=Path, default=codex_home / "config.toml")
    parser.add_argument("--plugin-cache", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only check (default)")
    mode.add_argument("--apply", action="store_true", help="merge approval keys into the selected existing config")
    args = parser.parse_args()
    config = args.config.expanduser().absolute()
    if not config.exists():
        print("No local config to audit. Check again after the client registers integrations.")
        return 0
    original = config.read_bytes()
    data = tomllib.loads(original.decode())
    cache = args.plugin_cache or config.parent / "plugins" / "cache"
    updates = approval_updates(data, cache)
    if not updates:
        print("Existing integration approval keys match the policy. Runtime behavior was not tested.")
        return 0
    for path, value in updates.items():
        print(" / ".join(path) + " -> " + value)
    if not args.apply:
        print("Changes required. No configuration was written; use --apply as an explicit setup action.")
        return 1
    apply_policy(config, original, data, updates)
    print("Approval policy merged. Transports, credentials, enabled states, and unrelated settings preserved.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PolicyError as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, subprocess.SubprocessError):
        # Avoid exception payloads: they may expose local config or MCP credentials.
        print("Integration policy check/apply failed. Inspect the selected config and local manifests privately; no credential values were printed.", file=sys.stderr)
        sys.exit(2)
