import subprocess
import sys


def test_package_imports():
    import github_daily_report

    assert github_daily_report.__version__ == "0.1.0"


def test_package_module_exposes_cli_commands():
    result = subprocess.run(
        [sys.executable, "-m", "github_daily_report", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "collect" in result.stdout
