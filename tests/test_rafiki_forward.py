"""Exercise the Fish command with isolated SSH and lsof substitutes.

No real SSH connection, user config, or production control directory is used.
The tests use real Unix socket files and macOS lockf for lifecycle/concurrency.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dotfiles/fish/functions/rafiki-forward.fish"
FISH = shutil.which("fish")

FAKE_COMMAND = r'''#!/usr/bin/python3
import fcntl, json, os, socket, sys, time
from pathlib import Path

db = Path(os.environ["RAFIKI_TEST_DB"])
with open(str(db) + ".guard", "a") as guard:
    fcntl.flock(guard, fcntl.LOCK_EX)
    data = json.loads(db.read_text())
    args = sys.argv[1:]
    if Path(sys.argv[0]).name == "lsof":
        port = next(a.split(":", 1)[1] for a in args if a.startswith("-iTCP:"))
        if port in data["active"] or port in data.get("occupied", []):
            print("98765")
            sys.exit(0)
        sys.exit(1)

    control = Path(args[args.index("-S") + 1])
    port = control.stem[1:]
    if "-O" in args:
        action = args[args.index("-O") + 1]
        if action == "check":
            sys.exit(0 if port in data["active"] else 255)
        assert action == "exit", args
        if port in data.get("fail_stop", []):
            print("mock: stop failed", file=sys.stderr)
            sys.exit(255)
        data["active"].remove(port)
        control.unlink()
        data["stops"].append(port)
    else:
        assert "-M" in args and "-fnNT" in args, args
        forward = args[args.index("-L") + 1]
        assert forward == "127.0.0.1:{0}:127.0.0.1:{0}".format(port), args
        for option in ["ExitOnForwardFailure=yes", "ControlMaster=yes",
                       "ControlPersist=no", "GatewayPorts=no", "BatchMode=yes"]:
            assert option in args, args
        if port in data.get("fail_start", []):
            print("mock: connection failed", file=sys.stderr)
            sys.exit(255)
        time.sleep(data.get("start_delay", 0))
        with socket.socket(socket.AF_UNIX) as s:
            s.bind(str(control))
        data["active"].append(port)
        data["starts"].append(port)
    db.write_text(json.dumps(data))
'''


@unittest.skipUnless(FISH and shutil.which("lockf"), "requires Fish and macOS lockf")
class RafikiForwardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rf-test-", dir="/private/tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "s/rafiki-forward"
        self.db = self.root / "state.json"
        self.db.write_text(json.dumps({"active": [], "starts": [], "stops": []}))
        binary_dir = self.root / "bin"
        binary_dir.mkdir()
        for command in ["ssh", "lsof"]:
            path = binary_dir / command
            path.write_text(FAKE_COMMAND)
            path.chmod(0o755)
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.root / "s"),
                        RAFIKI_TEST_DB=str(self.db),
                        PATH=str(binary_dir) + os.pathsep + os.environ["PATH"])

    def update(self, **values):
        data = self.read()
        data.update(values)
        self.db.write_text(json.dumps(data))

    def read(self):
        return json.loads(self.db.read_text())

    def command(self, *args):
        return [FISH, "--no-config", "-c",
                'source "$argv[1]"; rafiki-forward $argv[2..]', str(SOURCE), *args]

    def run_forward(self, *args, expected=0):
        result = subprocess.run(self.command(*args), env=self.env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertIn("Status atual", result.stdout)
        self.assertIn("rafiki-forward stop all", result.stdout)
        return result

    def make_socket(self, port):
        self.state.mkdir(parents=True, exist_ok=True)
        with socket.socket(socket.AF_UNIX) as s:
            s.bind(str(self.state / ("p" + port + ".sock")))

    def test_no_arguments_only_reports_status(self):
        result = self.run_forward()
        self.assertIn("inativa", result.stdout)
        self.assertEqual(self.read()["starts"], [])
        self.assertFalse(self.state.exists())

    def test_open_only_missing_ports_and_report_both(self):
        self.run_forward("8080")
        result = self.run_forward("8080", "8000")
        self.assertIn("Já estava ativa: porta 8080", result.stdout)
        self.assertIn("Aberta: 127.0.0.1:8000", result.stdout)
        self.assertEqual(self.read()["starts"], ["8080", "8000"])
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_duplicates_and_leading_zeros_do_not_duplicate_tunnels(self):
        self.run_forward("08080", "8080", "8000", "8000")
        self.assertEqual(self.read()["starts"], ["8080", "8000"])

    def test_invalid_arguments_do_not_partially_apply(self):
        for arg in ["0", "65536", "abc", "--wrong", "8080:example:80", "stop"]:
            with self.subTest(arg=arg):
                self.run_forward("8000", arg, expected=2)
                self.assertEqual(self.read()["starts"], [])

    def test_stop_selected_port_keeps_other_ports(self):
        self.run_forward("8080", "8000")
        result = self.run_forward("stop", "8080", "8001")
        self.assertIn("Parada: porta 8080", result.stdout)
        self.assertIn("Já estava inativa: porta 8001", result.stdout)
        self.assertEqual(self.read()["active"], ["8000"])
        self.assertEqual(self.read()["stops"], ["8080"])

    def test_stop_all_only_stops_owned_tunnels(self):
        self.update(occupied=["9999"])
        self.run_forward("8080", "43210")
        self.run_forward("stop", "all")
        self.assertEqual(self.read()["active"], [])
        self.assertEqual(set(self.read()["stops"]), {"8080", "43210"})
        self.assertEqual(self.read()["occupied"], ["9999"])

    def test_busy_external_port_is_not_adopted_or_stopped(self):
        self.update(occupied=["8080"])
        result = self.run_forward("8080", expected=1)
        self.assertIn("ocupada por outro processo", result.stdout)
        self.run_forward("stop", "8080")
        self.assertEqual(self.read()["starts"], [])
        self.assertEqual(self.read()["stops"], [])

    def test_start_failure_is_nonzero_and_other_ports_are_still_processed(self):
        self.update(fail_start=["8080"])
        result = self.run_forward("8080", "8000", expected=1)
        self.assertIn("mock: connection failed", result.stderr)
        self.assertNotIn("Aberta: 127.0.0.1:8080", result.stdout)
        self.assertEqual(self.read()["active"], ["8000"])

    def test_stop_failure_preserves_active_session_and_returns_failure(self):
        self.run_forward("8080")
        self.update(fail_stop=["8080"])
        result = self.run_forward("stop", "8080", expected=1)
        self.assertNotIn("Parada: porta 8080", result.stdout)
        self.assertIn("ativa (rafiki-forward)", result.stdout)
        self.assertEqual(self.read()["active"], ["8080"])

    def test_stale_socket_can_be_reused(self):
        self.make_socket("8080")
        self.run_forward("8080")
        self.assertEqual(self.read()["active"], ["8080"])

    def test_stop_all_removes_stale_control_sockets(self):
        self.make_socket("43210")
        self.run_forward("stop", "all")
        self.assertFalse((self.state / "p43210.sock").exists())
        self.assertEqual(self.read()["stops"], [])

    def test_stop_all_continues_after_one_session_fails(self):
        self.run_forward("8080", "8000")
        self.update(fail_stop=["8000"])
        self.run_forward("stop", "all", expected=1)
        self.assertEqual(self.read()["active"], ["8000"])
        self.assertEqual(self.read()["stops"], ["8080"])

    def test_oversized_control_path_is_rejected_before_starting_ssh(self):
        self.env["XDG_STATE_HOME"] = str(self.root / ("x" * 80))
        self.run_forward("8080", expected=1)
        self.assertEqual(self.read()["starts"], [])

    def test_unexpected_control_file_is_preserved(self):
        self.state.mkdir(parents=True)
        path = self.state / "p8080.sock"
        path.write_text("unrelated file")
        self.run_forward("8080", expected=1)
        self.assertEqual(path.read_text(), "unrelated file")
        self.assertEqual(self.read()["starts"], [])

    def test_state_directory_symlink_is_rejected(self):
        destination = self.root / "other"
        destination.mkdir()
        self.state.parent.mkdir()
        self.state.symlink_to(destination, target_is_directory=True)
        result = subprocess.run(self.command("8080"), env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Status atual indisponível", result.stdout)
        self.assertEqual(list(destination.iterdir()), [])

    def test_custom_port_appears_in_later_status(self):
        self.run_forward("43210")
        result = self.run_forward()
        self.assertRegex(result.stdout, r"43210\s+ativa")
        self.assertIn("Parar uma porta: rafiki-forward stop 43210", result.stdout)
        self.assertEqual(self.read()["starts"], ["43210"])

    def test_help_status_and_usage_errors_always_report_status(self):
        for args, expected in [(("--help",), 0), (("status",), 0),
                               (("stop",), 2), (("stop", "all", "8080"), 2),
                               (("status", "8080"), 2), (("stop", "all"), 0)]:
            with self.subTest(args=args):
                self.run_forward(*args, expected=expected)

    def test_concurrent_starts_create_only_one_tunnel(self):
        self.update(start_delay=0.3)
        first = subprocess.Popen(self.command("8080"), env=self.env,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        second = subprocess.Popen(self.command("8080"), env=self.env,
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for process in [first, second]:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stdout + stderr)
        finally:
            for process in [first, second]:
                if process.poll() is None:
                    process.terminate()
                process.communicate(timeout=5)
        self.assertEqual(self.read()["starts"], ["8080"])

    def test_compatibility_command_delegates_to_the_safe_function(self):
        command = [FISH, "--no-config", "-c",
                   'source "$argv[1]"; source "$argv[2]"; ports 8080',
                   str(SOURCE), str(SOURCE.with_name("ports.fish"))]
        result = subprocess.run(command, env=self.env, text=True,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read()["active"], ["8080"])


if __name__ == "__main__":
    unittest.main()
