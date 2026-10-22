"""Validate the shared setup in disposable homes; never run Git mutations or MCPs.

Requires Python 3.11+, mise 2026.10.15+, and Codex CLI for rule checks.
Run: python3 -m unittest discover -s tests -p 'test_codex_setup.py' -v
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
MISE = shutil.which("mise")


def codex_executable():
    """Resolve a mise shim while the original tool installation is still visible."""
    candidate = shutil.which("codex")
    if not candidate or not MISE or Path(candidate).resolve() != Path(MISE).resolve():
        return candidate
    result = subprocess.run([MISE, "which", "codex"], capture_output=True, text=True, timeout=20)
    resolved = Path(result.stdout.rstrip("\r\n"))
    if (result.returncode or not resolved.is_absolute() or not resolved.is_file()
            or not os.access(resolved, os.X_OK) or resolved.resolve() == Path(MISE).resolve()):
        raise RuntimeError("Cannot resolve the Codex mise shim before test isolation; check `mise which codex`.")
    return str(resolved)


CODEX = codex_executable()
POLICY_SCRIPT = ROOT / "scripts/codex-integrations.py"
spec = importlib.util.spec_from_file_location("integration_policy", POLICY_SCRIPT)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def load(path):
    return tomllib.loads(path.read_text())


def shared_entries(manifest):
    return {key: value for key, value in load(ROOT / manifest)["dotfiles"].items()
            if key.startswith(("~/.codex/", "~/.agents/skills/"))}


class IsolatedHome(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-setup-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.home / ".codex/config.toml"
        self.config.parent.mkdir()
        self.global_dir = self.home / ".config/mise"
        self.global_dir.mkdir(parents=True)
        (self.root / "empty.toml").write_text("")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("MISE_", "CODEX_"))}
        self.env.update({
            "HOME": str(self.home),
            "CODEX_HOME": str(self.config.parent),
            "MISE_CONFIG_DIR": str(self.global_dir),
            "MISE_GLOBAL_CONFIG_FILE": str(self.global_dir / "config.toml"),
            "MISE_SYSTEM_CONFIG_FILE": str(self.root / "empty.toml"),
            "MISE_DATA_DIR": str(self.root / "data"),
            "MISE_CACHE_DIR": str(self.root / "cache"),
            "MISE_STATE_DIR": str(self.root / "state"),
        })


class ManifestTests(unittest.TestCase):
    def test_platforms_share_existing_sources_with_disjoint_merge_ownership(self):
        entries = shared_entries("mise.toml")
        self.assertEqual(entries, shared_entries("rafiki.toml"))
        self.assertEqual(len(entries), 10)
        owned = set()

        def leaves(data, path=()):
            for key, value in data.items():
                if isinstance(value, dict):
                    yield from leaves(value, path + (key,))
                else:
                    yield path + (key,)

        for entry in entries.values():
            source = ROOT / entry["source"]
            self.assertTrue(source.exists(), str(source))
            if "merge" in entry:
                keys = set(leaves(load(source)))
                self.assertFalse(owned & keys, "Config fragments overlap")
                owned.update(keys)


@unittest.skipUnless(MISE, "requires mise")
class BootstrapTests(IsolatedHome):
    def prepare(self, manifest="rafiki.toml", source_link=True):
        project = self.home / "workspace/mac-setup"
        project.mkdir(parents=True)
        (project / "dotfiles").symlink_to(ROOT / "dotfiles", target_is_directory=True)
        config = project / manifest
        lines = ['min_version = "2026.10.15"', "[settings.history]", "enabled = false", "[dotfiles]"]
        for key, entry in shared_entries(manifest).items():
            fields = ", ".join(
                f"{name} = {str(value).lower() if isinstance(value, bool) else policy.toml_string(value)}"
                for name, value in entry.items()
            )
            lines.append(policy.toml_string(key) + " = { " + fields + " }")
        config.write_text("\n".join(lines) + "\n")
        (self.global_dir / "config.toml").symlink_to(config)
        if source_link:
            (self.global_dir / "dotfiles").symlink_to(project / "dotfiles", target_is_directory=True)
        return project

    def bootstrap(self):
        return subprocess.run(
            [MISE, "-C", str(self.home), "bootstrap", "--only", "dotfiles", "--yes"],
            env=self.env, capture_output=True, text=True, timeout=45,
        )

    def test_existing_config_preserved_and_second_apply_unchanged(self):
        self.prepare()
        self.config.write_text('''# Keep the app's choices.
model = "local-choice"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "danger-full-access"
[mcp_servers.example]
command = "/bin/false"
[mcp_servers.example.env]
TOKEN = "synthetic-private-value"
[desktop]
appearanceDarkCodeThemeId = "tokyo-night"
''')
        personal = self.home / ".agents/skills/personal/SKILL.md"
        personal.parent.mkdir(parents=True)
        personal.write_text("personal skill\n")
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        first = self.config.read_bytes()
        data = load(self.config)
        self.assertEqual(data["model"], "local-choice")
        self.assertEqual(data["model_reasoning_effort"], "medium")
        self.assertEqual(data["sandbox_mode"], "workspace-write")
        self.assertEqual(data["mcp_servers"]["example"]["env"]["TOKEN"], "synthetic-private-value")
        self.assertEqual(data["desktop"]["appearanceDarkCodeThemeId"], "tokyo-night")
        self.assertEqual(data["desktop"]["open-local-url-in-target-preference"], "external-browser")
        self.assertIn(b"# Keep the app's choices.", first)
        self.assertEqual(personal.read_text(), "personal skill\n")
        self.assertEqual(self.bootstrap().returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)

    def test_fresh_macos_config_has_defaults_without_incomplete_mcp_server(self):
        self.prepare("mise.toml")
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = load(self.config)
        self.assertEqual(data["model"], "gpt-6.1-sol")
        self.assertEqual(data["model_reasoning_effort"], "xhigh")
        self.assertNotIn("mcp_servers", data)
        self.assertFalse(self.config.is_symlink())
        if CODEX:
            result = subprocess.run([CODEX, "features", "list"], cwd=self.home,
                                    env=self.env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    def run_update_recipe(self):
        binary_dir = self.home / ".local/bin"
        binary_dir.mkdir(parents=True)
        (binary_dir / "mise").symlink_to(MISE)
        fake_git = binary_dir / "git"
        fake_git.write_text(
            '#!/bin/sh\nif [ "$1" = "-C" ] && [ "$3" = "pull" ]; then exit 0; fi\n'
            + "exec " + shlex.quote(shutil.which("git")) + ' "$@"\n'
        )
        fake_git.chmod(0o700)
        self.env["PATH"] = str(binary_dir) + os.pathsep + self.env["PATH"]
        readme = (ROOT / "README.md").read_text()
        recipe = readme.split("Update after pushing changes:", 1)[1].split("```sh", 1)[1].split("```", 1)[0]
        return subprocess.run(["sh", "-eu", "-c", recipe], cwd=self.home,
                              env=self.env, capture_output=True, text=True, timeout=45)

    def test_readme_update_repairs_old_linux_install_missing_source_link(self):
        self.prepare(source_link=False)
        result = self.run_update_recipe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.global_dir / "dotfiles").is_symlink())
        self.assertEqual(load(self.config)["sandbox_mode"], "workspace-write")

    def test_readme_update_preserves_existing_real_source_directory(self):
        self.prepare(source_link=False)
        directory = self.global_dir / "dotfiles"
        directory.mkdir()
        marker = directory / "personal.txt"
        marker.write_text("preserve this directory\n")
        self.assertNotEqual(self.run_update_recipe().returncode, 0)
        self.assertEqual(marker.read_text(), "preserve this directory\n")
        self.assertFalse(directory.is_symlink())
        self.assertFalse(self.config.exists())

    def test_invalid_toml_is_not_overwritten(self):
        self.prepare()
        original = b'model = [invalid\n'
        self.config.write_bytes(original)
        self.assertNotEqual(self.bootstrap().returncode, 0)
        self.assertEqual(self.config.read_bytes(), original)

    def test_existing_global_instructions_are_not_forced_over(self):
        self.prepare()
        instructions = self.config.parent / "AGENTS.md"
        instructions.write_text("Existing owner instructions\n")
        self.assertNotEqual(self.bootstrap().returncode, 0)
        self.assertEqual(instructions.read_text(), "Existing owner instructions\n")


class IntegrationTests(IsolatedHome):
    def compliant_plugin(self):
        self.config.write_text('''[apps._default]
default_tools_approval_mode = "writes"
approvals_reviewer = "auto_review"
[plugins."runtime@local"]
enabled = true
''')
        cache = self.config.parent / "plugins/cache/local/runtime/1"
        cache.mkdir(parents=True)
        return cache

    def prepare(self):
        self.config.write_text('''# Keep secrets and state local.
model = "local-choice"
[mcp_servers.node_repl]
command = "/bin/false"
args = ["local-argument"]
default_tools_approval_mode = "approve"
[mcp_servers.node_repl.env]
TOKEN = "synthetic-private-value"
[mcp_servers.node_repl.tools.js]
approval_mode = "auto"
[mcp_servers.disabled]
command = "/bin/false"
enabled = false
[apps.example]
default_tools_approval_mode = "approve"
[apps.example.tools.read_or_write]
approval_mode = "auto"
[plugins."runtime@local"]
enabled = true
[plugins."disabled@local"]
enabled = false
''')
        cache = self.config.parent / "plugins/cache/local/runtime/1"
        cache.mkdir(parents=True)
        (cache / ".codex-plugin").mkdir()
        (cache / ".codex-plugin/plugin.json").write_text(json.dumps({
            "name": "runtime", "mcpServers": "./.mcp.json",
        }))
        (cache / ".mcp.json").write_text(json.dumps({"mcpServers": {"kernel": {
            "type": "stdio", "command": "/bin/false", "default_tools_approval_mode": "approve",
            "tools": {"execute": {"approval_mode": "approve"}},
        }}}))

    def run_policy(self, *args):
        return subprocess.run([sys.executable, str(POLICY_SCRIPT), "--config", str(self.config), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=45)

    def test_check_is_read_only_and_never_prints_credentials(self):
        self.prepare()
        original = self.config.read_bytes()
        result = self.run_policy("--check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertNotIn("synthetic-private-value", result.stdout + result.stderr)
        self.assertIn("node_repl", result.stdout)
        self.assertIn("kernel", result.stdout)

    def test_portable_mcp_file_is_audited_even_without_configured_server_overrides(self):
        cache = self.compliant_plugin()
        (cache / "plugin.json").write_text(json.dumps({"name": "runtime", "version": "1"}))
        (cache / "mcp.json").write_text(json.dumps({"mcpServers": {"portable": {
            "type": "streamable-http", "url": "https://example.com/mcp",
        }}}))
        original = self.config.read_bytes()
        result = self.run_policy("--check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("portable / default_tools_approval_mode -> prompt", result.stdout)
        self.assertEqual(self.config.read_bytes(), original)

    def test_declared_mcp_paths_inline_servers_and_compatibility_maps_are_audited(self):
        cache = self.compliant_plugin()
        (cache / ".codex-plugin").mkdir()
        metadata = cache / ".codex-plugin/plugin.json"
        external = cache / "config/servers.json"
        external.parent.mkdir()
        server = {"kernel": {"command": "/bin/false", "tools": {"execute": {}}}}
        external.write_text(json.dumps(server))
        for declaration in ("./config/servers.json", ["./config/servers.json"], server):
            with self.subTest(declaration_type=type(declaration).__name__):
                metadata.write_text(json.dumps({"name": "runtime", "mcpServers": declaration}))
                result = self.run_policy("--check")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("kernel / tools / execute / approval_mode -> prompt", result.stdout)

    def test_known_plugins_without_mcp_can_pass_the_check(self):
        cache = self.compliant_plugin()
        for relative in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            with self.subTest(metadata=relative):
                metadata = cache / relative
                metadata.parent.mkdir(exist_ok=True)
                metadata.write_text(json.dumps({"name": "runtime", "skills": "./skills/"}))
                result = self.run_policy("--check")
                self.assertEqual(result.returncode, 0, result.stderr)
                metadata.unlink()

    def test_portable_openai_extension_replaces_the_compatibility_overlay(self):
        cache = self.compliant_plugin()
        (cache / ".codex-plugin").mkdir()
        (cache / ".codex-plugin/plugin.json").write_text(json.dumps({
            "name": "runtime", "mcpServers": "./missing-legacy.json",
        }))
        (cache / "mcp.json").write_text(json.dumps({"mcpServers": {
            "portable": {"type": "stdio", "command": "/bin/false"},
        }}))
        (cache / "plugin.json").write_text(json.dumps({
            "name": "runtime", "extensions": {"com.openai": {}},
        }))
        result = self.run_policy("--check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("portable / default_tools_approval_mode -> prompt", result.stdout)
        (cache / "plugin.json").write_text(json.dumps({"name": "runtime"}))
        self.assertEqual(self.run_policy("--check").returncode, 2)

    def test_incomplete_plugin_coverage_never_reports_success_or_applies_changes(self):
        cache = self.compliant_plugin()
        original = self.config.read_bytes()
        metadata = cache / "plugin.json"
        cases = {
            "missing_metadata": None,
            "unreadable_format": 'synthetic-private-value invalid json',
            "unsupported_declaration": json.dumps({"name": "runtime", "extensions": {
                "com.openai": {"mcpServers": 42}}}),
            "missing_declared_file": json.dumps({"name": "runtime", "extensions": {
                "com.openai": {"mcpServers": "./missing.json"}}}),
            "out_of_package_file": json.dumps({"name": "runtime", "extensions": {
                "com.openai": {"mcpServers": "./../private.json"}}}),
        }
        for case, content in cases.items():
            with self.subTest(case=case):
                if content is not None:
                    metadata.write_text(content)
                for mode in ("--check", "--apply"):
                    result = self.run_policy(mode)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("Incomplete plugin coverage", result.stderr)
                    self.assertNotIn("synthetic-private-value", result.stdout + result.stderr)
                    self.assertEqual(self.config.read_bytes(), original)
                if metadata.exists():
                    metadata.unlink()
        cache.rmdir()
        result = self.run_policy("--check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Incomplete plugin coverage", result.stderr)

    def test_malformed_mcp_file_and_uninspected_cached_version_are_incomplete(self):
        cache = self.compliant_plugin()
        (cache / "plugin.json").write_text(json.dumps({"name": "runtime"}))
        mcp = cache / "mcp.json"
        for content in ('synthetic-private-value invalid json', '{}'):
            with self.subTest(content=content):
                mcp.write_text(content)
                result = self.run_policy("--check")
                self.assertEqual(result.returncode, 2)
                self.assertIn("Incomplete plugin coverage", result.stderr)
                self.assertNotIn("synthetic-private-value", result.stdout + result.stderr)
        mcp.unlink()
        (cache.parent / "2").mkdir()
        self.assertEqual(self.run_policy("--check").returncode, 2)

    def test_absent_runtime_is_not_registered_and_disabled_integrations_stay_disabled(self):
        self.prepare()
        data = load(self.config)
        del data["mcp_servers"]["node_repl"]
        updates = policy.approval_updates(data, self.config.parent / "plugins/cache")
        self.assertFalse(any("node_repl" in path or "disabled" in path for path in updates))
        self.assertFalse(any(path[-1] in ("command", "env", "enabled") for path in updates))

    def test_invalid_private_config_does_not_leak_in_errors(self):
        original = b'TOKEN = "synthetic-private-value" invalid\n'
        self.config.write_bytes(original)
        result = self.run_policy("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("synthetic-private-value", result.stdout + result.stderr)
        self.assertEqual(self.config.read_bytes(), original)

    @unittest.skipUnless(MISE, "requires mise")
    def test_apply_preserves_transport_credentials_and_is_idempotent(self):
        self.prepare()
        before = load(self.config)
        updates = policy.approval_updates(before, self.config.parent / "plugins/cache")
        expected = copy.deepcopy(before)
        for path, value in updates.items():
            parent = expected
            for part in path[:-1]:
                parent = parent.setdefault(part, {})
            parent[path[-1]] = value
        result = self.run_policy("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = load(self.config)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["mcp_servers"]["node_repl"]["default_tools_approval_mode"], "prompt")
        self.assertEqual(actual["mcp_servers"]["node_repl"]["tools"]["js"]["approval_mode"], "prompt")
        kernel = actual["plugins"]["runtime@local"]["mcp_servers"]["kernel"]
        self.assertEqual(kernel["default_tools_approval_mode"], "prompt")
        self.assertEqual(kernel["tools"]["execute"]["approval_mode"], "prompt")
        self.assertEqual(actual["apps"]["example"]["default_tools_approval_mode"], "writes")
        self.assertEqual(actual["apps"]["example"]["tools"]["read_or_write"]["approval_mode"], "writes")
        self.assertIn("# Keep secrets and state local.", self.config.read_text())
        self.assertNotIn("synthetic-private-value", result.stdout + result.stderr)
        first = self.config.read_bytes()
        self.assertEqual(self.run_policy("--apply").returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)
        self.assertEqual(self.run_policy("--check").returncode, 0)
        if CODEX:
            result = subprocess.run([CODEX, "features", "list"], cwd=self.home,
                                    env=self.env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(MISE, "requires mise")
    def test_apply_handles_unicode_config_paths_and_section_names(self):
        self.config = self.home / ".codex/João 🚀/config.toml"
        self.config.parent.mkdir()
        self.config.write_text('''[mcp_servers.example]
command = "/bin/false"
[mcp_servers.example.tools."execute🚀"]
approval_mode = "approve"
''', encoding="utf-8")
        result = self.run_policy("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = load(self.config)
        self.assertEqual(data["mcp_servers"]["example"]["tools"]["execute🚀"]["approval_mode"], "prompt")
        self.assertEqual(self.run_policy("--check").returncode, 0)

    @unittest.skipUnless(MISE, "requires mise")
    def test_apply_refuses_a_linked_config_without_touching_its_target(self):
        self.prepare()
        target = self.root / "private-config.toml"
        self.config.rename(target)
        original = target.read_bytes()
        self.config.symlink_to(target)
        result = self.run_policy("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(target.read_bytes(), original)
        self.assertTrue(self.config.is_symlink())


class SerializationTests(unittest.TestCase):
    def test_toml_strings_round_trip_unicode_quotes_and_all_control_characters(self):
        value = 'João 🚀 "quoted" \\ path ' + ''.join(chr(n) for n in range(32)) + '\x7f'
        self.assertEqual(tomllib.loads('value = ' + policy.toml_string(value))["value"], value)
        fragment = policy.render_fragment({("apps", value, "approval_mode"): "prompt"})
        self.assertEqual(tomllib.loads(fragment)["apps"][value]["approval_mode"], "prompt")

    def test_non_scalar_unicode_is_rejected(self):
        with self.assertRaises(policy.PolicyError):
            policy.toml_string("invalid\ud800")


@unittest.skipUnless(MISE and CODEX, "requires mise and Codex CLI")
class ExecutableTests(IsolatedHome):
    def test_suite_resolves_a_mise_shim_before_isolating_the_installation(self):
        binary_dir = self.root / "bin"
        binary_dir.mkdir()
        marker = self.root / "resolved.txt"
        fake_mise = binary_dir / "mise"
        fake_mise.write_text(
            '#!/bin/sh\nif [ "${0##*/}" = codex ]; then\n'
            '  echo "Unresolved Codex shim reached isolated environment" >&2; exit 99\nfi\n'
            'if [ "$1" = which ] && [ "$2" = codex ]; then\n'
            '  [ "${MISE_DATA_DIR:-}" = ' + shlex.quote(self.env["MISE_DATA_DIR"]) + ' ] || exit 98\n'
            '  printf "resolved\\n" >> ' + shlex.quote(str(marker)) + '\n'
            '  printf "%s\\n" ' + shlex.quote(CODEX) + '\n  exit 0\nfi\n'
            'exec ' + shlex.quote(MISE) + ' "$@"\n'
        )
        fake_mise.chmod(0o700)
        (binary_dir / "codex").symlink_to(fake_mise)
        self.env["PATH"] = str(binary_dir) + os.pathsep + self.env["PATH"]
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "test_codex_setup.GitRuleTests", "-v"],
            cwd=ROOT / "tests", env=self.env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker.read_text(), "resolved\n")
        self.assertIn("Ran 3 tests", result.stderr)


@unittest.skipUnless(CODEX, "requires Codex CLI")
class GitRuleTests(IsolatedHome):
    def decision(self, tokens):
        result = subprocess.run(
            [CODEX, "execpolicy", "check", "--rules",
             str(ROOT / "dotfiles/codex/rules/owner-git.rules"), "--", *tokens],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout).get("decision")

    def test_direct_push_checkout_and_verification_bypasses_are_forbidden(self):
        for tokens in [["git", "push", "origin", "main"],
                       ["git", "commit", "--no-verify", "-m", "fix"],
                       ["git", "commit", "-n", "-m", "fix"],
                       ["gh", "pr", "checkout", "123"]]:
            with self.subTest(tokens=tokens):
                self.assertEqual(self.decision(tokens), "forbidden")

    def test_merge_staging_commit_and_global_options_are_reviewed(self):
        for tokens in [["git", "merge", "--no-edit", "origin/main"],
                       ["git", "add", "--", "src/file.ts"],
                       ["git", "commit", "--no-edit"],
                       ["git", "commit", "-m", "fix", "--no-verify"],
                       ["git", "-C", "/tmp/example", "push", "origin", "main"],
                       ["git", "-c", "core.hooksPath=/dev/null", "commit", "-m", "fix"],
                       ["gh", "--repo", "example/project", "pr", "checkout", "123"]]:
            with self.subTest(tokens=tokens):
                self.assertEqual(self.decision(tokens), "prompt")

    def test_ordinary_reads_do_not_gain_an_allow_rule_or_prompt(self):
        for tokens in [["git", "status"], ["git", "diff", "--cached"],
                       ["git", "log", "-n", "1"], ["gh", "pr", "view", "123"]]:
            with self.subTest(tokens=tokens):
                self.assertIsNone(self.decision(tokens))


if __name__ == "__main__":
    unittest.main()
