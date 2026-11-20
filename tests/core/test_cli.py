import subprocess
import sys

from firewitness.cli import discover, main


def test_discovery_finds_records():
    found, failed = discover()
    assert "records" in found and not failed


def test_main_runs(capsys):
    assert main(["--version"]) == 0
    assert main([]) == 0


def test_python_dash_m():
    r = subprocess.run([sys.executable, "-m", "firewitness", "records", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "clean" in r.stdout
